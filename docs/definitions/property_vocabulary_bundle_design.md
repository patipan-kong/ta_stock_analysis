# Property Vocabulary Bundle Design

_Milestone M25. Design only — no vocabulary extension, no new Asset Definition, no runtime/library/readiness/enforcement change. Produced against the vocabulary and library as they stood after [M24](../engineering/DECISION_LOG.md) (`library.DEFINITION_LADDERS = {CASH, EQUITY, ETF, FUND, BOND}`; `AcquisitionSemantics` has `NOT_TRANSACTABLE`, `VENUE_TRADED`, `NAV_WINDOW`; `SettlementPattern` has `INSTANT`, `CYCLE_BASED`; `ValuationQuestion` has `IDENTITY`, `CONTINUOUS_QUOTATION`, `PERIODIC_NAV`; `FlowType` has `INTEREST`, `DIVIDEND`, `COUPON`)._

| | |
|---|---|
| **Status** | Design document (M25) — non-binding, non-executable |
| **Scope** | PROPERTY — the sole remaining `VOCABULARY_GAP` binding |
| **Input** | [asset_model_gap_analysis.md](asset_model_gap_analysis.md) §3.3, §5, §6, §7, §8 (M20) — this document re-validates and deepens that analysis rather than repeating it |
| **Companion** | [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the process a future authoring milestone will walk once this bundle ships |

---

## 1. Purpose

M20's gap analysis found PROPERTY the most vocabulary-hungry of the five remaining bindings — four axes, not the one-or-two-word pattern ETF, FUND, and BOND each proved sufficient. That size is exactly why it is the wrong candidate for the "ship the word, author the definition" two-milestone rhythm M17→M18, M21→M22, M23→M24 already established: four coordinated words invite exactly the failure mode this milestone's brief names — optimizing each axis independently and arriving at four vocabulary members that individually pass the anti-explosion rules (`asset_definitions.md` §7.2) but collectively don't cohere as one domain model.

This document is the missing middle step: before any of the four words are proposed for real, re-check that each gap is still real and correctly placed, design the four together as one bundle, and stress-test reuse and individuation claims that M20 recorded but did not need to defend in depth (an analysis milestone's job is breadth across five bindings; this milestone's job is depth on one). No vocabulary is added here — the deliverable is a design ready for a future Step 2 extension milestone to execute against, the same relationship this document's own §8 recommendation bears to that future milestone.

---

## 2. Re-Validation of the Four Identified Gaps

Each of M20's four PROPERTY candidates (`asset_model_gap_analysis.md` §3.3, §5: C2, C3, C4, C7), re-checked against the vocabulary as it stands today — after M21's `NAV_WINDOW` and M23's `COUPON`/`SCHEDULED_TERMINAL`, neither of which existed when M20 wrote its table.

### 2.1 Axis 4 — Valuation (C2, appraisal valuation)

**Still real?** Yes. `ValuationQuestion` today has `IDENTITY` (fixed face amount, no question), `CONTINUOUS_QUOTATION` (continuously observed market price), and `PERIODIC_NAV` (a periodic, published net-asset-value calculation). Property has none of these: there is no face amount, no continuous market, and — the word most worth checking explicitly, since it is the newest addition an author might reach for — no periodic recurring valuation cadence. `PERIODIC_NAV` presumes a *scheduled*, recurring calculation (daily or weekly, the way a fund publishes NAV); a property appraisal is event-triggered (a sale, a refinancing, a scheduled portfolio revaluation date chosen by the holder, not the kind) and produces a professional judgment, not an aggregation formula. Reusing `PERIODIC_NAV` for property would misdescribe the cadence, not merely under-describe it — a `PERIODIC_NAV`-declaring engine could reasonably assume a computable, formula-driven value exists on a fixed schedule, which is false for an appraisal.

**Correctly located?** Yes — Axis 4 is defined as "what may it be asked to be worth, and when?" (`asset_definitions.md` §5.1.4); appraisal cadence is exactly that question's answer for this kind, not a different axis wearing a valuation costume.

**Verdict:** confirmed gap, Axis 4.

### 2.2 Axis 2 — Acquisition (C3, negotiated acquisition)

**Still real?** Yes. `AcquisitionSemantics` today has `NOT_TRANSACTABLE`, `VENUE_TRADED`, and `NAV_WINDOW` (M21). `NAV_WINDOW` is the word most worth checking explicitly, since it is the newest and — like `PERIODIC_NAV` above — was minted for a different kind (FUND) with a superficially similar "not a continuous venue" shape. But `NAV_WINDOW` names subscription and redemption struck *against the issuer* at a *published NAV* — a mechanism that presumes an issuer, an ongoing pool, and a periodic published price. Property acquisition has none of these: there is no issuer to subscribe against, no NAV to strike at, and no window — each transaction is a bespoke, bilateral negotiation between two counterparties over a price arrived at case-by-case. Reusing `NAV_WINDOW` would be as dishonest as reusing `VENUE_TRADED`; neither existing mechanism is what actually happens.

**Correctly located?** Yes — Axis 2 asks "how does it change hands," and bilateral negotiation is a mechanism answer to exactly that question, not an acquisition-adjacent fact belonging elsewhere.

**Verdict:** confirmed gap, Axis 2.

### 2.3 Axis 3 — Settlement (C4, manual/negotiated settlement)

**Still real?** Yes. `SettlementPattern` today has only `INSTANT` and `CYCLE_BASED`. `CYCLE_BASED` presumes a *standard* cycle length — T+1, T+2, a fixed number of days after trade, refined per-instance (D10) but structurally the same shape for every trade of the kind. A property closing has no standard cycle: the date is itself a negotiated term of the transaction, contingent on financing, inspection, and title contingencies that vary transaction to transaction, not merely in length but in *shape* (a closing can be extended, made contingent, or renegotiated in ways a settlement cycle cannot). This is a different settlement pattern, not a longer cycle.

**Correctly located?** Yes — Axis 3 asks "when is a change of hands real," and a negotiated closing date is exactly that question's answer here.

**Verdict:** confirmed gap, Axis 3.

### 2.4 Axis 5 — Flows (C7, rent)

**Still real, and — the one gap most worth checking against a *new* word since M20 — could `COUPON` (M23) now express it?** No, on both counts. `FlowType` today has `INTEREST`, `DIVIDEND`, and `COUPON`. `COUPON`'s own docstring (`vocabulary.py`) scopes it deliberately: "a periodic, contractually-fixed income flow" tied to "a held instrument" with a redemption/principal relationship in mind — its own reuse note names "private debt" as the anticipated next consumer, not property. Rent is a different economic relationship: income from a counterparty's continued *occupancy or use* of a physical asset under a lease, with no principal amount, no redemption event, and no necessary tie to a scheduled-terminal existence pattern (a property does not "mature"; a lease term is a relationship-level fact about the tenancy, not the property's own existence pattern). Reusing `COUPON` for rent would conflate a creditor's yield on a principal with a landlord's income from use — a real behavioral difference an accounting engine would eventually need to tell apart (rent has no accrual-to-principal relationship to reconcile; a coupon does), which is precisely the D3 "some engine must behave differently" test.

This check matters because it is exactly the discipline M24 applied to BOND's event-family question and M22 applied to FUND's valuation question: before proposing a new word, confirm the newest existing word on the same axis doesn't already cover the case. It doesn't here — `COUPON` and `RENT` are genuinely different income characters, not two names for one concept.

**Correctly located?** Yes — Axis 5 asks "what does holding it generate," and rent is a holding-generated flow like any other.

**Verdict:** confirmed gap, Axis 5.

### 2.5 Is a different abstraction preferable? (bundle-level check)

One risk worth naming explicitly, since two of the four candidates both carry the word "negotiated": is Axis 2's negotiated acquisition and Axis 3's negotiated settlement actually *one* concept spuriously split across two axes, the way an umbrella word would be (`asset_definitions.md` §6.3's "no composite words" concern, applied in reverse — one concept masquerading as two)?

They are not the same concept. Axis 2 answers "how do two parties agree to transact at all" (mechanism of price discovery and counterparty-finding); Axis 3 answers "when does an agreed transaction become real" (timing and finality of the change of hands). These are already independent questions for every existing definition — Equity v1 answers them as `VENUE_TRADED` + `CYCLE_BASED`, two different mechanisms describing one economic event (a market trade) from two different engines' vantage points (the trade-matching mechanism vs. the ledger's booking timing). Property answers both questions with "negotiated" only because, for this kind, *both* the mechanism and the timing happen to be bespoke and bilateral — a coincidence of this kind's real-world shape, not evidence the platform's axis split is wrong. The two words remain independently necessary and independently owned (§3 below), the same way `VENUE_TRADED` and `CYCLE_BASED` are two words for one Equity trade rather than one word split in half.

**Conclusion:** all four gaps from M20 are re-confirmed as real, correctly axis-located, and not expressible by any word added since M20 (`NAV_WINDOW`, `COUPON`, `SCHEDULED_TERMINAL`). No fifth gap surfaced, and no existing candidate collapsed into another. The bundle is exactly the four axes M20 found, now argued in depth rather than asserted.

---

## 3. Vocabulary Candidate Table

| Candidate name | Axis / enum | Semantic definition | Owning engine | D1 contribution | Relationship to existing vocabulary |
|---|---|---|---|---|---|
| `NEGOTIATED_TRANSFER` | Axis 2 · `AcquisitionSemantics` | Acquisition and disposal by bilateral, case-by-case negotiation between counterparties — no continuous venue matching bids and offers, no periodic published NAV to transact against, no issuer subscription/redemption relationship. | Asset Foundation (the mint/registration path that knows the mechanism by which an instance actually changes hands — the same owner `NAV_WINDOW`'s docstring names for this axis; §5.1 axis 2's "how does it change hands" is this subdomain's own question, distinct from Market Intelligence's worth question). | PROPERTY declares a mechanism no canonical definition currently declares — automatic individuation on this axis alone against CASH (`NOT_TRANSACTABLE`), EQUITY/ETF/BOND (`VENUE_TRADED`), FUND (`NAV_WINDOW`). | New third-axis-sibling member alongside `NOT_TRANSACTABLE`/`VENUE_TRADED`/`NAV_WINDOW`; none of the three existing members' meaning changes. |
| `NEGOTIATED_CLOSING` | Axis 3 · `SettlementPattern` | A settlement date and process individually agreed per transaction — not a standard fixed-length cycle after trade, not instantaneous — commonly contingent on financing, inspection, or title conditions that can extend or renegotiate the closing itself. | Ledger & Accounting (the subdomain that books a change of hands as real and needs to know the shape of "when," the same way it already consumes `INSTANT`/`CYCLE_BASED`; distinct from Axis 2's mint-time mechanism question). | Same effect as `NEGOTIATED_TRANSFER` — no canonical definition today declares any settlement pattern but `INSTANT`/`CYCLE_BASED`; PROPERTY individuates on this axis independent of every other. | New second-axis-sibling member alongside `INSTANT`/`CYCLE_BASED`; neither existing member's meaning changes. |
| `APPRAISAL_ON_EVENT` | Axis 4 · `ValuationQuestion` | Worth is established by a professional appraisal triggered by an event (a sale, a refinancing, a holder-chosen revaluation date) — a third, distinct question-shape from a continuously observed market price and from a scheduled, formula-driven periodic calculation. Cadence and question-shape only, per D2 — never an appraisal methodology or a price. | Market Intelligence (the same owner named for `CONTINUOUS_QUOTATION` and `PERIODIC_NAV`; §5.1 axis 4 — "what may it be asked to be worth, and when"). | No canonical definition today declares any valuation question but `IDENTITY`/`CONTINUOUS_QUOTATION`/`PERIODIC_NAV`; independent individuation on this axis. | New fourth-axis-sibling member; existing three members' meaning unchanged. Name matches the constitution's own phrase verbatim (`asset_definitions.md` §5.1.4: "continuous quotation, periodic NAV, appraisal-on-event, or identity"). |
| `RENT` | Axis 5 · `FlowType` | A holding-generated income flow arising from a counterparty's continued occupancy or use of a physical asset under a lease or similar arrangement — distinct from `DIVIDEND` (discretionary, issuer-declared), `INTEREST` (balance accrual), and `COUPON` (contractually-fixed yield against a held instrument's principal, per §2.4 above). | Ledger & Accounting (the same owner named for `COUPON`/`DIVIDEND`/`INTEREST`; §5.1 axis 5 — "what does holding it generate"). | No canonical definition today grants any flow but `INTEREST`/`DIVIDEND`/`COUPON`; independent individuation on this axis. | New fourth-axis-sibling member alongside `INTEREST`/`DIVIDEND`/`COUPON`; none of the three existing members' meaning changes. Name matches the constitution's own §5.1.5 and §9 Property-walk wording verbatim ("rent flow"). |

All four pass the anti-explosion rules (`asset_definitions.md` §7.2) individually: each names a mechanism or income character, not a proper noun; each is a genuine behavioral difference an owning engine must eventually honor (D3); none is a synonym or umbrella for an existing word (§2 above argues this explicitly for the two "negotiated" words and for `RENT` vs. `COUPON`); each names its family (its axis) rather than inventing one.

---

## 4. Reuse Analysis

Per the brief: examples are illustrative, not assumed future bindings. Each candidate's plausible consumers, checked rather than accepted at face value.

| Candidate | Plausible future consumers | Scrutiny |
|---|---|---|
| `NEGOTIATED_TRANSFER` | Physical exposure Commodity (if that scope branch is chosen, M20 §3.5); future Business/private-ownership (`asset_definitions.md` §9's own next walk after Property); Infrastructure held as direct private ownership. | **Not** a listed REIT — a publicly-traded REIT is `VENUE_TRADED` like any other listed security and needs none of this bundle. A *non-traded* REIT or property fund, however, is more likely `NAV_WINDOW`-shaped (subscription/redemption against a published NAV) than `NEGOTIATED_TRANSFER`-shaped (no bilateral price negotiation occurs) — so REIT is a genuinely mixed case whose actual future word depends on the specific structure, not a clean consumer of this bundle. Recorded so the brief's own example list is not treated as a requirements list, the same discipline M20 §5 applied to its own brief's examples. |
| `NEGOTIATED_CLOSING` | Same pairing as `NEGOTIATED_TRANSFER` — Business, physical Commodity, direct-ownership Infrastructure. | Insurance Assets (a brief example) is a weak fit on inspection: most insurance-linked instruments (cat bonds, life settlements) that reach a platform would more plausibly need venue-traded or negotiated-*acquisition* semantics with standard-cycle or instant settlement, not a bespoke negotiated closing process — flagged as speculative, not a confident consumer. |
| `APPRAISAL_ON_EVENT` | Property, physical Commodity, future Business/private-ownership (the same trio M20 §5 named for C2); Private Assets generally — a private equity or private credit stake carried at a periodic professional/GP mark is a genuine appraisal-on-event shape, arguably the broadest reuse candidate in this bundle. | Highest-confidence reuse of the four, matching M20's own note that C2 seeds "future Business" — the appraisal *question-shape* (event-triggered professional judgment) generalizes further than the specific mechanism words do, since many different acquisition/settlement shapes can still share one valuation answer. |
| `RENT` | PROPERTY (the only confirmed consumer, matching M20's own finding). | Infrastructure assets that earn a usage or occupancy fee (a toll road, a leased facility) share `RENT`'s income character in kind, but this is a tentative, unconfirmed extension noted for completeness — not asserted as a real future binding, per the brief's own "do not assume they will exist" instruction and the constitution's no-speculative-grants discipline (`asset_definition_library.md` §3.3) applied here to vocabulary rather than to a specific definition's grants. |

**Reading against ENGINEERING_PRINCIPLES.md's "reuse before create":** the bundle's four words are, in aggregate, the platform's second-largest single reuse investment identified to date (after M20's own ranking of `SCHEDULED_TERMINAL` as the single highest-reuse word) — `APPRAISAL_ON_EVENT` alone plausibly serves three future bindings, and the negotiated-mechanism pair serves two, before any of the four have been used for anything but Property.

---

## 5. Bundle Dependency Analysis

```
NEGOTIATED_TRANSFER (Axis 2)   ──┐
NEGOTIATED_CLOSING  (Axis 3)   ──┼── PROPERTY authorable once all four ship
APPRAISAL_ON_EVENT  (Axis 4)   ──┤    (order-independent among themselves —
RENT                (Axis 5)   ──┘    no candidate's meaning depends on another's)
        │
        ├── NEGOTIATED_TRANSFER + NEGOTIATED_CLOSING: independent enum members,
        │   but a matched conceptual pair (§2.5) — reviewing them in the same
        │   change lets governance verify they are not an accidental umbrella
        │   split (the check §2.5 already performs) before both are pinned.
        │
        ├── APPRAISAL_ON_EVENT: fully independent of the other three; highest
        │   reuse value (§4) — no reason to sequence it after the others.
        │
        └── RENT: fully independent of the other three; narrowest confirmed
            reuse (§4) — no reason to sequence it before the others.

Reuse dependencies (consumption, not word-on-word — same distinction M20 §7 drew):
  Business/private-ownership   ── needs NEGOTIATED_TRANSFER + NEGOTIATED_CLOSING
                                    + APPRAISAL_ON_EVENT once Property's cluster ships
  Physical-exposure Commodity  ── needs the identical three, IF that scope branch
                                    is chosen (M20 §3.5, unchanged by this document)
  Private Assets (equity/credit marks) ── needs APPRAISAL_ON_EVENT only
```

No candidate's construction or fingerprinting depends on another candidate's enum existing first — each is independently addable, the same property M20 §7 found across its own nine candidates. The only real dependency is **consumption**: PROPERTY itself needs all four before it is D1-authorable (§6 below), exactly as M20 already found for its own three-word cluster before this document added the fourth (`RENT`) explicitly into the same bundle. M20's own §8 recommendation had left `RENT`'s bundling with the other three ambiguous — naming it "a cluster" of "C2+C3+C4" while separately counting "four words counting Axis 5's RENT." This document resolves that ambiguity: all four ship together, as one governed extension event, because none has independent value to any binding before PROPERTY exists to consume it (unlike `PERIODIC_NAV`, which served ETF alone for a full milestone before FUND's later reuse, or `SCHEDULED_TERMINAL`, whose reuse case exists independent of BOND).

---

## 6. D1 Analysis

Once all four words exist, PROPERTY's minimal honest declaration would be: Unit — `DISCRETE`, indivisible (`permits_fractional_refinement=False`, `permits_lot_refinement=False`, already expressible today, no new word); Acquisition — `NEGOTIATED_TRANSFER`; Settlement — `NEGOTIATED_CLOSING`; Valuation — `APPRAISAL_ON_EVENT`; Flows — `{RENT}`; Event families — `∅` (honest absence, D7, Cash v1's own precedent — no new word); Existence — `OPEN_ENDED` (reuse; a property does not mature, so `SCHEDULED_TERMINAL` would misdescribe it — no new word here either).

No canonical definition today (CASH, EQUITY, ETF, FUND, BOND) declares `NEGOTIATED_TRANSFER`, `NEGOTIATED_CLOSING`, `APPRAISAL_ON_EVENT`, or `RENT` on any axis — PROPERTY would individuate on **four independent axes simultaneously**, the largest D1 margin of any definition admitted to the library so far (ETF: one axis, M18; FUND: one axis, M22; BOND: two axes, M24). This is worth defending explicitly against the brief's own warning ("avoid introducing vocabulary that exists solely to satisfy uniqueness"), because four new words is the kind of number that invites the suspicion:

**Is this manufactured uniqueness, or genuine description?** Genuine description, on two grounds. First, every one of the four words answers a question the constitution already asks of every kind (the seven axes are fixed, §5.1) — nothing here proposes a new *kind* of question, only an honest answer to four existing ones that no prior kind needed to answer this way. Second, the cheaper alternative — reusing an existing word on each axis rather than adding a true one — was checked and rejected on truthfulness grounds in §2 above, not on convenience grounds: declaring `VENUE_TRADED` or `NAV_WINDOW` for property acquisition, `CYCLE_BASED` for its settlement, `PERIODIC_NAV` for its valuation, or `COUPON` for its rent would each be a **misdescription** (D10's "an instance fact that contradicts its definition's vocabulary is a registration-time defect" applied one level up, to the definition's own honesty), not a legitimate economization. Four words are needed because Property is genuinely unlike every kind the library has described so far on four separate constitutional questions at once — not because four words make a more impressive-looking individuation margin.

Symmetrically, the bundle does **not** over-differentiate the axes that don't need it: Unit semantics, Event-family grants, and Existence pattern all reuse existing declarations exactly as M20 found (§3.3), with no new word proposed on any of them — the same "minimal truthful projection" discipline M22 and M24 already applied when they resisted narrowing Fund's and Bond's event-family/relationship grants "because the kind seemed atypical." This bundle only spends new vocabulary where genuine differentiation exists, and reuses everywhere it honestly can.

---

## 7. Recommended Extension Order

All four words are recommended to ship together, as **one** governed Step 2 extension milestone (not split across separate milestones the way FUND/BOND's single-and-double words were) — per §5's dependency finding, none has independent reuse value before PROPERTY exists to consume it, so there is no benefit to the staggered "ship the word, wait, author later" rhythm the smaller bindings used. Within that one milestone, a recommended internal sequence for review and commit ordering:

1. **`RENT` (`FlowType`)** first — the simplest of the four: a single new sibling on an axis whose extension pattern (`COUPON`, M23) is now twice-proven, and independent of every other candidate here. Lowest review risk, and the natural warm-up commit.
2. **`APPRAISAL_ON_EVENT` (`ValuationQuestion`)** second — independent of every other candidate, and the bundle's highest-confidence reuse case (§4); proving it early is the cheapest validation of this document's central reuse claim.
3. **`NEGOTIATED_TRANSFER` (`AcquisitionSemantics`)** and **`NEGOTIATED_CLOSING` (`SettlementPattern`)** third and fourth, reviewed together — the matched conceptual pair identified in §2.5; committing them adjacently lets a reviewer directly compare the two "negotiated" words side by side and confirm they remain two independent axis-answers rather than one concept accidentally split (the check this document performs in §2.5, re-performable by any future reviewer at the point the words are actually proposed).

This order optimizes the same three criteria M20 §8 used for its cross-binding sequencing, applied here within one binding's cluster: **maximum reuse proven early** (`APPRAISAL_ON_EVENT` second, not last), **minimum churn per reviewable unit** (simplest word first), **minimum governance risk** (the pair most likely to raise a "is this really two words" question reviewed together, not separately, so the question is asked once with full context rather than twice in isolation).

---

## 8. What This Document Deliberately Does Not Do

Per the brief's non-goals: no word above has been added to `vocabulary.py`; no `AssetType` PROPERTY definition has been drafted; `readiness_report.py`, `enforcement_decisions.py`, `library.py`, `registry.py`, and every pinned fingerprint are byte-identical to their M24 state; no runtime, registry, or capability-projection change is proposed or required. No structural validation test was added for this milestone — the deliverable is prose and tables with no executable surface to check, and the brief's own instruction ("only add structural validation if analysis artifacts require consistency checks") found no such need here, unlike M20 whose gap matrix cross-referenced live code state in ways worth a future test guarding (none of that document's own claims were test-guarded either, for the same reason).

**One finding worth recording for a future milestone** (per the brief's "Update DECISION_LOG.md if architectural findings arise"): `readiness_report.py`'s and `enforcement_decisions.py`'s current PROPERTY rows both name only the Axis 4 (valuation) gap ("ValuationQuestion has no appraisal-pricing member") as PROPERTY's blocker, not all four axes this document (and M20 before it) found missing. This is the same class of staleness M20 found and recorded for FUND's and BOND's rows without correcting them in that milestone — and is left uncorrected here for the identical reason: fixing hand-authored rationale text is in scope for whichever future milestone actually ships this vocabulary bundle (the same discipline that milestone will inherit from M21/M23's own precedent of updating the row only once the gap actually closes), not this design-only one.

---

## Related Documents

- [asset_model_gap_analysis.md](asset_model_gap_analysis.md) — M20's platform-wide survey; §3.3, §5, §6, §7, §8 are this document's starting point, re-validated and deepened for PROPERTY alone
- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution; §5.1's seven axes, §7.2's anti-explosion rules, §8.1's evolution ladder, and §9's own Property walk (itself corrected by M20, unchanged by this document)
- [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the eight-stage process a future PROPERTY-authoring milestone will walk once this bundle ships
- [definition_review_checklist.md](definition_review_checklist.md) — item 1 ("Vocabulary complete?") is this document's method, applied in depth to one binding instead of across five
- [asset_definition_bond.md](asset_definition_bond.md) — BOND v1 (M24), the most recent precedent for a multi-axis individuation (two axes) and for the "reuse the newest sibling word first" check §2 applies here to `NAV_WINDOW`/`COUPON`
- [../../backend/services/asset_definitions/vocabulary.py](../../backend/services/asset_definitions/vocabulary.py) — the closed vocabulary this bundle proposes extending, unchanged by this milestone
- [../../backend/services/asset_definitions/readiness_report.py](../../backend/services/asset_definitions/readiness_report.py) — PROPERTY's row, found imprecise by §8 above, left uncorrected per this milestone's non-goals
- [../../backend/services/asset_definitions/enforcement_decisions.py](../../backend/services/asset_definitions/enforcement_decisions.py) — PROPERTY's row, same finding
- [../GLOSSARY.md](../GLOSSARY.md) — source of the illustrative (not governed) "Rent" and axis-4 word lists this document's names were checked against
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — where this milestone's findings and any future vocabulary extension are recorded
