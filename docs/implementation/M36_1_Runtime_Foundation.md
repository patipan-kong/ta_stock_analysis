# M36.1 - Multiple Portfolio Runtime Foundation

**Date:** 2026-07-20

**Document class:** Implementation plan (planning milestone)

**Status:** `PROPOSED_FOR_IMPLEMENTATION`

**Implementation authority:** `AVAILABLE FOR M36.1 ONLY` (per project status)

**Runtime authority:** `NONE` (rollout not yet authorized)

**Confirmed scope decisions (2026-07-20):**
- Current Selection uses **strict no-default**: a fresh/cleared session with
  portfolios present resolves to `NONE` + prompt to select — never auto-open,
  not even when exactly one portfolio exists (full `M36-WP1-A04` conformance).
- **Portfolio Lifecycle State (former Phase 4) is deferred** to a later
  milestone. M36.1 therefore ships with **zero database schema change**.

**Governing architecture (frozen, not amended by this plan):**
[M36-WP1](M36_WP1_Multiple_Portfolio_Foundation.md),
[M35-WP1](M35_WP1_Product_Workspace_Foundation.md),
[M33.8](M33_8_stable_human_identity_and_scoped_authorization_foundation.md),
[M34 Decision Register](m34/audit/registers/decision_register.md),
[Platform Architecture](../architecture/platform_architecture.md),
[Portfolio Domain Model](../architecture/PORTFOLIO_DOMAIN_MODEL.md).

---

## 1. Purpose and framing

This plan defines the smallest implementation milestone that makes the runtime
conform to the canonical Multiple Portfolio Foundation (M36-WP1). It designs no
new architecture, changes no canonical ownership, and adds none of the deferred
concerns (sharing, RBAC, cross-portfolio analytics, wealth aggregation,
execution, AI).

**Central finding from the codebase audit:** the runtime is *already*
structurally multi-portfolio. It is not greenfield. Therefore M36.1 is
predominantly a **conformance and consolidation** milestone, not a construction
milestone. The core multiple-portfolio runtime requires **no database schema
change**.

### 1.1 What already exists (verified)

| Canonical element (M36-WP1) | Current runtime reality | Conformance |
| --- | --- | --- |
| One Product Workspace establishes one Workspace Context (§5.1) | `Workspace` table; single default row (id=1); `_ws_id(db)` helper resolves it ([backend/main.py:164](../../backend/main.py#L164)) | Conformant (single-workspace runtime; multi-workspace deferred) |
| Workspace references zero/one/many Portfolio Identities (§5.1, A02) | `Portfolio.workspace_id` FK, `Workspace.portfolios` one-to-many ([backend/models/database.py:58](../../backend/models/database.py#L58)) | Conformant |
| Each Portfolio Identity retains one Accounting Scope (§11, inv. 3) | Holdings/transactions/snapshots carry `portfolio_id` FK; never merged | Conformant |
| Referenceability = exact identity + exact one-workspace relationship (§5.2, inv. 9) | Every endpoint filters `Portfolio.id == portfolio_id AND Portfolio.workspace_id == ws` (~40 call sites) | Conformant in effect, **not centralized** |
| Current Selection is zero-or-one, Experience-owned (§9, A04) | `PortfolioContext.activeId` + `localStorage` ([frontend/lib/PortfolioContext.tsx](../../frontend/lib/PortfolioContext.tsx)) | **Non-conformant** (see §1.2) |
| Portfolio Lifecycle State (active/archived/closed), Ledger-owned (§3.3, §12) | Glossary term registered ([docs/GLOSSARY.md:575](../GLOSSARY.md#L575)); **no runtime field** | Absent (foundation gap) |

### 1.2 Conformance violations to remediate (the real work)

The existing `PortfolioContext` predates M36 and breaks two foundation
invariants:

- **V1 - First-portfolio default.** On load it selects
  `list.find(saved) ?? list[0] ?? null`
  ([PortfolioContext.tsx:31](../../frontend/lib/PortfolioContext.tsx#L31)).
  Falling back to `list[0]` is a **default portfolio chosen by architecture**,
  violating `M36-WP1-A04` (Current Selection has no architecture default),
  invariant 20 (missing selection never causes automatic selection), and §8.3
  (no first/default/largest/most-recent by architecture).

- **V2 - Automatic fallback on delete.** On delete it re-points selection to
  `remaining[0]`
  ([PortfolioContext.tsx:53-54](../../frontend/lib/PortfolioContext.tsx#L53)).
  This violates §9.2 (clearing goes to `NONE`, "no automatic selection of
  another portfolio") and invariant 11 (cleared without fallback).

These two lines are the primary remediation target. Everything else is
consolidation and conformance hardening.

### 1.3 Explicit non-goals (unchanged from M36-WP1 deferrals)

M36.1 does **not** implement: portfolio sharing, RBAC/membership/grants,
cross-portfolio comparison or aggregation, wealth/net-worth roll-up, execution
or trading, AI behavior, lifecycle **transition** workflows (create-beyond-
today, archive, close, merge, clone commands), a generic read-access policy, or
multi-workspace runtime. Each retains its existing M36-WP1 §13 attachment point.

### 1.4 M33 authority: untouched by design

Switching Current Selection is pure Experience Interaction State and is **not**
an M33-governed action (§9.3; invariant 12: selection grants no authority).
M36.1 therefore invokes **no** M33 contract and changes no governed-action
boundary. The existing execution/decision endpoints that *are* governed keep
their current boundaries verbatim. This keeps the frozen M33.8 surface out of
scope and is a deliberate risk reducer.

---

## 2. Ownership map for the milestone

Every unit of work below is tagged to its canonical owner so no task drifts
ownership. This table is the guardrail for code review.

| Runtime concern | Canonical owner (M36-WP1 §7) | M36.1 realizes it as | Must NOT become |
| --- | --- | --- | --- |
| Current Selection (zero-or-one, orientation) | Experience Platform | Frontend `PortfolioContext` state + M35 User Preference persistence | A backend column, an ambient default, or an authority |
| Portfolio referenceability (identity + one-workspace relationship) | Ledger & Accounting (identity) resolved by M35 Context Resolver | One shared backend resolver + one shared frontend guard | A permission check or availability check |
| Portfolio Lifecycle State (active/archived/closed) | Ledger & Accounting | Deferred; no runtime representation in this milestone | Current Selection, permission, or a transition decision |
| Portfolio Identity, Accounting Scope, holdings, ledger | Ledger & Accounting | Unchanged | Merged or duplicated across portfolios |
| Governed actions (execution/decision) | Existing decision gate + M33 | Unchanged | Reached via selection instead of authority |

---

## 3. Implementation phases

Phases are ordered by risk and dependency. The entire milestone needs **no
migration** (lifecycle state is deferred). Phase 5 is cross-cutting hardening.

### Phase 0 - Referenceability resolver consolidation (no behavior change)

Centralize the ~40 inline `Portfolio.id == portfolio_id AND workspace_id == ws`
lookups into one function that *is* the runtime expression of the M36 §5.2
referenceability contract (identity + exact one-workspace relationship). This
makes the contract testable in one place and gives every future caller a single
fail-closed path.

- **Backend:** add `resolve_portfolio_reference(db, ws_id, portfolio_id) ->
  Portfolio | None` (a "Context Resolver / Scope Reference" analog per M35
  §11.3). Return `None` on absent identity, foreign workspace, or mismatch — a
  boundary result, never a fallback. Replace inline lookups incrementally.
- **Frontend:** add `resolvePortfolioReference(portfolios, id): Portfolio |
  null` used by the context and switcher.
- **No behavior change** — this is a characterization-tested refactor.

### Phase 1 - Current Selection conformance (frontend, core remediation)

Rewrite `PortfolioContext` so Current Selection is a true zero-or-one
orientation with **`NONE` as a first-class legitimate state**:

1. Remove the `list[0]` default (fixes V1). Initial selection is the persisted
   value **only if it still resolves** in the current workspace; otherwise
   `NONE`. Strict no-default: `NONE` is the resolved state even when exactly
   one portfolio exists — the single reference is not auto-opened (§8.2).
2. On delete/vanish, clear to `NONE` — never fall back to `remaining[0]`
   (fixes V2). §9.2.
3. Selection is set **only** by explicit human orientation (`selectPortfolio(id)`)
   or a validated deep-entry, never implicitly.
4. Persist under an M35 User Preference State key (rename
   `active_portfolio_id` -> `workspace_current_selection`) and re-validate on
   rehydrate (§9.2: a remembered selection may propose orientation "only after
   exact context validation").

Expose `currentSelection: number | null` (renamed from `activeId`) and a
`hasSelection` boolean so consumers can branch cleanly.

### Phase 2 - Explicit context propagation + fail-closed boundary

Ensure portfolio-scoped surfaces never operate without a resolved selection,
and that a mismatch surfaces as a boundary state, not a silent fallback
(§6.3, §7.1).

- Guard: portfolio-scoped API calls are gated on `hasSelection`; when `NONE`,
  the surface renders an explicit "select a portfolio" empty state (M36-WP1
  §8.1/§8.2: the sole reference is not automatically selected).
- Backend already returns `404` for an unresolved portfolio; standardize the
  frontend handling so a stale selection (deleted/foreign) transitions the
  context to `NONE` and shows the boundary state — it never picks another
  portfolio (§6.3, invariant 21).

### Phase 3 - Workspace portfolio switcher contract

Consolidate the scattered per-page selection (`portfolio/page.tsx` `<select>`,
`Navbar`, and ~25 consumer files) onto the shared context so there is exactly
one switching mechanism.

- The switcher is Workspace-Scope orientation over the explicit set of
  same-workspace Portfolio Identities (§10 navigation model). It lists
  zero/one/many, sets selection explicitly, offers an explicit "no selection"
  affordance, and never auto-picks.
- Visual design (labels, ordering, recents, favourites) stays deferred per
  §10 law 10 — this phase defines behavior, not styling.

### Deferred - Portfolio Lifecycle State (not in M36.1)

Portfolio Lifecycle State (active/archived/closed) is a **future milestone**,
confirmed out of scope here. Multiple-portfolio switching is fully functional
without it, and deferring it keeps M36.1 at **zero schema change**. When it is
picked up, it attaches additively per M36-WP1 §12: a Ledger & Accounting-owned
`lifecycle_state` field (nullable -> backfill `'active'`) surfaced read-only,
with archive/close/merge/clone **transition commands** routed through Portfolio
Domain Model §9 and the Platform decision gate — never encoded as workspace
state. The registered Glossary term ([docs/GLOSSARY.md:575](../GLOSSARY.md#L575))
already reserves the vocabulary for that later work.

### Phase 5 - Conformance test suite + consumer audit

Encode the invariants as executable tests (see §7) and audit every `activeId`
consumer for `NONE`-safety.

---

## 4. Backend work

| # | Task | Files | Complexity |
| --- | --- | --- | --- |
| B1 | `resolve_portfolio_reference()` resolver + unit tests | new `backend/services/portfolio_reference.py`; `backend/main.py` | S |
| B2 | Replace inline lookups with resolver (incremental, behavior-preserving) | `backend/main.py` (~40 sites), routers | M |
| B3 | Keep "cannot delete last portfolio" guard unchanged (decision confirmed — see §10) | `backend/main.py:651` (no change) | none |

Backend keeps: every endpoint remains `portfolio_id`-explicit and
workspace-scoped. **No endpoint signature changes. No new backend Current-
Selection state** (Current Selection is Experience-owned; a backend
`current_portfolio_id` column would violate §12 and is prohibited).

## 5. Frontend work

| # | Task | Files | Complexity |
| --- | --- | --- | --- |
| F1 | Rewrite `PortfolioContext`: `NONE`-legal, no `list[0]`, no delete fallback, re-validated rehydrate, renamed persistence key | `frontend/lib/PortfolioContext.tsx` | M |
| F2 | `resolvePortfolioReference()` helper + `hasSelection`/`currentSelection` API | `frontend/lib/PortfolioContext.tsx` | S |
| F3 | Consumer audit: make every `activeId` reader `NONE`-safe (empty state) | ~25 files under `frontend/app`, `frontend/components` | L (breadth) |
| F4 | Shared workspace switcher behavior on the context | `frontend/components/Navbar.tsx`, `frontend/app/portfolio/page.tsx` | M |
| F5 | "Select a portfolio" boundary/empty state for portfolio-scoped surfaces | portfolio-scoped pages | M |
| F6 | Stale-selection handling -> transition to `NONE` + boundary state on 404 | `frontend/lib/api.ts` callers / context | S |

## 6. Migration & compatibility

### 6.1 Migration impact

- **None.** The entire milestone ships with **zero schema change** — the
  strongest "minimal architectural risk" property of this plan. Portfolio
  Lifecycle State, the only element that would have required a migration, is
  deferred to a later milestone.

### 6.2 Compatibility analysis

- **API contracts:** unchanged. All endpoints are already `portfolio_id`-
  explicit and workspace-scoped; no consumer breaks.
- **Backend behavior:** B1/B2 are behavior-preserving (characterization-tested).
  B3-B5 are additive.
- **Frontend behavior — one intentional change:** the "fresh session with no
  valid saved selection" case changes from *auto-open first portfolio* to
  *`NONE` + prompt to select* (strict, including the single-portfolio case).
  This is the deliberate cost of conformance with `M36-WP1-A04`. Compatibility
  bridge: existing users retain their persisted `active_portfolio_id` (migrated
  to the new key on first load if it still resolves), so only brand-new or
  cleared-storage sessions ever see `NONE`.
- **Data:** untouched. No portfolio identity, accounting scope, or ledger
  record is written (invariant 22), and no schema changes.

## 7. Testing strategy

Encode the M36 invariants as executable conformance tests — this is how the
plan proves it "realizes the canonical foundation."

**Backend (pytest):**
- `resolve_portfolio_reference` returns the portfolio for (valid id, valid ws);
  `None` for absent id, foreign-workspace id, and mismatched relationship — and
  **never** a different portfolio (inv. 9, 21; §5.2, §6.3).
- Referenceability is independent of availability (inv. 10).
- Regression: existing portfolio suites (holdings, snapshots, rebuild) stay
  green — Accounting Scopes remain separate (inv. 3).

**Frontend (component/unit):**
- No-default: empty saved selection -> `currentSelection === null` even with
  N>0 portfolios (fixes V1; inv. 20).
- No-fallback: deleting the selected portfolio -> `NONE`, not `remaining[0]`
  (fixes V2; §9.2, inv. 11).
- Rehydrate: saved id that no longer resolves -> `NONE` (§9.2).
- Switch: explicit `selectPortfolio(B)` moves A->B with no cross-portfolio
  state bleed (§9.2, inv. 17).
- Boundary: portfolio-scoped surface with `NONE` renders the empty state and
  issues no portfolio-scoped call (§8.1).

**Manual smoke:** zero / one / many portfolios each behave per §8.1-8.3.

## 8. Rollout strategy

- **Single-user, single-workspace runtime -> minimal blast radius.**
- Ship **Phase 0** first (pure refactor, invisible) to de-risk the resolver.
- Gate **Phase 1's** visible behavior change behind a frontend flag
  (`WORKSPACE_NO_DEFAULT_SELECTION`) so the no-default UX can be validated,
  then remove the flag once accepted.
- No migration ships in this milestone; deploys are code-only.
- Runtime authority for actual deployment remains `NONE` until separately
  granted (project status: "Runtime authority: NOT YET").

## 9. Risk analysis

| ID | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Pages assume non-null `activeId`; `NONE` breaks them | High | High | F3 consumer audit + shared empty-state; flag-gated rollout (§8) |
| R2 | Stale/foreign saved selection resolves to a wrong portfolio | Med | High | Re-validate on rehydrate via resolver; clear to `NONE` (F1/F6) |
| R3 | Scope drift: someone adds a backend `current_portfolio_id` | Med | High | §2 ownership map + review gate: Current Selection is Experience-owned only (§12) |
| R4 | Scope creep: reintroducing the deferred lifecycle field mid-milestone | Med | Med | Lifecycle is explicitly out of M36.1; zero-schema-change is a milestone invariant |
| R5 | "Delete last portfolio" guard vs §8.1 (zero-portfolio workspace is valid) | Low | Low | Resolved: guard kept unchanged in M36.1; relaxation deferred to a later lifecycle/administration milestone |
| R6 | B2 mass refactor regresses an endpoint | Low | Med | Behavior-preserving, characterization tests before/after; incremental replace |

## 10. Blockers

- **No blockers.** M36 is `CLOSED AND CANONICAL`; implementation authority is
  available for M36.1; the runtime is already structurally multi-portfolio.
- **All scope decisions resolved:**
  - No-default Current Selection is strict (NONE + prompt, even for a single
    portfolio).
  - Portfolio Lifecycle State is deferred out of M36.1 (zero schema change).
  - The "cannot delete last portfolio" guard is **kept unchanged** in M36.1.
    A zero-portfolio workspace is architecturally valid (§8.1), but deletion of
    the final portfolio stays product-constrained here; relaxing it is deferred
    to a later portfolio-lifecycle or administration milestone.

## 11. Recommended implementation order

```text
1. Phase 0  (B1, B2, F2)     - resolver consolidation, no behavior change   [de-risk]
2. Phase 1  (F1)             - Current Selection conformance (fix V1, V2)   [core]
3. Phase 2  (F5, F6)         - fail-closed boundary + propagation           [core]
4. Phase 3  (F4)             - single workspace switcher contract           [core]
5. Phase 5  (F3, tests)      - consumer audit + conformance suite           [harden]
```

Phases 0-3 + 5 deliver a fully M36-conformant multiple-portfolio runtime with
no schema change. Portfolio Lifecycle State is a separate later milestone.

## 12. Concrete coding task breakdown (deliverable 2)

Complexity key: **S** = <0.5 day, **M** = ~1-2 days, **L** = multi-day (breadth).

| Task | Phase | Type | Complexity | Depends on | Blocker |
| --- | --- | --- | --- | --- |
| B1 resolver + tests | 0 | Backend | S | - | none |
| B2 replace ~40 inline lookups | 0 | Backend | M | B1 | none |
| F2 `resolvePortfolioReference` + context API surface | 0 | Frontend | S | - | none |
| F1 rewrite `PortfolioContext` (no default/no fallback/revalidate) | 1 | Frontend | M | F2 | product sign-off on no-default UX |
| F5 "select a portfolio" boundary state | 2 | Frontend | M | F1 | none |
| F6 stale-selection -> `NONE` on 404 | 2 | Frontend | S | F1 | none |
| F4 shared workspace switcher | 3 | Frontend | M | F1 | none |
| F3 `NONE`-safety consumer audit (~25 files) | 5 | Frontend | L | F1 | none |
| Frontend conformance tests | 5 | Test | M | F1,F4 | none |
| Backend conformance tests | 0/5 | Test | S | B1 | none |

**Effort shape:** one L (F3 breadth audit), several M (F1/F4/F5/B2), rest S.
The critical path is F2 -> F1 -> (F4/F5) -> F3. Backend is light; the milestone
is frontend-weighted because Current Selection is Experience-owned.

## 13. Success criteria

M36.1 is complete when:

- Current Selection is zero-or-one with `NONE` legal; no first-portfolio
  default (V1 fixed); no automatic fallback on delete (V2 fixed).
- Referenceability flows through one shared resolver expressing §5.2.
- Zero, one, and many portfolios each behave per §8.1-8.3.
- Portfolio-scoped surfaces fail closed to a boundary state, never a silent
  fallback (§6.3).
- Milestone ships with zero database schema change (lifecycle state deferred).
- All conformance tests green; no change to M36 or any frozen M29-M35 artifact,
  no canonical ownership moved, and no deferred concern introduced.

## 14. Retained non-authorizations

This plan creates no runtime authority, no deployment, no governed-action
change, no M33 contract use, and no amendment to M36 or any frozen milestone.
It authorizes implementation work for M36.1 only; runtime rollout remains
`NOT YET` pending separate authorization.

## 15. Verification limitation record (WP4C/WP4D)

This section records a **verification limitation**, not a runtime defect.
Every runtime finding raised across the WP4A-WP4D conformance sweeps (F01-F07)
was resolved and re-verified; the item below concerns only how much of that
resolution can be proven by an executable test versus a bounded code-trace.

**1. Why full optimizer rendering is not executed inside jsdom**

`frontend/app/optimizer/page.tsx` is a ~2900-line page component. Rendering it
in full through `@testing-library/react` under vitest/jsdom exhausts the Node
heap before the test can reach an assertion — this reproduces consistently and
is an environment/tooling limit, not a behavior issue in the page itself.
Extracting the page's async logic into a separately-testable controller/hook
would resolve this, but was judged out of scope for a conformance-completion
pass: it would be a structural change made "solely to satisfy a test," which
the governing missions for this work explicitly prohibit ("do not extract
controllers solely for testing," "this is a completion pass, not a redesign").
The limitation is therefore accepted and documented rather than engineered
around.

**2. Evidence actually obtained**

In place of a full optimizer render, the following executable and code-trace
evidence stands for the request-isolation (F04) and unresolved-portfolio (F03)
guarantees:

- Executable: `frontend/tests/PortfolioContext.test.tsx` — Current Selection
  no-default/no-fallback/rehydrate behavior (V1/V2 fixes).
- Executable: `frontend/tests/WorkspaceScopeSwitcher.test.tsx` — switcher
  contract (explicit selection only, no auto-pick).
- Executable: `frontend/tests/RequestIsolation.test.tsx` — a real F04 consumer
  (`app/ai-analytics/(hub)/human-vs-ai/page.tsx`) exercising the identical
  `requestIdRef`-guard pattern used throughout the optimizer. As of WP4C this
  includes a strengthened A->B race case: B is resolved first and asserted
  rendered, then a late A response for the abandoned selection is resolved
  afterward and asserted **not** to overwrite B's data — proving stale-response
  rejection with distinguishable per-portfolio fixture data, not merely "no
  crash."
- Executable (backend): `backend/tests/test_workspace_referenceability_m36_1_wp4b.py`
  and `..._wp4c.py` — targeted resolver/service-boundary tests proving
  mismatched-workspace lookups are rejected with the pre-existing exception
  type/response shape, for every centralized service (F05).
- Code-trace (not executable): the optimizer's own `selectionRef` (set
  synchronously in the render body, not an effect) and its guarded call sites
  — `loadHistory`, the persona-load effect, the ops-status effect, `handleRun`,
  and `handleSelectHistory` — were verified by direct reading against the same
  pattern proven executable above. This is a bounded, single-file read of the
  exact guarded lines, not a broad assertion of correctness.

**3. Confidence statement**

This is a **verification limitation**, not a known or suspected runtime
defect. No optimizer behavior described above has failed any check performed
against it (manual trace, `tsc --noEmit`, production build, or the isolated
executable coverage of the identical pattern elsewhere). The limitation is
that the optimizer's specific wiring is confirmed by code-trace rather than by
a rendered, executable assertion, and that distinction should be preserved
precisely in any future re-review rather than represented as "tested."
