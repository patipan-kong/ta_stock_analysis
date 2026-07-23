# M40-WP1 — Independent Specification Review

**Review date:** 2026-07-23

**Reviewer role:** Independent specification reviewer (fresh session; not the
author of WP1, the M40 architecture proposal, the prior constitutional
review, the review response, or the independent confirmation).

**Artifact reviewed:** [M40-WP1 — Canonical Market Measure Vocabulary and Ownership Specification](M40_WP1_Canonical_Market_Measure_Vocabulary_and_Ownership_Specification.md)
(status `COMPLETE_FOR_WP2_CONSTITUTIONAL_ADMISSION_REVIEW`, not yet approved).

**Judged against:** [Platform Architecture](../architecture/platform_architecture.md)
§5–§7 (layers, domains, dependency law, gates); [Canonical Glossary](../GLOSSARY.md)
(`Canonical Temporal Claim`, `Event Type`, `Producing Domain`, `Degraded State`,
`Market Observation`, `Investment Judgment`); [M34 Decision Register](m34/audit/registers/decision_register.md)
`M34-D-0004`, `M34-D-0005`, `M34-D-0010`; and the frozen M39 corpus
(WP1–WP6, [Epic Closeout](M39_EPIC_CLOSEOUT.md)). Governing text was read
directly, not assumed from WP1's own citations.

**Scope discipline:** This review evaluates WP1 only. It does not redesign
M40, does not review the M40 architecture proposal or WP2+ work packages on
their own merits, and does not reopen the four Required Corrections already
closed by the independent confirmation — it treats that confirmation as
settled and asks only whether WP1, as a downstream artifact, correctly
operationalizes it.

---

## 1. Executive Assessment

WP1 is a disciplined, mechanically-minded specification that gets the hard
parts right: every term is explicitly non-canonical, every term carries
exactly one candidate owner, the Observation/Calculation split is preserved
rather than re-litigated, the `UNAVAILABLE` collision fixed by the prior
correction round stays fixed, and §10 correctly disclaims every adjacent
authority (formula, implementation, runtime, provider, persistence, API,
production method).

Two defects nonetheless survive independent testing of the ownership model:

1. the §7.1 admission predicate — the actual pass/fail gate — has no row that
   tests for Wealth Intelligence leakage, even though §7.2's routing matrix
   and the Platform Architecture both recognize Wealth Intelligence as an
   exclusive owner of goal/net-worth/life-plan meaning reachable from Market
   Intelligence's own "Provides" list; and
2. `Input Sufficiency` (§6.8) is lexically and semantically adjacent to the
   frozen M39-WP4 term `Semantic Sufficiency` — both Market-Intelligence-owned,
   both answering "is there enough data" — and WP1 nowhere reconciles or
   distinguishes them, despite demonstrating the correct discipline for doing
   exactly this elsewhere (`Observation` vs `Calculation`, `UNAVAILABLE` vs
   `DEPENDENCY_UNRESOLVED`).

Neither defect creates authority leakage, ownership overlap that survives to
runtime, or a constitutional contradiction. Both are fixable inside WP1
without touching the ten-term set's substance. **Verdict: APPROVED WITH
REQUIRED CORRECTIONS.**

---

## 2. Vocabulary Findings

- The ten candidate terms (§6.1–§6.10) match the count asserted in §9 and
  the Purpose statement. No term is defined twice; no term is left with a
  dangling reference.
- The `Observation` vs `Calculation` Event Type split (§4.1, §6.2) is
  applied consistently everywhere it recurs (§6.4, §6.5, §7.1, §8.1, §8.3)
  and matches the Glossary's approved `Event Type` enumeration (`Observation,
  Retrieval, Calculation, Analysis Generation, Snapshot Creation, Batch
  Evaluation, Synchronization` — verified directly in `GLOSSARY.md`). No new
  Event Type is invented.
- `Computation Outcome` (§6.3: `SUCCEEDED`, `INSUFFICIENT_INPUT`,
  `DEPENDENCY_UNRESOLVED`, `FAILED`) and `Degraded State` (Glossary:
  `UNKNOWN`, `UNAVAILABLE`, `DELAYED`, `STALE`, `PARTIAL`, `CONFLICTING`) no
  longer share a token. The prior `UNAVAILABLE` collision is verifiably
  fixed, and §6.3/§8.2 correctly keep the two axes orthogonal.
- **Finding (moderate) — undeclared collision with a frozen M39 term.**
  `Input Sufficiency` (§6.8) is defined as "the deterministic classification
  of whether every declared prerequisite for the specified calculation is
  satisfied by the exact supplied canonical inputs," owned by Market
  Intelligence. M39-WP4's frozen `Semantic Sufficiency` (verified directly in
  `M39_WP4_market_observation_payload_specification.md` §4.6) is "the
  condition in which the canonical fact content preserves enough
  source-established meaning," also owned by Market Intelligence. Both terms
  use "Sufficiency" to mean "is there enough X," both belong to the same
  domain, and neither WP1 nor its §8.3 terminology-reservation list
  distinguishes them or forbids conflating them. WP1 demonstrably knows how
  to perform this reconciliation — it did so explicitly for `Observation`
  versus `Calculation` — but did not do it here.
- **Finding (minor) — two already-canonical terms are candidate-labeled.**
  `Producing Domain` (§6.5) and the four-field shape of `Calculation Temporal
  Claim` (§6.4) are not new vocabulary; `Canonical Temporal Claim`, `Event
  Type`, `Producing Domain`, and `Degraded State` are already canonical and
  governed by `M34-D-0005` (verified in `GLOSSARY.md`). WP1 is only fixing
  `Producing Domain`'s *value* to `Market Intelligence` for the M40 case and
  reusing the existing four-field grammar. Labeling the whole term
  "candidate vocabulary... subject to admission" overstates what WP2 must
  actually approve (a value assignment, not a new concept) and could cause a
  future reader to think the temporal grammar itself is up for renegotiation.
  Harmless in direction (over-caution, not overreach) but imprecise.

## 3. Ownership Findings

- Every term in §6 has exactly one named owner, and every "Non-owner" list
  is populated (no term is silently ownerless).
- The §4 Frozen Ownership Baseline correctly excludes Ledger & Accounting,
  Portfolio Intelligence, Decision Intelligence, Trust & Evaluation, and
  Experience Platform from Market Measure semantics, matching Platform
  Architecture §6.3, §6.5–§6.7, §6.9 exactly as verified.
- **Finding (moderate) — Wealth Intelligence has no baseline row.** §4 gives
  every other adjacent domain its own preservation row but has none for
  Wealth Intelligence, even though Platform Architecture §6.2 states Market
  Intelligence "Provides... Wealth Intelligence (planning assumptions),"
  meaning a Calculated Market Measure could plausibly feed a Wealth
  Intelligence planning input. §7.2's routing matrix does catch this
  ("Household, person, goal, net worth, or life-plan meaning | Wealth
  Intelligence or other existing owner | Outside M40"), so the omission is
  not fatal to the ownership model as a whole — but see §4 of this review
  for why it becomes a real gap once the actual admission gate (§7.1) is
  examined.
- No term claims shared ownership, and no term's "Permitted inputs" secretly
  admits a forbidden category through a different name.

## 4. Boundary Findings

- **Finding (required correction) — §7.1's admission predicate has no Wealth
  exclusion row.** §7.1 states plainly: "A candidate qualifies for the M40
  Market Measure boundary only when every row is `PASS`," and this is the
  operative gate WP2 is instructed to run (§7.4 step 5, §9 condition 5). Its
  twelve rows test Portfolio exclusion ("No Portfolio subject, membership,
  holding, transaction, cash flow, attribution, exposure, allocation, or
  performance meaning exists"), Judgment exclusion, Evaluation exclusion, and
  Authority exclusion — but no row tests for household/goal/net-worth/
  obligation/protection meaning, i.e. Wealth Intelligence's exclusive
  vocabulary (Platform Architecture §6.8). A candidate that leaks into
  Wealth Intelligence meaning without also tripping the Portfolio row (e.g.,
  a "market context relevant to a goal horizon" measure that touches no
  ledger, holding, or attribution concept) could pass all twelve §7.1 rows
  and only be caught later, informally, by the §7.2 table — which §7.4's own
  procedure applies only *after* §7.1 in principle, but which is not itself
  phrased as a pass/fail gate the way §7.1 is. This is a real hole in the
  "fail-closed" claim the document makes for itself in §6.10 and §9 condition
  5.
- Every other boundary in §7.2's routing matrix (external Observation,
  Asset identity, Ledger, Decision Intelligence, Trust & Evaluation,
  Experience, provider/runtime, authority) is complete and correctly
  disjoint from the §7.1 predicate rows that already cover the same ground.
- §7.3's seven non-overlap invariants are consistent with §4 and §7.2 and add
  no new claim beyond what those two sections already establish.
- §7.4's nine-step decision procedure is sound and closes with the required
  three-way disposition (`ELIGIBLE_FOR_ADMISSION_REVIEW` / sole owner /
  `INADMISSIBLE`) with no fourth, shared-ownership option — correctly
  fail-closed in its own terms, modulo the Wealth-row gap above.

## 5. Authority Findings

- §10's non-leakage list was checked term-by-term against §6: no term's
  "Permitted inputs" or "Semantic meaning" field smuggles in a formula,
  calculation method, storage mechanism, provider adapter, transport
  concern, or authorization grant. "Stable content digests" in §6.6 is the
  only field that brushes against an implementation concept (a digest
  implies *some* computation), but it is scoped strictly to identity
  preservation of already-frozen M39 evidence, not to a mandated algorithm,
  storage location, or persistence claim — this is acceptable as written and
  is noted only as a candidate for a clarifying footnote, not a defect.
- No term creates Decision Log, Graphify, or closeout authority, and none is
  invoked anywhere in the document.
- Nothing in WP1 modifies M39's frozen corpus, the Platform Architecture, the
  Canonical Glossary, or the M34 Decision Register; all are read and cited,
  never amended.

## 6. Risks

| Risk | Severity | Where it could surface |
| --- | --- | --- |
| Wealth Intelligence leakage undetected by the §7.1 gate | Moderate | A future WP (e.g., a "market context for goal horizon" measure) is admitted under M40 vocabulary when it should route to Wealth Intelligence |
| `Input Sufficiency` / `Semantic Sufficiency` conflation | Moderate | A future implementer or WP2 reviewer treats "enough observation payload" and "enough calculation input" as the same gate, silently merging an M39-frozen concept with an M40-candidate one |
| Over-labeling already-canonical grammar as "candidate" | Low | WP2 spends review effort re-approving the four-field temporal grammar itself instead of only the value assignment, wasting but not endangering the gate |

## 7. Required Corrections

1. **Add a Wealth exclusion row to §7.1.** Insert a predicate row (parallel
   to the existing Portfolio exclusion row) testing that no household,
   person, goal, net worth, obligation, protection, or life-plan meaning
   exists in the candidate's subject, inputs, or output claim, routing
   failure to Wealth Intelligence. This closes the gap between §7.1 (the
   actual pass/fail gate) and §7.2 (the routing matrix), and makes §6.10's
   "fail-closed" claim true of the gate WP2 is actually instructed to run.
2. **Reconcile `Input Sufficiency` (§6.8) with M39-WP4's frozen `Semantic
   Sufficiency`.** Add a sentence — in the same style already used for
   `Observation` vs `Calculation` in §4.1 and §8.3 — stating that `Semantic
   Sufficiency` governs whether an Observation payload preserves enough
   source-established meaning to be admitted as M39 evidence, while `Input
   Sufficiency` governs a distinct, later question: whether a calculation's
   own declared prerequisites are satisfied by the inputs supplied to it.
   Add this pairing to §8.3's terminology reservations so the distinction is
   enforced, not merely asserted once.

## 8. Recommended Improvements

1. Reframe §6.4/§6.5 to state plainly that the Canonical Temporal Claim
   four-field grammar, `Event Type`, and `Producing Domain` are already
   canonical (`M34-D-0005`), and that what WP2 is actually asked to admit is
   the *value assignment* (`Event Type = Calculation`, `Producing Domain =
   Market Intelligence`) for the M40 case — not the grammar itself. This
   would tighten WP2's review scope without weakening it.
2. Add one clause to §6.6 clarifying that "stable content digest" describes
   an identity-preserving reference property only, and admits no digest
   algorithm, storage medium, or persistence claim — removing the one field
   in the document that reads, even faintly, as implementation-flavored.
3. Consider naming `Input Sufficiency`'s two-value set (`SATISFIED` /
   `INSUFFICIENT`) further from `Computation Outcome`'s `INSUFFICIENT_INPUT`
   than the current near-identical strings allow, to reduce the same class
   of lexical-collision risk the document elsewhere took care to eliminate
   (e.g., `UNAVAILABLE` → `DEPENDENCY_UNRESOLVED`). This is not required
   because the two axes are already explicitly declared orthogonal in §8.2,
   but tighter naming would remove even the appearance of collision.

## 9. Final Recommendation

**APPROVED WITH REQUIRED CORRECTIONS.**

WP1's ownership model, boundary predicates, and authority disclaimers are
substantively sound and correctly preserve every frozen M39 and platform
constitutional boundary they touch. It does not, however, fully survive an
adversarial test of its own "fail-closed" claim: the Wealth Intelligence
exclusion exists only in an informal routing table, not in the actual §7.1
admission gate, and one candidate term (`Input Sufficiency`) is left
undistinguished from an already-frozen, lexically adjacent M39 term in a
domain that has otherwise been careful to perform exactly this kind of
reconciliation. Both corrections are narrow, additive, and resolvable without
altering the ten-term set, the boundary architecture, or any admission
requirement already in place. Until both are made, WP2 should not treat §7.1
as a complete gate or treat §6.8 as unambiguous with respect to M39-WP4.

---

## Validation

- **Markdown / heading validation:** headings are sequential and
  well-formed (`#` → `##`, no skipped levels); no unclosed emphasis or code
  fences.
- **Link validation:** all outbound links (Platform Architecture, Canonical
  Glossary, M34 Decision Register, all six M39 work packages, M39 Epic
  Closeout, and the WP1 specification itself) were confirmed to exist on
  disk before being cited.
- **`git diff --check`:** clean (see below).
- **Scope confirmation:** this document is the only file created by this
  review. The WP1 specification, the M40 proposal, the prior independent
  review, the review response, the independent confirmation, the Decision
  Log, and the Canonical Glossary are all unmodified. No Graphify refresh
  and no closeout were performed. Nothing was committed or pushed.
