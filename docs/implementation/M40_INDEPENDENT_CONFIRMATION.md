# M40 — Independent Confirmation of Review Corrections

**Confirmation date:** 2026-07-23

**Reviewer role:** Independent constitutional architecture reviewer (author of
the prior review; not the proposal author).

**Nature of this document:** Confirmation that the Required Corrections issued
in the prior review are resolved. It is **not** a new architecture review and
introduces no new review criteria.

**Artifacts assessed:**

- Updated proposal — [M40 — Canonical Asset Market Measure Foundation](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md)
- Author response — [M40 — Response to Independent Constitutional Architecture Review](M40_REVIEW_RESPONSE.md)

**Judged against:** the prior [Independent Constitutional Architecture Review](M40_INDEPENDENT_CONSTITUTIONAL_ARCHITECTURE_REVIEW.md)
(verdict `APPROVED WITH REQUIRED CORRECTIONS`) and the governing repository
authority it cited — [Platform Architecture](../architecture/platform_architecture.md),
[Canonical Glossary](../GLOSSARY.md), and [M34 Decision Register](m34/audit/registers/decision_register.md)
`M34-D-0004`, `M34-D-0005`, `M34-D-0010`.

**Verdict:** **APPROVED.**

**Scope discipline:** This confirmation is the only file created. It modifies no
proposal, no prior review, no frozen milestone, no Decision Log, and no code,
and it triggers no Graphify refresh and no closeout.

---

## 1. Summary

All four Required Corrections are **RESOLVED**. Each claimed change was verified
against the **updated proposal itself**, not only against the response document.
The corrections were applied where they belong — at the ownership/vocabulary/
temporal seam and at the WP2 admission gate — and none introduced a domain,
expanded scope, changed the title, or created implementation, runtime,
persistence, provider, or production authority.

| Required correction | Prior concern | Disposition |
| --- | --- | --- |
| RC-1 — Layer/domain ownership reconciliation | Computed value homed in an Observation-layer domain without §5/§6 proof | **RESOLVED** |
| RC-2 — Market Observation vs. Calculated Market Measure | New term silently narrowed a frozen glossary entry / `M34-D-0010` | **RESOLVED** |
| RC-3 — `M34-D-0005` temporal/state integration | Uncited grammar; `UNAVAILABLE` token collision | **RESOLVED** |
| RC-4 — WP2 exit criteria and governing authorities | Blocking gates and authorities omitted | **RESOLVED** |

The corrections that were the two High risks in the prior review — the layer
placement (RC-1) and the frozen-vocabulary collision (RC-2) — are now closed
with mechanically testable boundaries and explicit admission gates, which is the
standard the prior review demanded.

---

## 2. RC-1 Assessment — Layer/Domain Ownership Reconciliation

**Prior requirement:** Prove, rather than assert, why a platform-computed market
value owned by Market Intelligence is constitutional given that Constitution §5
homes "meaning derived from observation" in the Knowledge layer and the §6 table
assigns Knowledge to Portfolio/Wealth Intelligence; and state a mechanically
testable boundary preventing drift into portfolio/life meaning. *(Authority:
Platform Architecture §5, §6, §6.2, §6.5; Law 9.)*

**What the updated proposal now does (verified):**

- **§2.4** adds the explicit reconciliation paragraph: the layer table "does not
  transfer every computed object to Portfolio Intelligence"; §5/§6.5 home
  *portfolio and life* meaning in the Knowledge layer, while §6.2 expressly
  assigns *asset valuation, regime, volatility, breadth, histories, and market
  context* to Market Intelligence; `M34-D-0010` assigns *technical observations
  and market statistics* to Market Intelligence.
- **§2.6** ("Layer and domain reconciliation") supplies the five-part,
  mechanically testable boundary — subject, permitted inputs, output meaning,
  input exclusions (no ledger/holding/tax-lot/membership), and judgment
  exclusion — and makes failure of items 1–4 **inadmissible** (routes the
  concept to Portfolio/Wealth Intelligence) and failure of item 5 a Decision
  Intelligence concern. It states explicitly that "label similarity is never
  sufficient" and that asset return/volatility/drawdown may be Market Measures
  while portfolio return/volatility/drawdown remain Portfolio Intelligence.
- **§2.6** frames the whole boundary as a Governance **G2** refinement, "not an
  exception to the six-layer model," grounded in §6.2, §5/§6.5, Law 9, and
  `M34-D-0010`.
- **WP2 exit criterion 1** and **Definition of Done item 4** require independent
  approval of this proof before vocabulary admission.

**Assessment:** The missing proof now exists, is grounded in the exact
authorities the prior review cited, and — critically — is *mechanical and
falsifiable* rather than asserted. This is precisely what RC-1 demanded.
**RESOLVED.**

---

## 3. RC-2 Assessment — Market Observation vs. Calculated Market Measure

**Prior requirement:** Prove that "Calculated Market Measure" carves
*platform-computed* statistics out of the *witnessed* "market statistic /
technical observation" already homed in the frozen **Market Observation**
glossary entry, **without reinterpreting** that boundary or `M34-D-0010` —
i.e., refine without weakening (G2). *(Authority: GLOSSARY "Market Observation";
`M34-D-0010`; Governance G2, G4; Vocabulary V1, V3.)*

**What the updated proposal now does (verified):**

- **§2.2** replaces the previously over-broad wording. It now states: a
  *witnessed or provider-reported* market statistic **remains** a Market
  Observation represented through M39 Observation semantics (Event Type
  `Observation`); a *platform-computed* statistic **remains Market
  Intelligence-owned market evidence** but is represented as a Calculated Market
  Measure with Event Type `Calculation`; neither is Investment Judgment.
- **§2.2** explicitly says this "refines artifact and event type; it does not
  narrow or reinterpret the frozen Market Observation ownership boundary," and
  acknowledges the glossary/`M34-D-0010` breadth rather than contradicting it.
- **WP2 validation** requires proving that a platform-computed statistic uses
  Event Type `Calculation` "without weakening the frozen Market Observation
  meaning," and **WP2 exit criterion 2** makes the refinement an admission gate.

**Assessment:** The apparent conflict I raised is removed. The distinction is now
drawn by **provenance and canonical Event Type**, not by silently narrowing a
reserved frozen term, and it is correctly characterized as a G2 refinement
subject to independent approval before any glossary change. This satisfies RC-2.
**RESOLVED.**

---

## 4. RC-3 Assessment — `M34-D-0005` Temporal and State Integration

**Prior requirement:** Cite `M34-D-0005` and conform the result to the Canonical
Temporal Claim grammar (Event Type `Calculation`, Producing Domain = Market
Intelligence, authoritative timestamp, Degraded State); resolve the `UNAVAILABLE`
collision between the proposal's state set and the reserved Degraded State.
*(Authority: `M34-D-0005`; GLOSSARY "Canonical Temporal Claim", "Event Type",
"Producing Domain", "Degraded State"; Vocabulary V1.)*

**What the updated proposal now does (verified):**

- **Header** adds `M34-D-0005` to governing authority.
- **§8.9** ("Canonical temporal and degraded-state grammar") adopts the full
  Canonical Temporal Claim: Event Type `Calculation`; Producing Domain `Market
  Intelligence`; an **explicit, method-defined authoritative timestamp, never a
  system-clock lookup**; and a Glossary-admitted Degraded State owned by Market
  Intelligence.
- **§8.8** renames the state axis to **Computation Outcome** and replaces the
  colliding `UNAVAILABLE` with **`DEPENDENCY_UNRESOLVED`**; **§8.9** reserves
  `UNAVAILABLE` for Degraded State and declares the two axes **orthogonal**,
  requiring WP5/WP6 to define a deterministic outcome/degraded-state interaction
  matrix.
- **§6 domain-model table**, **DoD items 10–11**, and the WP2 validation all
  carry the same grammar and the reservation.

**Assessment:** Both defects are cured. The collision is gone, the grammar is
adopted rather than paralleled, and making the authoritative timestamp an
explicit invocation input (no wall-clock) actively *strengthens* Law 4
determinism. This exceeds the minimum RC-3 asked for. **RESOLVED.**

---

## 5. RC-4 Assessment — WP2 Admission Criteria and Governing Authority

**Prior requirement:** Add `M34-D-0004` and `M34-D-0005` to governing authority;
make RC-1/RC-2/RC-3 explicit admission-blocking WP2 exit criteria; add a
Definition-of-Done item requiring independent approval of the layer and
Observation/Measure reconciliations. *(Authority: Governance G3; Vocabulary V2.)*

**What the updated proposal now does (verified):**

- **Header** governing-authority list now names `M34-D-0004`, `M34-D-0005`, and
  `M34-D-0010`.
- **WP2 deliverables** add the six-layer/layer-to-domain reconciliation, the
  `M34-D-0004/0005/0010` compatibility proof, the witnessed-vs-computed
  refinement, and an asset-measure/portfolio-measure **negative corpus**.
- **WP2 exit criteria** enumerate RC-1, RC-2, and RC-3 as express conditions of
  independent constitutional approval **before** vocabulary admission or
  downstream work.
- **Definition of Done items 2, 4, 10, 11, and 20** carry the authorities, the
  independent-approval gate, and the temporal/state invariants.

**Assessment:** Each decision is now placed at its proper governance level (G3)
and downstream reliance is blocked until it is resolved (V2). This is exactly
the gating RC-4 required, and it adds no work package and no implementation
scope. **RESOLVED.**

---

## 6. Remaining Concerns

None that block confirmation. Two observations, both already carried by the
proposal and **not** conditions of this approval:

- The non-blocking recommendations from the prior review (RI-1 disambiguating
  "Market Measure" from Portfolio "measures"; RI-2 admitting a minimum
  vocabulary set) are now reflected in the WP2 "minimum coherent glossary
  proposal" deliverable and the §2.5 terminology table. No action required here.
- The substance of RC-1/RC-2/RC-3 is correctly deferred to WP2 for *independent
  constitutional approval before vocabulary admission*. That gate is now built
  into WP2 and the Definition of Done. This confirmation approves the
  **resolution of the corrections**; it does not itself admit M40 vocabulary,
  authorize a work package, or approve the milestone. WP2's own independent
  approval remains a future, separate gate — correctly so.

---

## 7. Final Recommendation

**APPROVED.**

RC-1 through RC-4 are each **RESOLVED**. The author accepted every correction,
applied it to the updated proposal at the correct constitutional seam, grounded
each change in the exact repository authority the prior review cited, and — for
the two High-risk seams — replaced assertion with mechanically testable
boundaries and admission-blocking gates. The response document faithfully
represents the changes actually present in the updated proposal, which were
verified directly.

This confirmation closes the corrections issued under the prior verdict
`APPROVED WITH REQUIRED CORRECTIONS`. It does not admit vocabulary, authorize
any work package, amend any frozen artifact, or create canonical,
implementation, runtime, provider, persistence, public-exposure, or
production-method authority. M40 remains a non-canonical proposal in
`NOT_APPROVED` state; its WP2 independent constitutional approval — now correctly
gated on the reconciliations above — is the next authority-bearing step.
