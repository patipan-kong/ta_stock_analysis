# Asset Scope Governance Review

_Milestone M28. Governance review only — no vocabulary extension, no new Asset Definition, no runtime/registry/enforcement/capability-projection change. Produced against the library as it stood after [M27](../engineering/DECISION_LOG.md) (`library.DEFINITION_LADDERS = {CASH, EQUITY, ETF, FUND, BOND, PROPERTY}`, no `AssetType` remaining `VOCABULARY_GAP`)._

| | |
|---|---|
| **Status** | Governance review (M28) — non-binding on vocabulary/library mechanics, binding on platform scope |
| **Scope** | CRYPTO, COMMODITY, OTHER (the three remaining non-`DEFINED` `AssetType` members) |
| **Precedes** | [asset_model_gap_analysis.md](asset_model_gap_analysis.md) (M20) — that document asked *can the declaration model express this?*; this document asks the prior, platform-strategy question — *should the platform represent this at all?* |
| **Reads as input** | [asset_model_gap_analysis.md](asset_model_gap_analysis.md), [readiness_report.py](../../backend/services/asset_definitions/readiness_report.py), [enforcement_decisions.py](../../backend/services/asset_definitions/enforcement_decisions.py), [asset_domain.py](../../backend/services/asset_domain.py), [asset_definitions.md](../architecture/asset_definitions.md) §9 |

---

## 1. Purpose

The first-generation Asset Definition Program is complete: six canonical definitions (CASH, EQUITY — M8; ETF — M18; FUND — M22; BOND — M24; PROPERTY — M27) span cash instruments, exchange-traded securities, pooled investment vehicles, fixed-income instruments, and negotiated physical assets. No `AssetType` remains classified `VOCABULARY_GAP`. Two bindings remain `SCOPE_UNDECIDED` — CRYPTO and COMMODITY — and one, OTHER, is permanently `EXEMPT`.

Every prior milestone in this program answered *how* to describe a kind. This milestone deliberately asks a different, prior question, per the brief's own framing: not "can the declaration model represent CRYPTO/COMMODITY?" (§3.4–3.5 of `asset_model_gap_analysis.md` already showed the answer is "yes, cheaply, once one open item resolves") but "should this platform carry the permanent governance weight of doing so?" Scope precedes modeling. Getting this order backwards — authoring a definition because the vocabulary happens to make it easy — is exactly how the duplicated-definition risk (`asset_definitions.md` §10.4) and the capability-explosion risk (§10.1) eventually get paid for, by a library that grew because it *could*, not because it *should*.

---

## 2. Review: CRYPTO

**Investment use cases.** Direct retail holding of a cryptocurrency (BTC, ETH, and similar fungible digital-bearer assets), tracked as a portfolio position with its own cost basis, valuation, and return contribution — the same shape any other holding takes in this platform's ledger.

**Portfolio behavior.** Continuously divisible, venue-traded (via an exchange), and priced by continuous quotation — three axes already well inside the existing vocabulary (`Divisibility.CONTINUOUS`, `AcquisitionSemantics.VENUE_TRADED`, `ValuationQuestion.CONTINUOUS_QUOTATION`). The one open axis is settlement: crypto markets trade 24/7 with block-confirmed, probabilistic finality, which does not obviously map onto `SettlementPattern`'s current `INSTANT`/`CYCLE_BASED` dichotomy. This is the same open item `asset_model_gap_analysis.md` §3.4 recorded and did not resolve — a domain-review judgment, not a vocabulary search.

**Overlap with existing definitions.** None. Every other canonical definition assumes a market with a settlement cycle or an instant, single-jurisdiction transfer (Cash). Crypto would be the first kind to individuate purely on continuous, always-open trading — a genuine behavioral difference, not a rebrand of Equity or ETF.

**Required future vocabulary.** At most one word: either a new `SettlementPattern` member for probabilistic/continuous finality, or a confirmation that `INSTANT` already honestly covers it (undecided until the domain review happens). The `STAKING` flow character named in the constitution's own §9 prose was never actually reserved in `vocabulary.py` (`asset_model_gap_analysis.md` §3.4/§1 finding 3) and, per the constitution's own "argued when a real position demands them" discipline, should stay unadded until an actual staking position needs it — not speculatively bundled into whichever milestone resolves settlement.

**Likely engine impact.** Structurally none by design (D5) once the settlement question is answered honestly — but the answer has a real downstream shadow worth naming plainly: engines that implicitly assume a market close (the daily snapshot scheduler's 17:45 ICT timing decision, recorded elsewhere in this log, exists *because* SET has a close) would need their own instance-level review for a 24/7 asset. That review is not a vocabulary concern and is not performed here; it is flagged so a future authoring milestone does not discover it mid-stream.

**Governance cost.** Low-to-moderate: one open axis to resolve by domain judgment, one new definition, one deliberately-deferred flow word, and — the only entry on this list — a genuine "is this actually new behavior for the whole platform, not just the definitions subdomain" question (24/7 markets), which no other canonical definition has had to answer yet.

**Conclusion: DEFER.**
Crypto is not redundant — unlike Commodity below, it fits no existing definition and would be a legitimate sixth-and-a-half kind of behavior for the platform to describe. But nothing in this review found evidence of present product demand: no crypto holdings feature, no crypto price-feed integration, no user-facing crypto workflow exists anywhere in this codebase today (confirmed by search — every current `CRYPTO` reference is scaffolding inside the asset-definitions subsystem itself: the reserved enum member, its `SCOPE_UNDECIDED` row, and the gap analysis). Authoring a canonical definition for a kind with no present consumer would be modeling ahead of need — the same anti-pattern the constitution itself refuses for individual grants (no speculative grants, §3.3 of `asset_definition_library.md`) applied one level up, to the decision of whether to model a kind at all. Revisit when either holds: (a) an explicit product decision to support user-held crypto positions, or (b) a concrete instance that needs registering. At that point, the domain review of Axis 3 is the correct first step — not vocabulary work, not authoring.

---

## 3. Review: COMMODITY

**The question, per the brief:** do physical commodities, commodity ETFs, and futures exposure already satisfy common user needs through existing definitions? Reviewed as the two structurally distinct shapes `asset_model_gap_analysis.md` §3.5 already separated:

**Derivative/exchange-traded commodity exposure** (a gold ETF, a futures-tracking ETC) is, axis-for-axis, already an ETF: venue-traded, discrete units, cycle settlement, continuously quoted, minimal-or-no income flow. Nothing about "the underlying happens to be gold instead of a basket of equities" is a fact any engine in this platform behaves differently on — it is a classification fact (`ClassificationDimension.ASSET_CLASS`, already a structural dimension in `asset_domain.py`), the same way a sector is. **This shape needs zero new definitions today** — it is already fully served by `AssetType.ETF`.

**Physical commodity exposure** (allocated gold, warehoused grain) is, axis-for-axis, the same shape PROPERTY now declares: negotiated acquisition, negotiated/manual settlement, appraisal-or-spot valuation, no income flow, no event families, open-ended existence. Whether it is *byte-identical* to `PROPERTY_V1` depends on one unresolved detail — unit divisibility (a real-estate parcel is indivisible; some allocated-bullion instruments are continuously divisible by weight, more like Cash's unit semantics than Property's) — which is an instance-level question about a specific future product, not a platform-scope question this review can or should resolve in the abstract.

This matters more than a restatement of §3.5's finding: it changes the governance conclusion. Per `asset_definitions.md` §2.2 — *"Two names with identical declarations are one definition, distinguished downstream by classification"* — if a physical commodity instrument's declarations end up matching `PROPERTY_V1` exactly, the correct outcome under D1 is **not** a new `AssetType`; it is minting under `AssetType.PROPERTY` with `ClassificationDimension.ASSET_CLASS = "Commodity"` distinguishing it from real estate downstream, exactly as the constitution requires. A distinct `COMMODITY` binding would, in that case, be a second definition with identical declarations to Property's — the precise duplicated-definition failure mode §10.4 exists to prevent, arrived at not through carelessness but through skipping this review's own question.

**Required future vocabulary.** None, under either shape, confirming `asset_model_gap_analysis.md` §3.5's own finding.

**Likely engine impact.** None — both shapes route through already-shipped definitions.

**Governance cost of introducing a distinct binding today.** Net negative: it would add a permanent `AssetType` member's worth of governance surface (a row in every table this program maintains, forever) to describe behavior two existing definitions already describe, buying nothing a classification value doesn't already buy more cheaply.

**Conclusion: REJECT.**
`COMMODITY` should not become a distinct canonical Asset Definition. Both use cases the world calls "commodity investing" are already servable today: derivative/ETF-shaped exposure through `AssetType.ETF`, and physical exposure — once a concrete instrument is on the table — through `AssetType.PROPERTY` plus an `ASSET_CLASS` classification value. This is a REJECT of the *binding*, not of the *investment*; no user is blocked, and nothing about this recommendation prevents a future, genuinely distinct physical-commodity instrument (one that provably fails to individuate the way described above — e.g., a continuously-divisible allocated-bullion product) from being proposed as its own definition when it actually exists, walking the ordinary evolution ladder (`asset_definitions.md` §8.1) like any other candidate. That is a future, need-driven proposal, not a standing roadmap item this review creates.

---

## 4. Review: OTHER

`OTHER` is the platform's explicit, permanent escape hatch for unclassified kinds (M9 TDD §10.2: "OTHER unregisterable"). Its `enforcement_decisions.py` row (`INTENTIONAL_LEGACY_BEHAVIOR` / `PRESERVE`) and `readiness_report.py` row (`EXEMPT`) both already state, and this review reconfirms, that no definition is ever anticipated for it: by construction it cannot honestly declare any axis (D7 requires an honest absence or presence, and "unclassified" is neither), so authoring one would violate D5 ("declared, never inferred") the moment a real instance was minted under it.

Six canonical definitions now exist where at M27's start there were five, and this review just closed CRYPTO and COMMODITY to explicit DEFER/REJECT decisions. Neither event narrows what `OTHER` is for: `OTHER` does not shrink as the library grows, because its purpose is not "whatever isn't defined yet" (a purpose the library's growth would erode) but "whatever the platform has not yet — or may never — chosen to model as a first-class kind" (a purpose that is structural, not temporal). A genuinely novel future kind — one nobody has proposed yet — would still mint under `OTHER` on arrival, the same as it would have at M7.

**Conclusion: reconfirmed, unchanged.** `OTHER` remains an intentional, permanent, structural exemption. No action.

---

## 5. Recommendation Matrix

| AssetType | Decision | Governance cost if pursued | Trigger to revisit |
|---|---|---|---|
| CRYPTO | **DEFER** | Low-moderate: one domain-review judgment (settlement axis fit), one new definition, one deliberately-unadded flow word | An explicit product decision to support user-held crypto positions, or a concrete instance requiring registration |
| COMMODITY | **REJECT** | N/A — recommendation is to not introduce the binding | A concrete physical-commodity instrument that provably fails to individuate against `PROPERTY_V1` (e.g., genuinely continuous unit semantics) |
| OTHER | **Reconfirmed permanent (EXEMPT)** | N/A — status quo | None; structural, not schedule-driven |

No code, vocabulary, registry, enforcement, or capability-projection change accompanies any row in this matrix. Per this milestone's own success criteria, a SUPPORT/DEFER/REJECT decision is a recorded governance position, not an implementation trigger — CRYPTO's DEFER in particular authorizes no vocabulary or authoring work; it only names the two conditions under which that work would become the *next* milestone's mandate.

---

## 6. Updated Roadmap

The Asset Definitions subdomain's forward path, restated now that the founding program is closed:

- **No scheduled vocabulary or authoring milestones remain.** `asset_model_gap_analysis.md` §8's five-step expansion order (FUND → BOND → PROPERTY → COMMODITY → CRYPTO) is now fully retired: steps 1–3 shipped (M21/M22, M23/M24, M25–M27); steps 4–5 are resolved by this review as REJECT and DEFER respectively, not "ship later" items.
- **The library is stable at six definitions** (CASH, EQUITY, ETF, FUND, BOND, PROPERTY) with no pending additions.
- **Future work is need-driven, not calendar-driven,** per §2 and §3's conclusions above: the next Asset Definitions milestone — if one ever happens — begins from a platform-strategy trigger (a product decision, a concrete instrument that fails to individuate against an existing definition), never from "the vocabulary would allow it."
- **Constitutional stability holds.** No amendment to `asset_definitions.md` §5.1's seven axes has ever been required across the entire program, including PROPERTY's four-axis individuation — the largest single test the axis model has faced. There is no basis in this review for anticipating one.

This section deliberately does not restate or modify `docs/architecture/ROADMAP.md`'s platform-level phase structure; it is the Asset Definitions subdomain's own forward statement, the same scope `asset_model_gap_analysis.md` §8 already kept its own roadmap section to.

---

## 7. Architecture Summary

**Vocabulary growth.** Four governed extension events across the program's life, eight words total: M17 (`ValuationQuestion.PERIODIC_NAV`), M21 (`AcquisitionSemantics.NAV_WINDOW`), M23 (`FlowType.COUPON`, `ExistencePattern.SCHEDULED_TERMINAL`), M26 (`AcquisitionSemantics.NEGOTIATED_TRANSFER`, `SettlementPattern.NEGOTIATED_CLOSING`, `ValuationQuestion.APPRAISAL_ON_EVENT`, `FlowType.RENT`). Every extension passed the anti-explosion rules (`asset_definitions.md` §7.2) and named exactly one owning engine, per Step 2 of the evolution ladder.

**Definition growth.** Two founding definitions (M8) plus four admitted definitions (M18, M22, M24, M27), each individuating against every predecessor under D1 — trending, as the constitution's §9 predicted, toward smaller vocabulary asks per class (ETF: 1 word; FUND: 1 word; BOND: 2 words; PROPERTY: 4 words, the largest single admission, still zero engine diffs).

**Runtime stability.** Zero engine diffs across all six admissions — the constitutional acceptance test (§8.1: "the diff for a new asset class contains one new definition and zero engine changes") held every single time, verified freshly at each milestone via a real `DefinitionRegistry.build()` boot rather than a synthetic fixture alone.

**Governance process.** Every extension and every admission was recorded in `DECISION_LOG.md`; every readiness/enforcement table row was hand-authored and cross-checked against the real library by dedicated tests (`test_definition_readiness.py`, `test_asset_definitions_enforcement.py`), never derived automatically — the discipline the M13/M15 briefs established at the program's start and which held through M27.

**Remaining open questions.** Exactly the three this review closes: CRYPTO (DEFER), COMMODITY (REJECT), OTHER (reconfirmed permanent). None are open in the sense of "blocking" anything — the program has no critical path running through any of them.

**Architectural debt genuinely remaining** (found during this review, not manufactured):

1. `asset_definition_library.md`'s header table (§ "Definitions") still reads "5 — Cash · Equity · ETF · Fund · Bond" and does not list Property — stale since M27. Purely a documentation inconsistency (the code, tests, and `readiness_report.py` are all correct); zero runtime or governance risk. Worth a one-line fix the next time that document is touched for any reason; not fixed here, consistent with this review's own non-goal against modifying declaration-adjacent artifacts and the established project discipline of not repairing a stale artifact outside the milestone that actually revisits it.
2. `asset_model_gap_analysis.md` §3.2's open question — whether Bond should also carry a redemption/call `EventFamily` grant — was left explicitly unresolved at BOND's authoring (M24) and has not been revisited since. Low risk (`BOND_V1` is complete and correct today with an empty grant on that axis), but genuinely open if Bond's event-family coverage is ever reconsidered.

No other debt was found. This review deliberately does not invent a third item to round out the list.

---

## Related Documents

- [asset_model_gap_analysis.md](asset_model_gap_analysis.md) — the M20 vocabulary/individuation analysis this review's CRYPTO/COMMODITY sections build directly on
- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution; §2.2 (names vs. behavior), §9 (Crypto's own worked walk), §10.1/§10.4 (capability explosion, duplicated definitions) all bear directly on this review's conclusions
- [asset_definition_library.md](asset_definition_library.md) — the library itself; §2 the "why six definitions validate the architecture" account this review's Architecture Summary extends
- [asset_domain.py](../../backend/services/asset_domain.py) — `AssetType`, `ClassificationDimension` — the structural enums this review's COMMODITY conclusion depends on (classification, not a new binding, is the correct home for "commodity" as a concept)
- [enforcement_decisions.py](../../backend/services/asset_definitions/enforcement_decisions.py) / [readiness_report.py](../../backend/services/asset_definitions/readiness_report.py) — the hand-authored tables whose CRYPTO/COMMODITY rows this review's decisions inform but, per this milestone's non-goals, deliberately does not edit
- [DECISION_LOG.md](../engineering/DECISION_LOG.md) — where this milestone's governance decisions are recorded
