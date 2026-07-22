/**
 * M38-WP10 Discovery Experience Runtime.
 *
 * This module is an Experience-owned, transient holder for an unmodified
 * M37 Discovery Candidate. It deliberately has no Search client, Registry or
 * Resolver dependency and creates neither Asset Focus nor durable identity.
 */

export type WorkspaceIdentity = string | number;

/** The only WP2 fact WP10 needs from the frozen public workspace boundary. */
export interface ResolvedWorkspacePrerequisite {
  readonly workspace_id: WorkspaceIdentity;
}

export interface WorkspacePrerequisiteReader {
  readResolvedWorkspace(): ResolvedWorkspacePrerequisite | null;
}

/** Exact public wire shape emitted for an M37 Discovery Candidate. */
export interface DiscoveryCandidate {
  readonly kind: "DISCOVERY";
  readonly claim_id: string;
  readonly provider_name: string;
  readonly reported_symbol: string | null;
  readonly reported_name: string | null;
  readonly reported_identifiers: Readonly<Record<string, string>>;
  readonly market: string | null;
  readonly currency: string | null;
  readonly match_field: string;
}

/** Exact public M37 Search degradation disclosure entry. */
export interface SearchDegradationEntry {
  readonly source: string;
  readonly reason: string;
  readonly message: string;
  readonly candidate_kind_uncertain: boolean;
}

export interface DiscoveryExperienceContext {
  readonly workspace_id: WorkspaceIdentity;
  readonly candidate: DiscoveryCandidate;
  readonly search_degradation?: readonly SearchDegradationEntry[];
  readonly experience_state: "OPEN" | "CLOSED";
}

/**
 * Opaque, process-local operation correlation. It is intentionally outside
 * DiscoveryExperienceContext and cannot be serialized into a route or DTO.
 */
const handleBrand: unique symbol = Symbol("M38-WP10 Discovery Experience");
export interface DiscoveryExperienceHandle {
  readonly [handleBrand]: true;
}

export interface OpenDiscoveryExperienceInput {
  readonly candidate: DiscoveryCandidate;
  readonly search_degradation?: readonly SearchDegradationEntry[];
}

export type DiscoveryExperienceRejectionReason =
  | "WORKSPACE_NOT_RESOLVED"
  | "INVALID_DISCOVERY_CANDIDATE"
  | "INVALID_SEARCH_DEGRADATION"
  | "REENTRANT_LIFECYCLE_COMMAND";

export type OpenDiscoveryExperienceResult =
  | {
      readonly status: "OPENED";
      readonly handle: DiscoveryExperienceHandle;
      readonly context: DiscoveryExperienceContext;
    }
  | {
      readonly status: "REJECTED";
      readonly reason: DiscoveryExperienceRejectionReason;
    };

export type DiscoveryExperienceCloseReason = "CLOSE" | "REPLACEMENT" | "EXPIRY";

export interface DiscoveryExperienceNotification {
  readonly context: DiscoveryExperienceContext;
  readonly reason: "OPEN" | DiscoveryExperienceCloseReason;
}

export type DiscoveryExperienceObserver = (notification: DiscoveryExperienceNotification) => void;

export interface CurrentDiscoveryExperience {
  readonly handle: DiscoveryExperienceHandle;
  readonly context: DiscoveryExperienceContext;
}

const CANDIDATE_KEYS = new Set([
  "kind",
  "claim_id",
  "provider_name",
  "reported_symbol",
  "reported_name",
  "reported_identifiers",
  "market",
  "currency",
  "match_field",
]);

const DEGRADATION_KEYS = new Set([
  "source",
  "reason",
  "message",
  "candidate_kind_uncertain",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, expected: ReadonlySet<string>): boolean {
  const keys = Object.keys(value);
  return keys.length === expected.size && keys.every((key) => expected.has(key));
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isStringRecord(value: unknown): value is Readonly<Record<string, string>> {
  return (
    isRecord(value) &&
    Object.entries(value).every(([key, entry]) => key.length > 0 && typeof entry === "string")
  );
}

export function isDiscoveryCandidate(value: unknown): value is DiscoveryCandidate {
  if (!isRecord(value) || !hasExactKeys(value, CANDIDATE_KEYS)) return false;

  return (
    value.kind === "DISCOVERY" &&
    typeof value.claim_id === "string" &&
    value.claim_id.length > 0 &&
    typeof value.provider_name === "string" &&
    value.provider_name.length > 0 &&
    isNullableString(value.reported_symbol) &&
    isNullableString(value.reported_name) &&
    isStringRecord(value.reported_identifiers) &&
    isNullableString(value.market) &&
    isNullableString(value.currency) &&
    typeof value.match_field === "string"
  );
}

function isSearchDegradationEntry(value: unknown): value is SearchDegradationEntry {
  if (!isRecord(value) || !hasExactKeys(value, DEGRADATION_KEYS)) return false;

  return (
    typeof value.source === "string" &&
    typeof value.reason === "string" &&
    typeof value.message === "string" &&
    typeof value.candidate_kind_uncertain === "boolean"
  );
}

function isSearchDegradation(
  value: unknown
): value is readonly SearchDegradationEntry[] | undefined {
  return value === undefined || (Array.isArray(value) && value.every(isSearchDegradationEntry));
}

function isWorkspaceIdentity(value: unknown): value is WorkspaceIdentity {
  return (
    (typeof value === "string" && value.length > 0) ||
    (typeof value === "number" && Number.isSafeInteger(value) && value >= 0)
  );
}

interface RuntimeInstance {
  readonly handle: DiscoveryExperienceHandle;
  readonly context: DiscoveryExperienceContext;
}

function createHandle(): DiscoveryExperienceHandle {
  return Object.freeze({ [handleBrand]: true }) as DiscoveryExperienceHandle;
}

function openContext(
  workspaceId: WorkspaceIdentity,
  input: OpenDiscoveryExperienceInput
): DiscoveryExperienceContext {
  const base = {
    workspace_id: workspaceId,
    candidate: input.candidate,
    experience_state: "OPEN" as const,
  };

  return Object.freeze(
    input.search_degradation === undefined
      ? base
      : { ...base, search_degradation: input.search_degradation }
  );
}

function closedContext(context: DiscoveryExperienceContext): DiscoveryExperienceContext {
  const base = {
    workspace_id: context.workspace_id,
    candidate: context.candidate,
    experience_state: "CLOSED" as const,
  };

  return Object.freeze(
    context.search_degradation === undefined
      ? base
      : { ...base, search_degradation: context.search_degradation }
  );
}

/**
 * Owns only the WP10 OPEN -> CLOSED lifecycle. The holder is deliberately
 * process-local: a new coordinator starts structurally ABSENT and replays
 * nothing.
 */
export class DiscoveryExperienceCoordinator {
  private current: RuntimeInstance | null = null;
  private transitionInProgress = false;
  private readonly observers = new Set<DiscoveryExperienceObserver>();
  private readonly workspacePrerequisite: WorkspacePrerequisiteReader;

  constructor(workspacePrerequisite: WorkspacePrerequisiteReader) {
    this.workspacePrerequisite = workspacePrerequisite;
  }

  readCurrent(): CurrentDiscoveryExperience | null {
    if (this.current === null) return null;
    return Object.freeze({ handle: this.current.handle, context: this.current.context });
  }

  open(input: OpenDiscoveryExperienceInput): OpenDiscoveryExperienceResult {
    if (this.transitionInProgress) {
      return Object.freeze({ status: "REJECTED", reason: "REENTRANT_LIFECYCLE_COMMAND" });
    }

    this.transitionInProgress = true;
    try {
      const workspace = this.workspacePrerequisite.readResolvedWorkspace();
      if (workspace === null || !isWorkspaceIdentity(workspace.workspace_id)) {
        return Object.freeze({ status: "REJECTED", reason: "WORKSPACE_NOT_RESOLVED" });
      }
      if (!isDiscoveryCandidate(input.candidate)) {
        return Object.freeze({ status: "REJECTED", reason: "INVALID_DISCOVERY_CANDIDATE" });
      }
      if (!isSearchDegradation(input.search_degradation)) {
        return Object.freeze({ status: "REJECTED", reason: "INVALID_SEARCH_DEGRADATION" });
      }

      const previous = this.current;
      const next: RuntimeInstance = Object.freeze({
        handle: createHandle(),
        context: openContext(workspace.workspace_id, input),
      });

      // Publish the successor as current before notifying replacement observers;
      // observers can therefore never read an intermediate current-state gap.
      this.current = next;
      if (previous !== null) {
        this.notify(closedContext(previous.context), "REPLACEMENT");
      }
      this.notify(next.context, "OPEN");

      return Object.freeze({ status: "OPENED", handle: next.handle, context: next.context });
    } finally {
      this.transitionInProgress = false;
    }
  }

  close(handle: DiscoveryExperienceHandle): boolean {
    return this.closeCurrent(handle, "CLOSE");
  }

  expire(handle: DiscoveryExperienceHandle): boolean {
    return this.closeCurrent(handle, "EXPIRY");
  }

  observe(observer: DiscoveryExperienceObserver): () => void {
    this.observers.add(observer);
    return () => {
      this.observers.delete(observer);
    };
  }

  private closeCurrent(
    handle: DiscoveryExperienceHandle,
    reason: Exclude<DiscoveryExperienceCloseReason, "REPLACEMENT">
  ): boolean {
    if (this.transitionInProgress) return false;

    this.transitionInProgress = true;
    try {
      if (this.current === null || this.current.handle !== handle) return false;

      const closing = this.current;
      this.current = null;
      this.notify(closedContext(closing.context), reason);
      return true;
    } finally {
      this.transitionInProgress = false;
    }
  }

  private notify(context: DiscoveryExperienceContext, reason: DiscoveryExperienceNotification["reason"]): void {
    const notification = Object.freeze({ context, reason });
    for (const observer of [...this.observers]) {
      try {
        observer(notification);
      } catch {
        // Observation is non-authoritative and cannot alter lifecycle outcome.
      }
    }
  }
}
