# M41-WP4 — Independent Architecture Review

**Document role:** Architecture Review Board (independent, fresh session)

**Reviewed artifact:** [`docs/implementation/M41_WP4_ARCHITECTURE_PROPOSAL.md`](M41_WP4_ARCHITECTURE_PROPOSAL.md)

**Review date:** 2026-07-24

**Milestone:** M41 — Governed Market Measure Semantics

**Work package:** M41-WP4 — Result, State, and Provenance Model

**Reviewer independence:** This review treats the proposal's author as a
separate party. It does not rewrite the proposal and proposes no redesign
except where a constitutional or internal-consistency defect requires it.

**Scope of review:** Only `M41_WP4_ARCHITECTURE_PROPOSAL.md`. Stage A, Stage B,
implementation, and runtime are explicitly out of scope.

---

## 1. Determination

**APPROVED WITH REQUIRED CORRECTIONS**

The proposal's scope, ownership boundaries, stage decomposition, review gates,
closeout conditions, and Epic-Closeout dependency chain are sound and match the
frozen M41 Architecture §6 allocation and the WP2/WP3 governance shape. All
authority fields remain `NONE`. No frozen decision is reopened and no governed
vocabulary is silently redefined.

Two required corrections must be resolved before the WP4 Architecture may be
frozen. **RC-1** is a genuine internal-consistency defect: the proposal
simultaneously composes a `Calculation` Canonical Temporal Claim into the
identity-bearing Result and requires Result identity to exclude computation
time, without reconciling the two — a conflict Stage B cannot resolve on its own
authority. **RC-2** is a mis-citation of the frozen WP3 handoff location, which
matters because the proposal's own discipline is exact, citation-only
consumption of frozen upstream authority.

Neither correction requires redesign. Both are minimal, additive
clarifications.

---

## 2. What the review verified as correct

The following claims were checked against the frozen sources, not accepted on
assertion:

- **Computation Outcome reuse.** The proposal uses exactly the four frozen
  values `SUCCEEDED` / `INSUFFICIENT_INPUT` / `DEPENDENCY_UNRESOLVED` /
  `FAILED` and creates no fifth outcome
  ([`GLOSSARY.md` Computation Outcome](../GLOSSARY.md)). Confirmed.
- **Market Measure Result reuse.** The proposal adds no meaning beyond the
  frozen M40 admission — "one immutable, owner-explicit semantic outcome …
  contains required calculated values only for `SUCCEEDED`"
  ([`GLOSSARY.md` Market Measure Result](../GLOSSARY.md)). Confirmed; the
  present-iff-`SUCCEEDED` invariant (Component B) matches the frozen entry.
- **Measure Value / Provenance ownership.** The §2 citations to
  [WP1 Candidate Register §6.6 (Measure Value `ADMIT`)](M41_WP1_CANDIDATE_VOCABULARY_AND_OWNERSHIP_REGISTER.md#66-measure-value)
  and §6.8 (Provenance `REUSE`, owned by Connectivity & Ingestion) are accurate.
  WP4 correctly positions itself as the first *relying* work package on Measure
  Value and a *carrier* — never owner — of Provenance.
- **WP3 handoff coordinates.** Component H (§6.8) reproduces the frozen WP3
  §14.6 handoff verbatim — "Measurement Window bytes/identity, exact semantic
  and dependency versions, exact qualified canonical arithmetic bytes on
  success, or one frozen outcome classification"
  ([WP3 Stage B §14.6](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md)).
  Confirmed no re-derivation is claimed.
- **Total classification consumption.** WP3 §12.1 total mapping onto the four
  Computation Outcome values exists and explicitly states it "does not define
  Result contents, reason representation, partial values, or degraded-state
  interaction" — i.e. WP3 genuinely defers those to WP4. The Component C
  "consume, do not re-classify" boundary is therefore real, not overlapping.
- **Snapshot Creation exclusion.** `Snapshot Creation` is a frozen Event Type
  value ([`GLOSSARY.md` Event Type](../GLOSSARY.md)); the WP1 register §6 note
  already records it as a reserved-boundary exclusion. WP4 treats it as an
  exclusion rule, not a new noun. Confirmed.
- **Degraded State reuse.** Degraded State is a closed frozen enum
  (`UNKNOWN`/`UNAVAILABLE`/`DELAYED`/`STALE`/`PARTIAL`/`CONFLICTING`), so the
  Component D "total (outcome × degraded-state) matrix" is finitely enumerable
  and well-posed. Confirmed.
- **Completion-test provenance.** §1's "hash stability, no-value-on-failure,
  complete lineage, canonical serialization round-trips" reproduces
  [M41 Architecture §12](M41_ARCHITECTURE_PROPOSAL.md) verbatim; the
  specification-only / no-committed-test-runner posture matches §13. Confirmed.
- **Responsibility assignment.** Every M41 Architecture §4/§6 WP4-allocated
  responsibility (Measure Value, Computation Outcome closure,
  outcome/degraded-state matrix, Result identity, reserved Snapshot boundary,
  Provenance model) is assigned exactly once in the §3.2 and §5.1 matrices. No
  cell is owned twice; no residual responsibility is left unassigned. Confirmed.
- **Authority posture.** Implementation, runtime, provider, persistence, API,
  production-method, and executable-validation authority are all `NONE`, and
  §4/§14 reinforce this. No hidden implementation requirement is created.
  Confirmed.

---

## 3. Required Corrections

### RC-1 — Result identity vs. the composed `Calculation` temporal-claim timestamp is unreconciled

**Affected sections:** §1 item 7; §6.1 (Component A); §6.5 (Component E);
§6.7 (Component G); §8.3 minimum-vector matrix ("Identity independence"); §11
acceptance criterion 7.

**Constitutional reason.** Under `M34-D-0005`, a Canonical Temporal Claim
"contains exactly … an authoritative timestamp," and Event Type `Calculation`
dates *when the calculation event occurred*
([`GLOSSARY.md` Canonical Temporal Claim / Event Type](../GLOSSARY.md)).
M40 Deterministic Calculation requires byte-identical output for identical
canonical inputs, and the frozen Market Measure Result entry states "identical
canonical semantic inputs and versions identify the same semantic result."

**Why repository consistency requires the correction.** The proposal makes
three statements that cannot all hold as written:

1. §6.1 (Component A) composes the **Canonical Temporal Claim** into the Result
   as a required coordinate, and §6.5 (Component E) fixes its Event Type to
   `Calculation` — whose authoritative timestamp is, by the frozen grammar, the
   calculation instant.
2. §6.7 (Component G) defines the canonical serialization to include
   "timestamp/temporal-claim encoding," and then defines **Result identity** as
   "a function of the canonical bytes only."
3. The same §6.7 bullet, the §8.3 "Identity independence" vector, and §11
   criterion 7 require identity to **exclude** "computation time," so that two
   Results differing only in computation time share one identity.

If the temporal-claim timestamp participates in the identity-bearing canonical
bytes, then two deterministically identical calculations run at different
instants produce different bytes and different identity — violating (3), the
§8.3 hash-stability vector, and the frozen "same inputs → same result" rule. If
it does not participate, then identity is *not* "a function of the canonical
bytes only" and a composed coordinate is silently excluded from identity —
contradicting (2). §6.5 actively separates the Result's temporal claim from the
deterministic Measurement Window ("the two are not the same field"), which
removes the one reading (a window-derived, deterministic timestamp) that would
have dissolved the conflict. As written, Stage B could satisfy any one of these
requirements while violating another and still claim conformance, and the §15
decisive test — two independent readers deriving "the same Result bytes and the
same Result identity" — is unreachable.

This is an architecture-layer ruling, not a Stage B contract detail: Stage B
must be told which coordinates feed identity before it can specify
serialization.

**Minimal correction required.** Add one explicit architectural rule to §6.7
(and reflect it in §1 item 7) stating that the authoritative timestamp
component of the Result's Canonical Temporal Claim — like every other
operational coordinate — **does not participate in Result identity**; that
Result identity is computed over an identity-bearing canonical form comprising
the lineage and version coordinates only; and that hash-stability and
round-trip are defined over that identity-bearing form. (Equivalently, the
proposal may instead rule that the `Calculation` claim's timestamp is derived
deterministically from frozen input coordinates and carries no wall-clock
instant — but if so, §6.5's separation of the temporal claim from the
Measurement Window must be reconciled with that derivation.) No component need
be redesigned; one disambiguating sentence closes the conflict.

### RC-2 — Partial-output deferral is cited to the wrong WP3 section

**Affected sections:** §1 item 8; §6.9 (Component I).

**Constitutional reason.** The proposal's governing discipline (§0, §2, §6.8,
§9.4, acceptance criterion 9) is that WP4 "consumes the WP3 handoff by exact
reference without re-derivation." A frozen architecture document that mis-points
its controlling upstream citation propagates the wrong pointer into Stage A and
Stage B, which are instructed to close "the case WP3 §4.4 left to the Result
contract."

**Why repository consistency requires the correction.** §1 item 8 and §6.9
attribute the partial-output deferral to **"WP3 §4.4."** WP3 §4.4 is
"Multi-role alignment and stable ordering" and contains no partial-output rule.
The actual deferral is
[WP3 Stage B §6.1](M41_WP3_STAGE_B_TEMPORAL_UNIT_ADJUSTMENT_ARITHMETIC_CONTRACT_SPECIFICATION.md):
"`independently_complete_coordinates` is permitted only when the frozen Market
Measure Definition declares separable output coordinates and WP4 permits their
Result composition. This artifact does not grant either permission," reinforced
by the §12.1 note that WP3 "does not define … partial values." A frozen WP4
architecture must cite the section that actually performs the deferral.

**Minimal correction required.** Replace "WP3 §4.4" in §1 item 8 and §6.9 with
"WP3 §6.1 (and the §12.1 note reserving partial values to the Result
contract)." No semantic change.

---

## 4. Advisory Observations

These are not blocking. They flag risks Stage A / Stage B should retire; the
architecture may freeze without acting on them.

**AO-1 — Disambiguate the `PARTIAL` Degraded State token from partial-output
composition.** Component D's matrix ranges over the frozen Degraded State enum,
which includes `PARTIAL`; Component I introduces "partial-output / partial-result
composition." These are different concepts (a degraded-availability
qualification vs. a Definition declaring separable output coordinates), and V1
(one term, one meaning) is at risk if Stage B lets them blur. Stage B should
state explicitly whether a partial-output Result must, may, or must not carry
Degraded State `PARTIAL`, so the two never conflate.

**AO-2 — Route the optional reason-representation field through the Stage A
candidate determination.** §4 permits "a reason *representation* field on the
Result … [that] adds no new governed noun." This is the single most likely
place a new governed taxonomy enters WP4 (WP3 §12.1 explicitly leaves "reason
representation" undefined). §7.1 scopes the Stage A register to "one row per
component in §6," but reason representation is not one of the nine components
and could be missed. Stage A should carry an explicit row giving the
reason-representation field a candidate-vocabulary determination, even if that
determination is "no new noun."

---

## 5. Consistency checks performed

| Dimension | Result |
|---|---|
| Internal / section consistency | Consistent except RC-1 (identity vs. temporal-claim timestamp). |
| Ownership consistency (§3.2, §5.1 matrices) | Every WP4-owned cell assigned once; no double ownership; no gap. |
| Terminology consistency | All governed nouns match frozen Glossary / WP1–WP3 spelling and meaning. |
| Authority consistency | All authority fields `NONE`; §4/§14 reinforce; no hidden implementation requirement. |
| Boundary consistency (§5.2 gate, §5.3 witnessed-vs-computed) | Sound; five-part gate carried forward from M41 Architecture §8. |
| Dependency consistency | WP3 handoff (§6.8) matches WP3 §14.6 verbatim; upstream deferral citation wrong only at RC-2. |
| Stage consistency | Stage A / Stage B / closeout mirror the confirmed WP2 and WP3 shape. |
| Acceptance-criteria consistency (§11) | 15 criteria coherent; criterion 7 is the one exposed by RC-1. |
| Closeout consistency (§12, §13) | Documentation-only; Decision Log / Graphify correctly deferred to Epic Closeout; no semantics added. |
| Epic-Closeout dependency | §10/§13 chain is sound: WP4 is terminal; Epic Closeout gated on WP4 confirmation; no closeout action authorized here. |

---

## 6. Statement of authority

This review grants **no** implementation, runtime, provider, persistence, API,
production-method, or executable-validation authority. All such authority
remains `NONE`.

Because the determination is **APPROVED WITH REQUIRED CORRECTIONS**, the WP4
Architecture is **not yet** frozen and Stage A may **not** begin until RC-1 and
RC-2 are resolved and the resolution is independently confirmed. Upon
unconditional confirmation of both corrections:

- the WP4 Architecture may be frozen and Stage A (Vocabulary and Semantic
  Surface Register, §7.1) may begin;
- no implementation authority is thereby created; and
- Stage B, and any later phase, remain gated behind their own review chains.

---

**Final determination: APPROVED WITH REQUIRED CORRECTIONS**

End of independent architecture review.
