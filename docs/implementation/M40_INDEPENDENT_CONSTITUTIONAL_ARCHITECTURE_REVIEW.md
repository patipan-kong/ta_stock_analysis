# M40 — Independent Constitutional Architecture Review

**Review date:** 2026-07-23

**Reviewer role:** Independent constitutional architecture reviewer (not the
proposal author).

**Subject:** [M40 — Canonical Asset Market Measure Foundation](M40_Canonical_Asset_Market_Measure_Foundation_Plan.md),
status `PROPOSED_FOR_ARCHITECTURAL_REVIEW`.

**Repository status governing this review:** M39 `COMPLETE AND FROZEN`; M40
proposal persisted but `NOT APPROVED`, `NOT CANONICAL`, no implementation,
runtime, or production authority.

**Authority precedence applied:** Where the proposal and the repository
conflict, the repository governs. Governing artifacts consulted directly:
[Platform Architecture](../architecture/platform_architecture.md) (the
Constitution, v1.1); [Canonical Glossary](../GLOSSARY.md);
[M34 Decision Register](m34/audit/registers/decision_register.md), decisions
`M34-D-0004`, `M34-D-0005`, `M34-D-0008`, and `M34-D-0010`; and the frozen
[M39 Epic Closeout](M39_EPIC_CLOSEOUT.md).

**Verdict:** **APPROVED WITH REQUIRED CORRECTIONS.**

**Scope discipline of this review:** This document is the only file added. It
modifies no proposal, no frozen milestone, no Decision Log, and no code, and it
triggers no Graphify refresh or closeout.

---

## 1. Executive Assessment

The M40 proposal is constitutionally literate and unusually defensive. It
correctly refuses to create a new Analysis domain, correctly homes nothing in a
fabricated authority, exhaustively withholds runtime/persistence/provider/API
authority, gates every implementation-bearing work package behind explicit
admission, and repeatedly re-states the facts-versus-judgment law that the
platform is built on. On the two failure modes most likely to sink a milestone
of this kind — **judgment leaking into a calculation** and **an engine
acquiring provider/asset-class knowledge** — the proposal is sound and, in
several places, exemplary.

It is **not** approvable as-is, because its central constitutional claim —
that a platform-**computed** market value is owned by **Market Intelligence**
and named a **Calculated Market Measure** — sits on a seam the proposal
asserts rather than proves. Three frozen authorities bear directly on that
seam and are either under-reconciled or uncited:

1. the six-layer model (Constitution §5), under which a value *derived from
   observation* reads as a **Knowledge-layer** object owned by Portfolio /
   Wealth Intelligence, not an Observation-layer object;
2. the frozen **Market Observation** glossary entry and `M34-D-0010`, which
   already classify "market statistics" and "technical observations" as
   Market-Intelligence-owned **Observations** — a homing the proposal both
   relies on and silently contradicts by insisting a computed statistic is
   *not* an observation; and
3. `M34-D-0005`, the canonical temporal-and-degraded-state grammar (Event Type
   `Calculation`, Producing Domain owns state), which is directly on point and
   is **never cited** by the proposal.

None of these is fatal. Each is closable, and the repository actually supplies
the material to close them in Market Intelligence's favor. But because all
three touch **frozen** authority, they must be resolved **before or within
M40-WP2** — the first admission-bearing constitutional gate — not deferred.
Hence: approved, with the corrections in Section 8 required before WP2 admits
any vocabulary.

The title and the successor scoping are an improvement over the informal
"Universal Asset Analysis Foundation," which would have implied exactly the
composite Analysis authority `M34-D-0010` forbids.

---

## 2. Constitutional Findings

**CF-1 — Facts/judgment separation is respected (PASS).** The proposal
prohibits outlook, direction, signal, attractiveness, and action semantics in
the core (§5, §7.4, §12) and correctly classifies "bullish/bearish/trend-as-
direction" as Investment Judgment while allowing "trend as a numeric statistic"
as a measure (§2.5). This conforms to Constitution §2.1 and the **Investment
Judgment** glossary entry ("interpretation of observations into an analytical
conclusion, outlook, or expected direction … owned by Decision Intelligence").
The distinction is fine-grained but correctly drawn and mechanically
enforceable; the Risk table already commits to forbidden-token tests.

**CF-2 — No new domain; nine-domain partition preserved (PASS).** The proposal
explicitly forbids becoming "a generic Analysis domain" or "a composite
Instrument Analysis authority" (§1) and homes every concept in existing
Market Intelligence vocabulary. This conforms to Constitution §6 and to
`M34-D-0010` ("No Instrument Analysis domain or composite authority is
created").

**CF-3 — Determinism and provenance obligations are met in substance (PASS
with required grounding).** Sections 8–9 satisfy Law 4 (deterministic,
reproducible, no wall-clock/provider dependence) and Law 14 (traceability). The
content is correct; its **authority citation is incomplete** — see CF-6 and
RC-3.

**CF-4 — Human-sovereignty / gate model untouched (PASS).** M40 authorizes no
ledger write, no decision, and no configuration change; it produces sibling
descriptive objects only. The three gates (Constitution §7.2) are not
approached. Law 12 is not implicated.

**CF-5 — Layer placement is unresolved (REQUIRED CORRECTION — RC-1).**
Constitution §5 places "meaning derived from truth and observation" in the
**Knowledge** layer, and the §6 layer→domain table assigns Knowledge to
**Portfolio Intelligence · Wealth Intelligence** — Market Intelligence is the
**Observation**-layer owner only. A Calculated Market Measure is, by the
proposal's own words, *not* a witnessed observation (§2.2) but a value derived
from observations — which reads as a Knowledge-layer object. The proposal never
reconciles this. The reconciliation exists in the repository (Constitution §6.2
gives Market Intelligence "market-state understanding: regime, volatility,
breadth" — derived statistics — and `M34-D-0010` homes "market statistics" in
Market Intelligence), but it must be made **explicitly**, because assigning a
Knowledge-shaped concept to an Observation-layer domain without proof is
exactly the kind of boundary drift Constitution §2.4 and Law 9 exist to
prevent.

**CF-6 — Temporal/state model is uncited against `M34-D-0005` (REQUIRED
CORRECTION — RC-3).** `M34-D-0005` and the **Canonical Temporal Claim** /
**Event Type** / **Producing Domain** / **Degraded State** glossary entries
establish the *only* canonical grammar for an authoritative dated result, and
`Calculation` is an approved Event Type whose Producing Domain owns its meaning
and degraded state. This is the precise constitutional hook that legitimizes a
Market-Intelligence calculation — and the proposal cites none of it. Worse, the
proposal's `Computation State` set reuses the token `UNAVAILABLE`, which
`M34-D-0005` already reserves as a producing-domain **Degraded State**,
creating a latent terminology collision (V1).

---

## 3. Architectural Findings

**AF-1 — Asset-agnostic core is correctly specified (PASS).** The core-input
prohibition (§7.1) — no asset type, ticker, exchange, provider identity,
workspace, or presentation label — is a direct, testable expression of Law 10
("the core never knows the edge") and Goal "multi-asset by design"
(Constitution §3). Applicability-by-requirement rather than by supported-type
list (§7.2) is the correct realization of "adding an asset class is description,
not surgery" (§9).

**AF-2 — Pure-kernel boundary is sound (PASS).** The forbidden-import list
(§11.2) and the empty-production-registry default (§4.5, §11.3) contain runtime
and authority leakage structurally, satisfying Laws 4, 7, and 10 and the
proposal's own zero-authority posture.

**AF-3 — M39 corpus treated as frozen (PASS).** The Observation Input Manifest
references immutable M39 Observation Identities and creates Market Measure
Results as **sibling** objects, mutating and reclassifying nothing (§2.1, §4.3,
§9). This respects the M39 Epic Closeout freeze and M39-WP6 identity semantics.

**AF-4 — Legacy analytics correctly quarantined (PASS).** `technical.py`,
`quant_engine.py`, `AnalysisCache`, `RegimeSnapshot`, and `SignalHistory` are
classified as non-canonical implementation evidence with no migration authority
(§2.3, §11.4). This respects `M34-D-0008` (`STOPPED_AUTHORITY` legacy records
prove no canonical authority) and Law 9 (no second implementation is minted;
the owner is extended or nothing is).

**AF-5 — `portfolio_metrics.py` used as template, not forked (PASS).** The
proposal cites it as a purity exemplar while explicitly refusing to generalize
its Ledger/Portfolio-owned semantics into Market Intelligence (§2.3),
respecting Law 9 and the §6.5 Portfolio Intelligence boundary.

**AF-6 — Implementation architecture in a proposal is permissible (PASS).**
The module layout (§11) is Level-4 (Technical Design) content; describing future
structure creates no authority under Governance G2/G3. No finding.

---

## 4. Ownership Findings

Each boundary was tested for leakage in both directions.

| Boundary pair | Proposal treatment | Governing authority | Verdict |
|---|---|---|---|
| Asset Foundation ↔ Market Intelligence | Asset identity/definition referenced only; providers are witnesses that never define an asset (§1.1, §7.3) | Constitution §6.1, Law 5, §7.4 (witness/authority) | **PASS** |
| Market Intelligence ↔ Portfolio Intelligence | Portfolio-level analytics excluded; "Return" flagged as a collision risk (§2.5, §5) | Constitution §6.5; **Analytical Grouping** glossary entry | **PASS, boundary must stay mechanical** — see RC-1; the asset-level "Return" measure vs. Portfolio "performance" seam is the most probable future leak |
| Market Intelligence ↔ Decision Intelligence | No signal/outlook/consensus; Investment Judgment, Instrument-Level Risk, Consensus, Analysis History left with Decision Intelligence (§5) | `M34-D-0010`; **Investment Judgment / Instrument-Level Risk / Analysis History** glossary entries | **PASS** |
| Market Intelligence ↔ Trust & Evaluation | Reports Computation State / Input Sufficiency, not quality/trust (§2.5, §5) | Law 8; **Evaluation** glossary entry | **PASS (monitored)** — a domain reporting its own computation outcome is not self-evaluation, but the "sufficiency, not trust" line must remain a tested invariant |
| Market Intelligence ↔ Asset Foundation vocabulary | Method Requirements stay Market-Intelligence-owned, never projected into Asset Definitions (§7.3) | `M34-D-0004`; Constitution §6.1 | **PASS** |
| Ownership of the *computed value itself* | Assigned to Market Intelligence as a **Calculated Market Measure** | Constitution §5 layer model; §6.2; `M34-D-0010`; **Market Observation** glossary entry | **CONTESTED — RC-1, RC-2** |

The first five rows are clean. The sixth is the review's load-bearing finding
and is developed in Section 5.

---

## 5. Terminology Findings

**TF-1 — "Calculated Market Measure" collides with the frozen "Market
Observation" definition (REQUIRED CORRECTION — RC-2).** The **Market
Observation** glossary entry defines an observation as "an observable market
fact, including a price, **technical observation, market statistic**, provider
observation, or news reference," owned by Market Intelligence and governed by
`M34-D-0010`. `M34-D-0010` itself homes "technical observations, market
statistics" in Market Intelligence **as Observations**. The proposal, however,
insists that a platform-computed statistic is explicitly **not** an Observation
Event (§2.2). Both cannot stand unreconciled: the frozen glossary says a market
statistic *is* an observation; the proposal says a computed market measure is
*not*. The honest distinction — a *witnessed/provider-reported* statistic is an
Observation, a *platform-computed* statistic is a Calculation — is a legitimate
**refinement** (Governance G2, "lower may refine, never weaken") and does not
weaken any law. But because it touches the meaning of a **reserved,
frozen** vocabulary entry and an immutable ARB decision, WP2 must prove the
carve-out explicitly under V1/V3 and G4, or the new term reinterprets a frozen
boundary — which G2 forbids.

**TF-2 — Title is correct and an improvement (PASS).** "Canonical Asset Market
Measure Foundation" is more precise than "Universal Asset Analysis Foundation,"
which would imply a supported-asset universe and a single Analysis authority
that `M34-D-0010` prohibits. "Foundation" is consistent with M35–M38 naming.
"Canonical Asset" reuses no reserved term improperly. Approved.

**TF-3 — "Measure" carries loose prior usage (RECOMMENDED — RI-1).** The
glossary prose already uses "measure" informally in Portfolio contexts
("cross-portfolio exposure measure"; "Measures whether a trade was actually
required"). No hard definitional collision exists, but WP2 should disambiguate
"Market Measure" from Portfolio "measures" to protect V1 hygiene.

**TF-4 — "Derivation" correctly avoided (PASS).** The proposal declines to name
its output an "Analytical Derivation" because the **Derivation** glossary entry
reserves the term for "any state computed from the **ledger**" (§2.5). This is
correct and respects the V3 reservation of *derivation* as load-bearing
vocabulary.

**TF-5 — Vocabulary surface area is large (RECOMMENDED — RI-2).** Section 6
introduces ~14 new nouns. V2 requires each to be registered before it is relied
upon. The proposal correctly defers registration to WP2 approval, but the sheer
count is a governance load and a future-collision surface; WP2 should admit the
minimum coherent set and reserve the rest.

---

## 6. Dependency Findings

**DF-1 — Work-package graph is acyclic and correctly gated (PASS).** WP1 →
WP2 → {WP3, WP4} → WP5 → WP6 → WP7 → WP8 → WP9 → WP10 with stated dependencies.
WP2 requires independent constitutional approval before any downstream
specification; WP7–WP8 are gated behind explicit implementation authorization.
This conforms to Governance G2/G3 and the M39 precedent of admission gates.

**DF-2 — Downward-only dependency respected (PASS).** The proposed dependency
direction (Asset Foundation projection + M39 Observation semantics → manifest →
pure core → result → future adapters, §11.2) points downward only and never
depends on Experience, Decision, Portfolio, or Trust. Conforms to Constitution
§7.1.

**DF-3 — RC-1/RC-2 must be resolved inside WP2, not deferred to later WPs
(FINDING).** Because RC-1 and RC-2 concern *ownership and vocabulary*, they are
WP2 questions by the proposal's own decomposition. The dependency graph is
correct precisely because it forces these questions to the front; the
correction is to make their resolution an explicit WP2 exit criterion (see
RC-4).

---

## 7. Risks

| Risk | Severity | Control status |
|---|---|---|
| A computed value drifts into being treated as an Observation, or vice versa, reinterpreting the frozen Market Observation boundary | **High** | Under-controlled; RC-2 required |
| A Knowledge-layer concept is owned by an Observation-layer domain without constitutional proof, eroding the §5/§6 layer model | **High** | Under-controlled; RC-1 required |
| Asset-level "Return"/"volatility"/"drawdown" measures leak into Portfolio Intelligence's performance/risk vocabulary | Medium | Named by proposal (§2.5); needs mechanical test at WP2/WP5 |
| Temporal/state semantics diverge from `M34-D-0005`; `UNAVAILABLE` token collision | Medium | Uncontrolled until RC-3 |
| "Computation State / Input Sufficiency" brushes Trust & Evaluation's quality boundary | Low | Correct line drawn; keep as tested invariant |
| Large new-vocabulary surface invites future one-word/two-meaning defects | Low | Deferred to WP2 admission; RI-2 |
| Legacy analytics silently promoted to canonical | Low | Well-controlled (§2.3, §11.4; `M34-D-0008`) |
| Hidden equity/provider assumptions in the core | Low | Well-controlled (§7.1, §7.4, forbidden-import tests) |

The two High risks are the same seam viewed from two frozen authorities; both
are closable and both are WP2-blocking.

---

## 8. Required Corrections

Each correction is mandatory before **M40-WP2** admits any vocabulary, and each
cites the governing repository authority that makes it mandatory.

**RC-1 — Reconcile Calculated Market Measure with the six-layer model and the
layer→domain table.** WP2 must state, and prove, why a platform-computed market
value owned by Market Intelligence is constitutional given that Constitution §5
homes "meaning derived from … observation" in the **Knowledge** layer and the
§6 table assigns Knowledge to Portfolio / Wealth Intelligence. The proof exists
in the repository and must be cited: Constitution §6.2 (Market Intelligence owns
"regime, volatility, breadth") and `M34-D-0010` (Market Intelligence owns
"market statistics, technical observations"). The correction must also state the
**mechanically testable** boundary that prevents a Market Measure from drifting
into portfolio/life meaning owned by Portfolio / Wealth Intelligence.
*Authority: Platform Architecture §5, §6 (layer table), §6.2, §6.5; Law 9.*

**RC-2 — Reconcile the new term against the frozen Market Observation entry and
`M34-D-0010`.** WP2 must prove that "Calculated Market Measure" carves
**platform-computed** statistics out of the **witnessed** "market statistic /
technical observation" already homed in the Market Observation glossary entry,
**without reinterpreting** that frozen boundary or `M34-D-0010`. If the carve-
out cannot be shown to *refine without weakening*, the term collides with
reserved frozen vocabulary and must be renamed or rescoped.
*Authority: GLOSSARY "Market Observation"; `M34-D-0010`; Governance G2, G4;
Vocabulary V1, V3.*

**RC-3 — Ground the temporal and state model in `M34-D-0005`.** The proposal
must cite `M34-D-0005` and conform its result to the **Canonical Temporal
Claim** grammar: Event Type `Calculation`, Producing Domain = Market
Intelligence, authoritative timestamp, and Degraded State. It must resolve the
`UNAVAILABLE` token collision between its `Computation State` set and the
`M34-D-0005` Degraded-State set (rename one, or state that they are orthogonal
axes and define their interaction).
*Authority: `M34-D-0005`; GLOSSARY "Canonical Temporal Claim", "Event Type",
"Producing Domain", "Degraded State"; Vocabulary V1.*

**RC-4 — Make RC-1/RC-2/RC-3 explicit WP2 exit criteria and add `M34-D-0005` to
the governing-authority list.** The proposal's governing-authority header omits
`M34-D-0005` and `M34-D-0004` despite both being directly on point. Add them,
and add a Definition-of-Done item requiring independent approval of the RC-1/
RC-2 layer-and-observation reconciliation.
*Authority: Governance G3 (decisions recorded at their proper level); Vocabulary
V2.*

---

## 9. Recommended Improvements

Non-blocking; they strengthen the proposal without gating it.

- **RI-1 — Disambiguate "Market Measure" from Portfolio "measures"** in the WP2
  glossary proposal (V1 hygiene). *(See TF-3.)*
- **RI-2 — Admit the minimum coherent vocabulary set in WP2** and reserve the
  remainder, reducing the ~14-noun surface area exposed at once. *(See TF-5.)*
- **RI-3 — Keep "sufficiency, not trust" a tested invariant** in the WP8/WP10
  conformance corpus, not only a prose assertion, to hold the Trust & Evaluation
  boundary mechanically. *(See Law 8.)*
- **RI-4 — Add an explicit "asset-measure vs. portfolio-measure" negative test**
  to WP5, exercising "Return," "volatility," and "drawdown" against the
  Portfolio Intelligence boundary named in RC-1.
- **RI-5 — Cross-reference `M34-D-0008`** in §2.3 where legacy analytics are
  quarantined, to anchor the `STOPPED_AUTHORITY` treatment to its ruling.

---

## 10. Final Recommendation

**APPROVED WITH REQUIRED CORRECTIONS.**

The M40 proposal is a constitutionally sound milestone boundary. Its ownership
model, asset-agnostic core, determinism discipline, legacy quarantine, and
zero-authority posture conform to the Constitution's laws and to the standing
M34 ARB decisions. It creates no new domain, no hidden authority, and no
runtime, persistence, provider, or execution leakage, and it treats the frozen
M39 corpus correctly.

Approval is conditioned on resolving **RC-1 through RC-4** before M40-WP2 admits
any vocabulary, because each touches **frozen** authority — the six-layer model
(Constitution §5–§6), the frozen **Market Observation** entry with `M34-D-0010`,
and the canonical temporal grammar of `M34-D-0005`. These are reconciliations,
not redesigns: the repository already supplies the material to close all three
in Market Intelligence's favor, and the proposal's own WP2 is the correct place
to do it. The recommended improvements (RI-1 through RI-5) further harden the
milestone but do not gate it.

This review admits nothing, authorizes no implementation, and amends no frozen
milestone. M40 remains `PROPOSED_FOR_ARCHITECTURAL_REVIEW`; this document
records the independent constitutional assessment of that proposal only.
