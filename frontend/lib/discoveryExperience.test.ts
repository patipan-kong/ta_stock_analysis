import assert from "node:assert/strict";
import { test } from "node:test";

import {
  DiscoveryExperienceCoordinator,
  type DiscoveryCandidate,
  type DiscoveryExperienceHandle,
  type SearchDegradationEntry,
  type WorkspacePrerequisiteReader,
} from "./discoveryExperience.ts";

function candidate(overrides: Partial<DiscoveryCandidate> = {}): DiscoveryCandidate {
  return {
    kind: "DISCOVERY",
    claim_id: "claim:provider:1",
    provider_name: "provider",
    reported_symbol: "ABC",
    reported_name: "ABC Corp",
    reported_identifiers: { PROVIDER_SYMBOL: "ABC" },
    market: "TEST",
    currency: "USD",
    match_field: "reported_symbol",
    ...overrides,
  };
}

function degradation(): readonly SearchDegradationEntry[] {
  return [
    {
      source: "catalog",
      reason: "unavailable",
      message: "Catalog was unavailable",
      candidate_kind_uncertain: true,
    },
  ];
}

function reader(workspaceId: string | number | null = 7): WorkspacePrerequisiteReader {
  return {
    readResolvedWorkspace: () =>
      workspaceId === null ? null : { workspace_id: workspaceId },
  };
}

test("opens an exact Discovery Candidate in the resolved current workspace", () => {
  const sourceCandidate = candidate();
  const sourceDegradation = degradation();
  const runtime = new DiscoveryExperienceCoordinator(reader("workspace-7"));

  const result = runtime.open({
    candidate: sourceCandidate,
    search_degradation: sourceDegradation,
  });

  assert.equal(result.status, "OPENED");
  if (result.status !== "OPENED") return;
  assert.equal(result.context.workspace_id, "workspace-7");
  assert.equal(result.context.experience_state, "OPEN");
  assert.strictEqual(result.context.candidate, sourceCandidate);
  assert.strictEqual(result.context.search_degradation, sourceDegradation);
  assert.strictEqual(runtime.readCurrent()?.context, result.context);
});

test("represents absence structurally before open and after close", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  assert.equal(runtime.readCurrent(), null);

  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;

  assert.equal(runtime.close(opened.handle), true);
  assert.equal(runtime.readCurrent(), null);
});

test("publishes OPEN then terminal CLOSED without adding a context state", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const observed: Array<{ state: string; reason: string }> = [];
  runtime.observe(({ context, reason }) => {
    observed.push({ state: context.experience_state, reason });
  });

  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;
  runtime.close(opened.handle);

  assert.deepEqual(observed, [
    { state: "OPEN", reason: "OPEN" },
    { state: "CLOSED", reason: "CLOSE" },
  ]);
});

test("replacement closes the old instance and installs one new OPEN instance", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const observed: Array<{ claim: string; state: string; reason: string }> = [];
  runtime.observe(({ context, reason }) => {
    observed.push({
      claim: context.candidate.claim_id,
      state: context.experience_state,
      reason,
    });
  });

  const first = runtime.open({ candidate: candidate({ claim_id: "claim:1" }) });
  const second = runtime.open({ candidate: candidate({ claim_id: "claim:2" }) });
  assert.equal(first.status, "OPENED");
  assert.equal(second.status, "OPENED");
  if (first.status !== "OPENED" || second.status !== "OPENED") return;

  assert.notStrictEqual(first.handle, second.handle);
  assert.equal(runtime.readCurrent()?.context.candidate.claim_id, "claim:2");
  assert.deepEqual(observed, [
    { claim: "claim:1", state: "OPEN", reason: "OPEN" },
    { claim: "claim:1", state: "CLOSED", reason: "REPLACEMENT" },
    { claim: "claim:2", state: "OPEN", reason: "OPEN" },
  ]);
});

test("replacement observers never read an intermediate current-state gap", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const currentClaims: Array<string | null> = [];
  runtime.observe(({ reason }) => {
    if (reason === "REPLACEMENT") {
      currentClaims.push(runtime.readCurrent()?.context.candidate.claim_id ?? null);
    }
  });

  runtime.open({ candidate: candidate({ claim_id: "claim:1" }) });
  runtime.open({ candidate: candidate({ claim_id: "claim:2" }) });
  assert.deepEqual(currentClaims, ["claim:2"]);
});

test("re-entrant open from replacement fails closed without a stale trailing OPEN", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const notifications: string[] = [];
  let nestedResult: ReturnType<DiscoveryExperienceCoordinator["open"]> | null = null;

  runtime.observe(({ context, reason }) => {
    notifications.push(
      `${context.candidate.claim_id}:${context.experience_state}:${reason}`
    );
    if (
      context.candidate.claim_id === "claim:A" &&
      context.experience_state === "CLOSED" &&
      reason === "REPLACEMENT"
    ) {
      nestedResult = runtime.open({ candidate: candidate({ claim_id: "claim:C" }) });
    }
  });

  const first = runtime.open({ candidate: candidate({ claim_id: "claim:A" }) });
  const replacement = runtime.open({ candidate: candidate({ claim_id: "claim:B" }) });
  assert.equal(first.status, "OPENED");
  assert.equal(replacement.status, "OPENED");
  if (replacement.status !== "OPENED") return;

  assert.deepEqual(nestedResult, {
    status: "REJECTED",
    reason: "REENTRANT_LIFECYCLE_COMMAND",
  });
  assert.strictEqual(runtime.readCurrent()?.handle, replacement.handle);
  assert.strictEqual(runtime.readCurrent()?.context, replacement.context);
  assert.deepEqual(notifications, [
    "claim:A:OPEN:OPEN",
    "claim:A:CLOSED:REPLACEMENT",
    "claim:B:OPEN:OPEN",
  ]);
});

test("re-entrant close from an observer causes no nested mutation", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  let nestedClose: boolean | null = null;
  let openedHandle: DiscoveryExperienceHandle | undefined;

  runtime.observe(({ reason }) => {
    if (reason === "OPEN") {
      openedHandle = runtime.readCurrent()?.handle;
      if (openedHandle !== undefined) nestedClose = runtime.close(openedHandle);
    }
  });

  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;
  assert.equal(nestedClose, false);
  assert.strictEqual(runtime.readCurrent()?.handle, opened.handle);
  assert.equal(runtime.close(opened.handle), true);
});

test("re-entrant expiry from an observer causes no nested mutation", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  let nestedExpiry: boolean | null = null;

  runtime.observe(({ reason }) => {
    if (reason === "OPEN") {
      const current = runtime.readCurrent();
      if (current !== null) nestedExpiry = runtime.expire(current.handle);
    }
  });

  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;
  assert.equal(nestedExpiry, false);
  assert.strictEqual(runtime.readCurrent()?.handle, opened.handle);
  assert.equal(runtime.expire(opened.handle), true);
});

test("a stale close or expiry cannot close a successor", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const first = runtime.open({ candidate: candidate({ claim_id: "claim:1" }) });
  const second = runtime.open({ candidate: candidate({ claim_id: "claim:2" }) });
  assert.equal(first.status, "OPENED");
  assert.equal(second.status, "OPENED");
  if (first.status !== "OPENED" || second.status !== "OPENED") return;

  assert.equal(runtime.close(first.handle), false);
  assert.equal(runtime.expire(first.handle), false);
  assert.strictEqual(runtime.readCurrent()?.handle, second.handle);
});

test("expiry closes only its targeted current instance", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const reasons: string[] = [];
  runtime.observe(({ reason }) => reasons.push(reason));
  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;

  assert.equal(runtime.expire(opened.handle), true);
  assert.equal(runtime.readCurrent(), null);
  assert.deepEqual(reasons, ["OPEN", "EXPIRY"]);
});

test("fails closed when the workspace prerequisite is unresolved", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader(null));
  assert.deepEqual(runtime.open({ candidate: candidate() }), {
    status: "REJECTED",
    reason: "WORKSPACE_NOT_RESOLVED",
  });
  assert.equal(runtime.readCurrent(), null);
});

test("a failed replacement leaves the current OPEN instance unchanged", () => {
  let resolved = true;
  const runtime = new DiscoveryExperienceCoordinator({
    readResolvedWorkspace: () => (resolved ? { workspace_id: 7 } : null),
  });
  const first = runtime.open({ candidate: candidate({ claim_id: "claim:1" }) });
  assert.equal(first.status, "OPENED");
  if (first.status !== "OPENED") return;

  resolved = false;
  const rejected = runtime.open({ candidate: candidate({ claim_id: "claim:2" }) });
  assert.deepEqual(rejected, {
    status: "REJECTED",
    reason: "WORKSPACE_NOT_RESOLVED",
  });
  assert.strictEqual(runtime.readCurrent()?.handle, first.handle);
});

test("rejects a Registered Candidate and any Discovery Candidate carrying asset_id", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const registered = { ...candidate(), kind: "REGISTERED", asset_id: 42 };
  const identityBearingDiscovery = { ...candidate(), asset_id: 42 };

  assert.equal(
    runtime.open({ candidate: registered as unknown as DiscoveryCandidate }).status,
    "REJECTED"
  );
  assert.equal(
    runtime.open({ candidate: identityBearingDiscovery as DiscoveryCandidate }).status,
    "REJECTED"
  );
  assert.equal(runtime.readCurrent(), null);
});

test("rejects malformed candidate fields and unknown candidate fields", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const emptyClaim = candidate({ claim_id: "" });
  const unknownField = { ...candidate(), rank: 1 };

  assert.equal(runtime.open({ candidate: emptyClaim }).status, "REJECTED");
  assert.equal(
    runtime.open({ candidate: unknownField as DiscoveryCandidate }).status,
    "REJECTED"
  );
});

test("rejects malformed degradation without hiding a currently open context", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;

  const malformed = [{ ...degradation()[0], extra: "not-public" }];
  const rejected = runtime.open({
    candidate: candidate({ claim_id: "claim:2" }),
    search_degradation: malformed as unknown as readonly SearchDegradationEntry[],
  });
  assert.deepEqual(rejected, {
    status: "REJECTED",
    reason: "INVALID_SEARCH_DEGRADATION",
  });
  assert.strictEqual(runtime.readCurrent()?.handle, opened.handle);
});

test("observer failure cannot change lifecycle outcome or suppress other observers", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const observed: string[] = [];
  runtime.observe(() => {
    throw new Error("non-authoritative observer failure");
  });
  runtime.observe(({ reason }) => observed.push(reason));

  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  assert.deepEqual(observed, ["OPEN"]);
  if (opened.status !== "OPENED") return;

  assert.equal(runtime.close(opened.handle), true);
  const reopened = runtime.open({ candidate: candidate({ claim_id: "claim:after-error" }) });
  assert.equal(reopened.status, "OPENED");
});

test("unsubscribe stops observation without changing current business state", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  let notifications = 0;
  const unsubscribe = runtime.observe(() => {
    notifications += 1;
  });
  unsubscribe();

  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  assert.equal(notifications, 0);
  assert.equal(runtime.readCurrent()?.context.experience_state, "OPEN");
});

test("a new runtime starts ABSENT and does not replay another runtime's context", () => {
  const firstRuntime = new DiscoveryExperienceCoordinator(reader());
  assert.equal(firstRuntime.open({ candidate: candidate() }).status, "OPENED");

  const restartedRuntime = new DiscoveryExperienceCoordinator(reader());
  assert.equal(restartedRuntime.readCurrent(), null);
});

test("canonical context and public handle expose no durable route or asset identity", () => {
  const runtime = new DiscoveryExperienceCoordinator(reader());
  const opened = runtime.open({ candidate: candidate() });
  assert.equal(opened.status, "OPENED");
  if (opened.status !== "OPENED") return;

  assert.deepEqual(Object.keys(opened.context), [
    "workspace_id",
    "candidate",
    "experience_state",
  ]);
  assert.equal(JSON.stringify(opened.handle), "{}");
  assert.equal("asset_id" in opened.context, false);
  assert.equal("route" in opened.context, false);
});

test("workspace identity is copied exactly without coercion", () => {
  const numeric = new DiscoveryExperienceCoordinator(reader(7)).open({ candidate: candidate() });
  const textual = new DiscoveryExperienceCoordinator(reader("7")).open({ candidate: candidate() });
  assert.equal(numeric.status, "OPENED");
  assert.equal(textual.status, "OPENED");
  if (numeric.status !== "OPENED" || textual.status !== "OPENED") return;

  assert.equal(numeric.context.workspace_id, 7);
  assert.equal(textual.context.workspace_id, "7");
  assert.notStrictEqual(numeric.context.workspace_id, textual.context.workspace_id);
});
