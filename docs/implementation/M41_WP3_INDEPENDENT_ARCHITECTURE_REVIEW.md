# M41-WP3 — Independent Architecture Review

**Document role:** Independent Architecture Review Board

**Review type:** Independent architectural review (fresh session)

**Review date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP3 — Temporal, Unit, Adjustment, and Arithmetic
Semantics

**Primary review target:**
[M41_WP3_ARCHITECTURE_PROPOSAL.md](M41_WP3_ARCHITECTURE_PROPOSAL.md)

**Review authority:** Architectural fidelity and boundary preservation only.
This board does not redesign WP3, does not introduce implementation detail,
and does not evaluate future WP4 design.

---

## 1. Executive Summary

The M41-WP3 Architecture Proposal is a faithful, in-allocation continuation of
the frozen M41 Architecture. Its declared scope matches the frozen
M41-WP3 charter clause verbatim in substance
([M41_ARCHITECTURE_PROPOSAL.md](M41_ARCHITECTURE_PROPOSAL.md), lines
222–224): *"cutoff/window, timezone/calendar, missing-data, unit/currency,
adjustment, decimal/rounding, and dependency specifications, each closed
against"* the determinism criterion. It adopts, without alteration, the frozen
exit condition — **"no ambient semantic default remains"** — and the required
**numerical and architectural** review mode
([M41_ARCHITECTURE_PROPOSAL.md](M41_ARCHITECTURE_PROPOSAL.md) lines 474, 490,
537).

The proposal preserves every previously frozen authority. It consumes WP1 and
WP2 contracts strictly by exact reference, adds no field to any frozen record,
does not construct or reorder the WP2 Manifest, does not strengthen M39
evidence, and explicitly defers the entire WP4 Result/Provenance/temporal-claim
surface. All work-package headers carry `NONE` for implementation, runtime,
provider, persistence, API, and production-method authority. The Stage A /
Stage B decomposition is a governance decomposition internal to the single
frozen WP3 work package, not a new milestone work package, and it faithfully
implements the allocated scope.

The cited upstream sections were verified to exist and to say what the proposal
represents them to say. The repository is unchanged: no frozen artifact,
Glossary, Decision Log, Implementation Index, or Graphify output is modified;
the only new file is the proposal itself.

**Final determination: APPROVED.** No required corrections. Two non-blocking
observations are recorded in §4.3 for the drafting team's awareness only; they
do not gate this approval and impose no obligation on Stage A.

---

## 2. Review Scope

This review verifies, and only verifies, that the proposal:

1. matches the frozen M41-WP3 allocation and does not reopen WP1 or WP2;
2. leaves WP1 responsibilities unchanged;
3. leaves WP2 responsibilities unchanged;
4. does not pull WP4 responsibilities forward;
5. keeps ownership boundaries singular and explicit;
6. introduces no new governed vocabulary without authority;
7. allocates temporal, unit, adjustment, arithmetic, and dependency semantics
   only within WP3 authority;
8. introduces no implementation, runtime, provider, persistence, API, or
   production authority;
9. proposes a Stage A / Stage B decomposition that faithfully implements the
   allocated WP3 scope; and
10. keeps repository governance consistent.

Explicitly out of scope for this board: redesigning WP3, supplying
implementation detail, and assessing future WP4 design.

---

## 3. Repository Validation

| Frozen artifact | Expected state | Verified state |
|---|---|---|
| M41 Architecture (proposal, review, corrections, confirmation) | Unchanged | Unchanged — not in working-tree diff |
| M41-WP1 corpus (register, Stage 2 contract, confirmations, closeout) | Unchanged | Unchanged — not in working-tree diff |
| M41-WP2 corpus (architecture, Stage A, Stage B contract, confirmations) | Unchanged | Staged from prior work; content unmodified by this proposal |
| `docs/GLOSSARY.md` | Unchanged | Unchanged — not touched |
| Decision Log | Unchanged | Unchanged — not touched |
| Implementation Index | Unchanged | Unchanged — not touched |
| Graphify output | Unchanged | Unchanged — not touched |
| New file | Only the WP3 proposal | `docs/implementation/M41_WP3_ARCHITECTURE_PROPOSAL.md` is the sole untracked addition |

The proposal's §13 self-declaration ("creates only the proposal; modifies no
frozen artifact, Glossary, Decision Log, Index, Graphify, or source") is
consistent with the observed working tree. Decision Log reconciliation and
Graphify refresh are correctly deferred to post-WP4 Epic Closeout.

**Cross-reference existence checks (spot-verified):**

- WP1 Register **§6.5 Measurement Window** exists, is disposed `ADMIT`, and
  already assigns to WP3 the obligation to supply "the exact calendar/timezone
  resolution rule and a golden vector proving no ambient default remains." The
  proposal's Component A discharges exactly this without renaming or redefining
  the noun.
- WP1 Stage 2 **§5 (Definition)**, **§6 (Method Version)**, **§7 (Method
  Requirement / Applicability)** exist as cited.
- WP2 Stage B **§4 (Measure Subject)** and **§5 (Observation Input Manifest,
  incl. §5.3 Manifest Entry)** exist as cited.

---

## 4. Findings

### 4.1 Objective-by-objective determination

| # | Objective | Determination | Basis |
|---|---|---|---|
| 1 | Scope matches frozen M41 allocation; no WP1/WP2 reopening | **Pass** | §1 executive determination and §1 "WP3 owns / does not own" lists mirror the frozen charter clause; §0 non-reopening rule enumerates the fixed WP2 contracts |
| 2 | WP1 responsibilities unchanged | **Pass** | §3.2 and §6.4 bind semantics to the existing Method Version semantic-version and declared dependency-version list, adding no field; Method Requirement's three categories and binary result are held closed |
| 3 | WP2 responsibilities unchanged | **Pass** | §6.5 forbids changing Manifest bytes, membership, identity, ordering; §4.2 defines a *separate* semantic calculation ordering over immutable entries and explicitly refuses to re-sort WP2 bytes |
| 4 | WP4 not pulled forward | **Pass** | §4.9, §5.1, §6.6, §8 defer Measure Value, Result identity, Provenance, Canonical Temporal Claim construction, reason-code vocabulary, partial-result composition, and the outcome/degraded-state matrix |
| 5 | Ownership singular and explicit | **Pass** | §5.1 singular-ownership matrix and §5.2 five-part gate assign exactly one owner per concern |
| 6 | No new governed vocabulary without authority | **Pass** | §2.1 preserves WP1 classifications; §9 Stage A expects "no new governed noun" and routes any genuine candidate through the full frozen five-stage workflow before reliance |
| 7 | Semantics allocated only within WP3 authority | **Pass** | Components A–I in §4 stay within temporal/missing-data/unit/adjustment/arithmetic/dependency closure and cite, not redefine, Unit Semantics and Structural Event |
| 8 | No implementation/runtime/provider/persistence/API/production authority | **Pass** | Header block sets all to `NONE`; §7 authorizes documentation/data fixtures only; §8 excludes code, kernels, resolvers, endpoints, schemas |
| 9 | Stage A / Stage B faithful to allocation | **Pass** | §9 stages are internal governance stages, not new work packages; Stage A = vocabulary-sufficiency register, Stage B = the normative contract of §§3–7 with the full §7.1 golden-vector matrix |
| 10 | Repository governance consistent | **Pass** | §13 and the verified working tree agree; deferral of Decision Log / Graphify is correct |

### 4.2 Boundary-preservation confirmations

- **Measurement Window is concretized, not re-typed.** The proposal keeps it an
  input-selection boundary bounding Manifest membership and repeatedly bars it
  from becoming a Canonical Temporal Claim or a field of Subject/Manifest
  (§3.1, §4.1, §6.1, Risk row 2). This matches WP1 §6.5's own constitutional
  constraints.
- **M39 immutability preserved.** §5.3 and §6.2 forbid merging identity-distinct
  Observations, fabricating precision from date-only evidence, filling absent
  source meaning, or letting interpolation/normalization/adjustment mutate an
  Observation. Derived working values are explicitly barred from masquerading as
  witnessed evidence and from entering the Manifest.
- **Computation Outcome reuse only.** §4.9 maps every WP3 rejection to the
  already-frozen `INSUFFICIENT_INPUT`, `DEPENDENCY_UNRESOLVED`, or `FAILED`
  meanings and creates no fifth outcome; it correctly leaves the success value
  and the Result envelope to WP4.
- **No implicit FX, no ambient clock/locale, no default calendar.** §4.3–§4.5
  and §6.3 forbid machine timezone/locale, weekday-as-calendar, a 252-session
  assumption, base-currency inference, and provider fallback.
- **No Dependency Manifest noun.** §4.8 uses the existing Method Version
  declared dependency-version field as the sole inventory and creates no
  registry, resolver, or loader.

### 4.3 Non-blocking observations (advisory only — not corrections)

1. **Stage A candidate pre-emption language.** §2.1 and §9 state that no future
   candidate is pre-owned or pre-admitted and route any genuine candidate
   through the full five-stage workflow. This is correct and sufficient. As a
   drafting note only, Stage A should ensure its "expected result: no new
   governed noun" phrasing is written as an *expectation to be tested*, not a
   *predetermined conclusion*, so the register remains a genuine sufficiency
   proof. No architectural change is required.
2. **Cross-dimension ordering proof burden.** §4.9 requires one exact
   processing order proven by "at least one non-commutative golden vector."
   This is architecturally adequate. As an advisory, the drafting team may find
   that unit-normalization/adjustment/interpolation/arithmetic interactions
   need more than a single vector to demonstrate the order fully; this is a
   Stage B sufficiency matter for the numerical reviewer, not an architecture
   defect.

Neither observation identifies a boundary violation, a scope overreach, an
authority leak, or a reopening of frozen material. They are recorded solely for
the drafting and Stage B numerical-review teams.

---

## 5. Final Determination

**APPROVED.**

The M41-WP3 Architecture Proposal faithfully implements the scope allocated by
the frozen M41 Architecture and preserves all previously frozen authorities
(platform/Asset Foundation, M34, M39, M40, M41 Architecture, M41-WP1,
M41-WP2). It introduces no new governed vocabulary without routing it through
the frozen workflow, allocates temporal/unit/adjustment/arithmetic/dependency
semantics only within WP3 authority, does not pull WP4 responsibilities
forward, and introduces no implementation, runtime, provider, persistence, API,
or production authority. Repository governance is consistent and no frozen
artifact is modified.

No required corrections are issued. The two items in §4.3 are non-blocking
advisories for the drafting team and impose no gate.

Per the proposal's own §10 sequence, WP3 may now proceed to Independent
Architecture Confirmation and, upon unconditional confirmation and freeze, to
Stage A drafting.

---

## Final Status

**APPROVED**
