# Asset Model Gap Analysis

_Milestone M20. Analysis only — no vocabulary extension, no new Asset Definition, no runtime/library/readiness/enforcement change. Produced against the vocabulary and library as they stood after [M19](../engineering/DECISION_LOG.md) (`library.DEFINITION_LADDERS = {CASH, EQUITY, ETF}`)._

| | |
|---|---|
| **Status** | Analysis document (M20) — non-binding, non-executable |
| **Scope** | FUND, BOND, PROPERTY, CRYPTO, COMMODITY (the five remaining non-exempt `AssetType` members) |
| **Companion** | [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the process this analysis feeds *into*, once a gap is actually closed |
| **Reads as input** | [vocabulary.py](../../backend/services/asset_definitions/vocabulary.py), [readiness_report.py](../../backend/services/asset_definitions/readiness_report.py), [enforcement_decisions.py](../../backend/services/asset_definitions/enforcement_decisions.py), [asset_definitions.md](../architecture/asset_definitions.md) §9 |

---

## 1. Purpose

[asset_definitions.md](../architecture/asset_definitions.md) §9 sketches a worked "evolution ladder" walk for several future classes, and `readiness_report.py`/`enforcement_decisions.py` already carry a one-line, hand-authored rationale per `AssetType`. Both are true but incomplete: the constitution's walks are illustrative prose written to argue the *pattern* works, not a verified check against the actual `vocabulary.py` enums; the readiness table's rationale is a single sentence per binding, written once (M15) and touched only when a specific milestone happened to revisit one row (M16, M18 — both ETF only).

This document does the axis-by-axis check the prose walks never did against the *real* current vocabulary, for all five remaining bindings at once, and groups the result by reusable concept rather than by binding — the brief's central instruction: "do not add one vocabulary member per AssetType without first checking whether a more general semantic concept exists."

Three findings fell out of doing this that are corrections to existing, checked-in artifacts, not new opinions:

1. **`readiness_report.py`'s FUND row is stale.** It states `ValuationQuestion` has no NAV-pricing member — true when M15 wrote it, false since M17 shipped `PERIODIC_NAV` for ETF. Nobody revisited FUND's row because M17's brief scoped the word to ETF's need only. FUND's real remaining gap is narrower and different (§3.1).
2. **The constitution's own Property walk (§9) is wrong against the shipped vocabulary.** It calls Property "Step 1, mostly by honest absence." Checked against `vocabulary.py`, Property needs *four* new words — the largest single-type ask of the five (§3.3). The prose was written aspirationally, ahead of `vocabulary.py`'s actual contents, and never reconciled.
3. **Crypto's "already-reserved" staking word is not reserved anywhere in code.** `vocabulary.py`'s own module docstring quotes the constitution's "already-reserved staking flow" language, but `FlowType` has never had a `STAKING` member. "Reserved" describes a sentence in a document, not a governed vocabulary entry (§3.4).

None of these are blocking defects — nothing downstream currently depends on the stale text being accurate — but a future author who trusts `readiness_report.py`'s FUND rationale at face value would start the wrong governed extension. This is recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md)'s M20 entry as required by the brief ("Update DECISION_LOG.md if architectural findings are discovered"); the files themselves are deliberately left untouched, per this milestone's non-goals — correcting them is in scope for whichever future milestone actually closes each gap, not this one.

---

## 2. Method

For each of the five bindings, three questions were asked against the actual current state of `backend/services/asset_definitions/vocabulary.py` (not against the constitution's prose, which is a design intent, and not against `readiness_report.py`'s existing text, which is a claim that itself needed checking):

1. **Which of the seven axes (§5.1) can already be honestly declared** using an existing word, and which cannot?
2. **For every axis that cannot**, is the blocker a missing *word* on an existing axis (a Step 2 vocabulary extension), or a missing *decision* about what the kind even means on this platform (a scope question no vocabulary addition resolves)?
3. **Would the resulting declaration set, once every gap is closed, actually individuate (D1)** against every currently-canonical definition (Cash v1, Equity v1, ETF v1) — checked the way M16 should have checked ETF the first time, not assumed from the axis names alone?

The same three questions, answered honestly, are what §3.2's `definition_review_checklist.md` items 1–3 will later demand of whoever actually authors each definition. This document exists so that milestone starts from an answered checklist instead of a blank one.

---

## 3. Per-AssetType Analysis

### 3.1 FUND

**Can it already be expressed? Mostly — as of M17, more than `readiness_report.py` currently credits.**

| Axis | Existing word available? | Notes |
|---|---|---|
| 1. Unit | Yes — `Divisibility.DISCRETE`, `permits_fractional_refinement=True` | Fund units are commonly fractionally allocated at subscription; no new word needed. |
| 2. Acquisition | **No.** | Open-ended funds are bought/sold through NAV-window subscription/redemption directly with the fund — not `NOT_TRANSACTABLE`, and declaring `VENUE_TRADED` would misdescribe the mechanism (there is no continuous order-book venue) as well as collide with ETF's declaration set under D1 (see below). This is FUND's real, sole vocabulary gap today. |
| 3. Settlement | Plausibly yes — `SettlementPattern.CYCLE_BASED`, `permits_cycle_length_refinement=True` | NAV-window redemption settles some fixed number of days after the strike, which `CYCLE_BASED` already honestly covers (same as Equity/ETF); worth confirming at authoring time, not a blocking gap today. |
| 4. Valuation | **Yes — `ValuationQuestion.PERIODIC_NAV` (M17).** | The word `readiness_report.py`'s FUND row still claims is missing. M17 added it for ETF's individuation need, but the word itself is binding-agnostic — nothing in `vocabulary.py`, `declarations.py`, or `capability_view.py` scopes it to ETF. This is the reuse the brief asks to look for, already realized once, unnoticed. |
| 5. Flows | Yes — `FlowType.DIVIDEND` | ETF v1 already reuses `DIVIDEND` for its distributions (M18) rather than declaring a separate word; the same precedent applies to fund distributions. A distinct `DISTRIBUTION` flow character is a candidate (§6) if a real accounting difference is later found, not asserted here. |
| 6. Event families | Yes, by honest absence or partial reuse | Funds don't split/spin-off the way listed equities do; a smaller or empty grant is a legitimate declaration (D7), decided at authoring time. |
| 7. Existence | Yes — `ExistencePattern.OPEN_ENDED` | "Open-ended fund" is literally the pattern's name. No gap. |

**D1 individuation check.** If FUND declared `PERIODIC_NAV` valuation and reused every other axis ETF_V1 uses (`VENUE_TRADED`, `DISCRETE`, `CYCLE_BASED`, `{DIVIDEND}`, ETF's event-family set, ETF's relationship set), it would be **byte-identical to ETF_V1** — a D1 violation, the exact mistake M16 made once already. The missing acquisition word is therefore not a nice-to-have; it is the thing that makes FUND individuable at all now that `PERIODIC_NAV` is shared. Once a NAV-window acquisition word exists, FUND's minimal shape mirrors ETF's own M18 precedent exactly: identical to ETF_V1 on every axis except Axis 2.

**Verdict:** one new word (Axis 2, acquisition), not the valuation word `readiness_report.py` currently names. Smallest single-word gap of the five bindings.

---

### 3.2 BOND

**Can it already be expressed? No — two words, both long-anticipated.**

| Axis | Existing word available? | Notes |
|---|---|---|
| 1. Unit | Yes — `Divisibility.DISCRETE` | Bonds are discrete-denomination instruments; no new word needed. |
| 2. Acquisition | Plausibly yes — `AcquisitionSemantics.VENUE_TRADED` | Most bond markets are exchange-listed or OTC-quoted in a venue-traded sense; open question for authoring time whether OTC bond trading is honestly `VENUE_TRADED` or needs the same negotiated-mechanism word Property needs (§3.3) — flagged, not resolved, here. |
| 3. Settlement | Yes — `SettlementPattern.CYCLE_BASED` | Standard cycle settlement; no new word needed. |
| 4. Valuation | Yes — `ValuationQuestion.CONTINUOUS_QUOTATION` | Exchange/OTC-quoted bonds fit the existing continuous-quotation word; no new word needed. |
| 5. Flows | **No.** | `FlowType` has `INTEREST` and `DIVIDEND` only. A bond coupon is a distinct, scheduled, contractually-fixed flow — constitution §9 names `COUPON` explicitly as one of Bond's two anticipated words. |
| 6. Event families | Arguably yes, by absence — but see below | `readiness_report.py`/`enforcement_decisions.py` both currently state Bond's gap as *"EventFamily has no maturity/coupon-redemption member."* This is not what the constitution's own §9 Bond walk says. |
| 7. Existence | **No.** | Constitution §9: *"the scheduled-terminal existence pattern (maturity as a known-in-advance terminal status; a call as an early one)."* `ExistencePattern` has exactly one member, `OPEN_ENDED`. This — not event families — is Bond's second anticipated word. |

**Correction to existing artifacts.** `readiness_report.py`'s and `enforcement_decisions.py`'s Bond rows both locate the gap on the *event-family* axis; the constitution's own worked example locates it on the *existence* axis (plus the flow axis, separately). Both readings have some merit — a bond redemption or early call could plausibly also want a discrete `EventFamily` grant (the way `EventFamily.DELISTING` marks an equity leaving its exchange), the same way Option/Future's later walks add exercise/expiry event families on top of their own existence-pattern words — but the constitution's literal Bond walk names only the flow word and the existence word as required, treating the event family question as open. This document does not resolve which is right; it is exactly the kind of question `definition_review_checklist.md` item 1 ("Vocabulary complete?") exists to force explicit, before authoring starts, not silently inherited from a stale rationale string.

**D1 individuation check.** Once `SCHEDULED_TERMINAL` exists, Bond individuates from every current definition trivially — no other canonical definition today declares any existence pattern but `OPEN_ENDED`, so the very first bond declaration is automatically distinct on that axis alone, independent of every other axis's content. Lowest individuation risk of the three `VOCABULARY_GAP` bindings.

**Verdict:** two new words minimum (Axis 5 `COUPON`, Axis 7 `SCHEDULED_TERMINAL`), with a third (an event-family word for redemption/call) an open authoring-time question, not a confirmed requirement.

---

### 3.3 PROPERTY

**Can it already be expressed? No — and not "Step 1" as the constitution currently claims.**

Constitution §9: *"Property — Step 1, mostly by honest absence: negotiated acquisition, manual settlement, appraisal valuation, rent flow, no event families, open-ended existence, indivisible unit semantics."* Checked word-by-word against `vocabulary.py`:

| Axis | Existing word available? | Notes |
|---|---|---|
| 1. Unit | Yes — `Divisibility.DISCRETE`, `permits_fractional_refinement=False`, `permits_lot_refinement=False` | "Indivisible" is expressible today. No gap. |
| 2. Acquisition | **No.** | `AcquisitionSemantics` has `NOT_TRANSACTABLE` and `VENUE_TRADED` only — no negotiated/private-transfer word. |
| 3. Settlement | **No.** | `SettlementPattern` has `INSTANT` and `CYCLE_BASED` only — no manual/negotiated-closing word. |
| 4. Valuation | **No.** | `ValuationQuestion` has `IDENTITY`, `CONTINUOUS_QUOTATION`, `PERIODIC_NAV` — no appraisal-on-event word. |
| 5. Flows | **No.** | `FlowType` has `INTEREST`, `DIVIDEND` — no rent word. |
| 6. Event families | Yes, by honest absence | "No event families" is a legitimate empty grant (D7, Cash v1's own precedent). No gap. |
| 7. Existence | Yes — `OPEN_ENDED` | No gap. |

Four of seven axes need a new word — the constitution's "mostly by honest absence" framing describes only axes 1, 6, and 7. This is the most vocabulary-hungry binding of the five, the opposite of its billing in §9, most likely because §9's prose was drafted to demonstrate the *ladder pattern* works across many classes and was never reconciled against `vocabulary.py`'s actual, later-frozen contents (`vocabulary.py`'s own history: only `PERIODIC_NAV` has ever actually been added, M17, for a completely different binding).

**D1 individuation check.** Once all four words exist, Property is trivially distinct from every current definition — no other definition declares negotiated acquisition, manual settlement, or appraisal valuation on any axis. Low individuation risk, same reasoning as Bond, once the words exist.

**Verdict:** four new words (Axes 2, 3, 4, 5) — a single, sizable, self-contained vocabulary-extension event, not a sequence of small ones. See §5 for why this cluster is also the platform's highest-reuse investment.

---

### 3.4 CRYPTO

**Can it already be expressed? Mostly — one open scope question, one deliberately deferred word.**

Constitution §9: *"Crypto — Step 1 with one or two Step-2 words: continuous quantity, near-instant settlement, continuous quotation, the already-reserved staking flow."*

| Axis | Existing word available? | Notes |
|---|---|---|
| 1. Unit | Yes — `Divisibility.CONTINUOUS` | No gap. |
| 2. Acquisition | Yes — `AcquisitionSemantics.VENUE_TRADED` | Crypto exchanges fit the existing venue-traded mechanism; the specific exchange is an instance fact (D10), same as any listed equity. No gap. |
| 3. Settlement | **Open — this is the actual `SCOPE_UNDECIDED` question, not a missing word.** | `readiness_report.py`'s own rationale: *"24/7, no traditional settlement cycle — fit against `SettlementPattern`'s INSTANT/CYCLE_BASED dichotomy is unconfirmed."* Whether on-chain, block-confirmed settlement is honestly `INSTANT` (the constitution's own prose leans this way — "near-instant") or needs its own semantic (variable finality, probabilistic confirmation, unlike cash's true instantaneity) is a domain-review judgment call, not something a vocabulary addition resolves by itself — the platform first has to decide what claim it is willing to make about crypto settlement before knowing whether a word is even missing. |
| 4. Valuation | Yes — `ValuationQuestion.CONTINUOUS_QUOTATION` | No gap. |
| 5. Flows | **Deferred, not blocking.** | `FlowType` has no `STAKING` member despite the constitution's phrase "the already-reserved staking flow" — see the correction in §3.5 below. Constitution §9 itself defers this: *"Fork and airdrop are candidate event families argued when a real position demands them — not before."* The same "not before a real need" discipline applies to staking; it is a real gap only the moment a staking position is actually modeled, and should not be added speculatively per the constitution's own no-speculative-grants style law (§3.3 of `asset_definition_library.md`) applied to vocabulary. |
| 6. Event families | Yes, by honest absence (deferred fork/airdrop excepted) | No blocking gap. |
| 7. Existence | Yes — `OPEN_ENDED` | No gap. |

**Verdict:** Crypto is *not* a vocabulary gap in the same sense as FUND/BOND/PROPERTY. Its blocker is a domain-review decision on Axis 3 (does the existing `INSTANT` word honestly describe blockchain settlement, or does the axis need a new member) — correctly classified `SCOPE_UNDECIDED`, distinct in *kind*, not just severity, from `VOCABULARY_GAP`. The staking flow is a second, independent, deliberately-deferred item that should not gate Crypto's authoring at all.

---

### 3.5 COMMODITY

**Can it already be expressed? Unknown — the question itself is not yet defined.**

Commodity is the one remaining binding with **no worked example anywhere in `asset_definitions.md` §9** — Cash, ETF, Bond, Option, Future, Crypto, Property, Business, and "Derivatives in general" are all walked; Commodity is not. `readiness_report.py`'s own rationale is the most upstream of any binding's: *"physical vs. derivative exposure not yet chosen as what 'COMMODITY' means here."*

This is not one axis-by-axis analysis but two, because the binding name currently covers two structurally different kinds of instrument that a platform decision has not yet separated:

- **Physical commodity exposure** (owning gold bars, warehoused grain) is, axis-for-axis, the same shape as Property: negotiated acquisition, manual/negotiated settlement, appraisal-or-spot valuation, no income flow, no event families, open-ended existence, continuous or discrete unit depending on the specific commodity. It would draw entirely on the vocabulary cluster Property already needs (§3.3, §5) — **zero new words**, if that cluster ships first.
- **Derivative/exchange-traded commodity exposure** (a commodity ETC, a futures-tracking product) is, axis-for-axis, the same shape as ETF: venue-traded, discrete units, cycle settlement, continuously quoted, no income flow (or a small distribution grant), corporate-action-like event set. It would draw entirely on the vocabulary ETF already shipped — **zero new words**, full stop, today.

Both branches individuate against existing definitions trivially (physical: same reasoning as Property; derivative: differs from ETF at minimum by its flow grant, likely none vs. ETF's `DIVIDEND`). Neither branch is blocked by vocabulary. **The entire blocker is the platform-scope decision of which shape — or both, as two separate future bindings — "COMMODITY" is meant to describe**, which is a product/domain decision, not an engineering one, and out of this analysis milestone's authority to make.

**Verdict:** no vocabulary gap under either interpretation; a pure scope decision, fully deferred until Property (if physical) or immediately (if derivative, reusing ETF's shape as-is) — see §8.

---

## 4. Asset Model Gap Matrix

| AssetType | Current readiness | Missing declaration axes | Missing vocabulary | Shared abstraction | Owning engine (for the missing word) | Blocker kind |
|---|---|---|---|---|---|---|
| FUND | `VOCABULARY_GAP` (stale rationale — see §1, §3.1) | Axis 2 (Acquisition) | NAV-window subscription/redemption acquisition semantics | Reuses Axis 4's `PERIODIC_NAV` (M17, shared with ETF) | Market Intelligence has none new; the acquisition word's owner is the mint/registration path (Asset Foundation itself, per Axis 2's "how does it change hands") | Vocabulary (1 word) |
| BOND | `VOCABULARY_GAP` | Axis 5 (Flows), Axis 7 (Existence); Axis 6 (Event families) — open question | `COUPON` flow; `SCHEDULED_TERMINAL` existence pattern; possibly a redemption/call event family | `SCHEDULED_TERMINAL` reusable by Option, Future, any future maturity-shaped kind | Ledger & Accounting (coupon flow); Lifecycle & Structural Events (existence pattern) | Vocabulary (2–3 words) |
| PROPERTY | `VOCABULARY_GAP` | Axis 2, 3, 4, 5 | Negotiated acquisition; manual/negotiated settlement pattern; appraisal valuation; `RENT` flow | Acquisition/settlement/valuation cluster reusable by Business (private ownership) and physical Commodity | Asset Foundation (acquisition, settlement mechanism words); Market Intelligence (appraisal valuation); Ledger & Accounting (rent flow) | Vocabulary (4 words) |
| CRYPTO | `SCOPE_UNDECIDED` | Axis 3 (Settlement) — open question, not confirmed missing | None confirmed; `STAKING` flow deliberately deferred | Settlement-fit decision has no reuse value elsewhere today (crypto's 24/7 model is currently unique among the five) | Market Intelligence / domain review, not an implementation owner yet | Scope decision, not vocabulary |
| COMMODITY | `SCOPE_UNDECIDED` | None — contingent entirely on which of two shapes is chosen | None under either interpretation | 100% reuse: either ETF's existing cluster (derivative) or Property's future cluster (physical) | N/A — no new implementation owner under either branch | Scope decision, not vocabulary |

_Estimated implementation order is stated as its own recommendation in §8, not folded into this matrix, because it depends on the cross-binding reuse analysis in §5 rather than any single row._

---

## 5. Reusable Domain Concepts

Grouped by concept rather than by binding, per the brief's instruction. Each concept names the axis it lives on, which vocabulary member(s) it corresponds to, and which of the five bindings would consume it.

| # | Concept | Axis | Vocabulary member(s) | Status | Consumers |
|---|---|---|---|---|---|
| C1 | Periodic reference valuation | 4 (Valuation) | `ValuationQuestion.PERIODIC_NAV` | **Already shipped (M17)** | ETF (shipped), FUND (candidate) |
| C2 | Appraisal / event-driven valuation | 4 (Valuation) | new `ValuationQuestion` member | Candidate | PROPERTY, physical COMMODITY, future Business |
| C3 | Negotiated acquisition | 2 (Acquisition) | new `AcquisitionSemantics` member | Candidate | PROPERTY, physical COMMODITY, future Business |
| C4 | Manual/negotiated settlement | 3 (Settlement) | new `SettlementPattern` member | Candidate | PROPERTY, physical COMMODITY, future Business |
| C5 | NAV-window subscription/redemption acquisition | 2 (Acquisition) | new `AcquisitionSemantics` member | Candidate | FUND (only consumer identified today; future money-market-fund-shaped kinds would reuse it) |
| C6 | Coupon income flow | 5 (Flows) | new `FlowType` member | Candidate | BOND (only consumer identified today; future private-debt-shaped kinds would reuse it) |
| C7 | Rent income flow | 5 (Flows) | new `FlowType` member | Candidate | PROPERTY (only consumer identified today) |
| C8 | Scheduled-terminal existence | 7 (Existence) | new `ExistencePattern` member | Candidate — **highest reuse value of any candidate** | BOND today; constitution §9 independently names it for Option and Future (via the mandatory-underlying/expiry pattern) and "Derivatives in general" |
| C9 | Staking reward flow | 5 (Flows) | new `FlowType` member | Candidate — **deliberately deferred**, per constitution's own "argued when a real position demands them" | CRYPTO, only if/when a real staking position is modeled |
| C10 | 24/7 / continuous settlement fit | 3 (Settlement) | none yet — open question whether `INSTANT` already covers it | Scope question, not a vocabulary candidate | CRYPTO only |
| C11 | Physical-vs-derivative exposure model | — | none — resolves to either C2+C3+C4 or full reuse of ETF's existing shape | Scope question, not a vocabulary candidate | COMMODITY only |

**Reading this table against the brief's own example list** ("periodic reference valuation, appraisal valuation, maturity lifecycle, coupon income, custody model, redemption semantics, physical settlement"): five of those seven examples map directly onto C1/C2/C8/C6/C4 above; "custody model" and "redemption semantics" did not surface as independently necessary during this analysis — custody is an instance/classification fact under existing axis boundaries (§5.3 of the constitution already rules worth/custody-adjacent facts out of the definition layer), and redemption is folded into C8's existence pattern plus the open event-family question noted in §3.2, rather than needing its own concept. This is recorded so the brief's illustrative list is not silently treated as a requirements list — two of its seven examples were checked and found to already be covered by other axes, not missed.

---

## 6. Vocabulary Candidate List

Every candidate above, restated as the literal governed-extension unit (`asset_definitions.md` §8.1 Step 2 requires one entry each: behavioral difference, owning engine, anti-explosion check).

| Candidate word | Enum | Behavioral difference argued | Anti-explosion check (§7.2) |
|---|---|---|---|
| NAV-window acquisition (C5) | `AcquisitionSemantics` | Registration/mint-time acquisition mechanism differs from venue order-book matching; no proper noun (no "mutual fund," no jurisdiction) | Passes — names a mechanism, not a wrapper |
| Coupon (C6) | `FlowType` | Ledger admits a distinct, contractually-scheduled fixed flow the way `DIVIDEND` is distinct from `INTEREST` today | Passes — already named in `GLOSSARY.md`'s illustrative Flow Type list (§7 below) |
| Scheduled-terminal existence (C8) | `ExistencePattern` | Lifecycle reachable-states set differs (a maturity/expiry date is a known terminal state, unlike `OPEN_ENDED`'s indefinite horizon) | Passes — no proper noun, names a pattern |
| Appraisal valuation (C2) | `ValuationQuestion` | Market Intelligence answers "worth" via a periodic professional appraisal-on-event, a third distinct cadence/question-shape from continuous quotation and periodic NAV | Passes |
| Negotiated acquisition (C3) | `AcquisitionSemantics` | Acquisition happens by private, bilateral negotiation, not a venue or a NAV window — a third distinct mechanism | Passes |
| Manual/negotiated settlement (C4) | `SettlementPattern` | Settlement timing and mechanism is bilaterally agreed per-transaction, not cycle- or instant-based | Passes |
| Rent (C7) | `FlowType` | Ledger admits a distinct holding-generated flow from occupancy/use, unlike interest or dividend character | Passes — already named in `GLOSSARY.md`'s illustrative list |
| Staking (C9) | `FlowType` | Deferred — argued in the constitution's own prose, and in `vocabulary.py`'s module docstring, but never actually added; **do not add speculatively** (§3.4) | N/A until a real position exists |

`GLOSSARY.md`'s existing "Flow Type" entry already lists `Coupon`, `Rent`, `Staking`, and `Distribution` as illustrative words in its definition prose (written when the glossary entry itself was authored, ahead of any of them being governed), and its "Event Family" entry already lists `Redemption`, `Expiry`, `Exercise` the same way. These are **not** governed vocabulary members — they are the glossary's own forward-looking illustration of the axis's *shape*, the same way this document's candidates are illustrations, not admissions. A future Step 2 extension for any of C2–C9 should still run the full gate (owning engine identified, test corpus, DECISION_LOG entry) even though the word already appears in prose; prior mention in illustrative text is not governance.

---

## 7. Dependency Graph Between Concepts

```
C1 (Periodic NAV valuation)         — SHIPPED (M17), unlocked ETF; also unlocks:
  └── C5 (NAV-window acquisition) ──── FUND authorable once C5 ships (C1 already available)

C6 (Coupon flow)         ──┐
                            ├── BOND authorable once both ship (order-independent)
C8 (Scheduled-terminal)  ──┘
        │
        └── reusable, independent of BOND, by any future maturity-shaped kind
            (Option, Future, "Derivatives in general" per constitution §9)

C2 (Appraisal valuation) ──┐
C3 (Negotiated acq.)      ─┼── PROPERTY authorable once all three ship (order-independent
C4 (Manual settlement)    ─┘    among themselves; naturally reviewed as one cluster)
        │
        └── reusable, without any new word, by:
              • future Business/private-ownership kind (constitution §9's own next walk)
              • physical-exposure COMMODITY, IF that scope branch is chosen

C10 (Crypto settlement fit) ── scope decision, blocks CRYPTO authoring; produces at most
                                one new SettlementPattern word, or confirms INSTANT
                                already suffices — decided independently of C1–C9

C11 (Commodity exposure model) ── scope decision, blocks COMMODITY authoring; resolves to
                                    zero new words either way:
                                      "derivative" branch → reuses ETF's shape as-is, today
                                      "physical" branch   → reuses C2+C3+C4, once shipped
```

No candidate concept depends on another candidate concept's vocabulary member to be *expressible* — every one of C2–C9 is independently addable. The graph's only real dependencies are **consumption** dependencies (a binding needs a cluster of words before it is authorable), not **word-on-word** dependencies (no candidate's definition references another candidate's enum). This matters for sequencing risk: shipping C8 alone (for Bond) never obligates shipping C6, and vice versa — each Step 2 extension in §8's roadmap can genuinely stand alone if a future milestone needs to reorder.

---

## 8. Recommended Expansion Order

1. **FUND — ship C5 (NAV-window acquisition) alone.** Smallest possible next step: one word, already-anticipated axis, and the only binding whose blocking gap collapsed (part of it, C1) two milestones ago without anyone noticing. Shipping this first is also the cheapest possible validation of this whole document's central thesis — that a word shipped for one binding's need (M17's `PERIODIC_NAV`, minted for ETF) really does serve a second binding later, exactly the way "reuse before create" (`ENGINEERING_PRINCIPLES.md`) predicts it should. Lowest governance risk: single word, single axis, no open sub-questions.

2. **BOND — ship C6 + C8 together.** Two words, both explicitly named by the constitution's own §9 walk (no new domain judgment required to justify either), and C8 (`SCHEDULED_TERMINAL`) is the single highest-reuse word identified anywhere in this analysis — every future maturity/expiry-shaped kind (Option, Future, and the constitution's own "Derivatives in general" pattern) draws on it. Shipping it now front-loads that reuse rather than re-deriving it whenever the first derivative milestone eventually arrives. The one open sub-question (§3.2's redemption/call event family) is explicitly left for that milestone's own D1/individuation review, not resolved here, per this document's analysis-only charter.

3. **PROPERTY — ship C2 + C3 + C4 together, as its own dedicated milestone.** The largest single vocabulary commitment among the three `VOCABULARY_GAP` bindings (four words counting Axis 5's `RENT`, three of which are this cluster). Deliberately sequenced *after* FUND and BOND so governance review benefits from two prior, successful, smaller Step 2 extensions' precedent before taking on the biggest one. The payoff is disproportionate to its cost: this cluster, once shipped, closes Property *and* pre-clears the physical-exposure branch of Commodity's scope decision *and* the future Business/private-ownership walk the constitution already anticipates — three future bindings' worth of reuse from one extension event.

4. **COMMODITY — scope decision, not an engineering milestone.** Recommended *after* step 3 ships, specifically so the decision-makers can compare the physical branch (now a real, shipped vocabulary cluster, not a hypothetical) against the derivative branch (ETF's already-shipped, already-proven shape) and choose by concrete example rather than in the abstract. Whichever way it resolves, zero new vocabulary is required — this step is pure product/domain judgment, appropriately sequenced last among the vocabulary-bearing work so it has the most evidence available when made.

5. **CRYPTO — domain-review scope decision on Axis 3 fit.** Recommended last: it is the one binding whose primary blocker (C10) has no reuse value for any other binding today, so shipping it earlier buys nothing for the rest of the roadmap the way BOND's `SCHEDULED_TERMINAL` or PROPERTY's cluster do. `STAKING` (C9) stays explicitly deferred regardless of when the settlement question resolves, per the constitution's own "not before a real need" instruction — it should not be bundled into whatever milestone resolves C10 unless a real staking position exists by then.

**Why this order, restated against the brief's three optimization criteria:**

- **Maximum reuse:** FUND first proves C1's reuse immediately; BOND's C8 seeds the largest number of future consumers of any single word; PROPERTY's cluster seeds two future bindings (Business, physical Commodity) at once. Ordered by proven-or-provable reuse value, descending.
- **Minimum vocabulary churn:** 1 word → 2 words → 4 words is an ascending-size progression — each Step 2 extension stays small and independently reviewable rather than bundling all nine remaining candidate words into one large, harder-to-audit change.
- **Minimum governance risk:** the two bindings whose gaps are purely engineering (FUND, BOND, PROPERTY — every word is already named or strongly implied by the constitution's own §9 prose) precede the two bindings whose gaps are product/domain judgment calls the engineering team cannot make unilaterally (COMMODITY, CRYPTO) — sequencing technical, low-ambiguity work ahead of decisions that need a human product owner's sign-off keeps each milestone's blast radius and required approvals as small as that milestone's own step actually needs.

---

## 9. What This Document Deliberately Does Not Do

Per the brief's non-goals: no word above has been added to `vocabulary.py`; no `AssetType` has been added to `asset_domain.py`; no canonical definition document has been drafted; `readiness_report.py`, `enforcement_decisions.py`, `library.py`, `registry.py`, and every pinned fingerprint are byte-identical to their M19 state. The corrections identified in §1 (FUND's stale readiness rationale, Bond's readiness-vs-constitution mismatch, the unshipped "reserved" staking word) are recorded here and in `DECISION_LOG.md`'s M20 entry precisely so a future milestone inherits them as known findings rather than rediscovering each one from scratch — but fixing them is out of this milestone's scope, exactly the way M19's own guide instructs future authors to treat a stale artifact they discover but were not asked to repair.

---

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution; §9's worked examples are this document's starting hypothesis, checked here against real code
- [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the eight-stage process each future binding walks once its gap closes
- [definition_review_checklist.md](definition_review_checklist.md) — item 1 ("Vocabulary complete?") is this document's method, applied per-definition instead of platform-wide
- [asset_definition_library.md](asset_definition_library.md) — the library itself; §2's table is the same "span the axes" exercise this document repeats for the five remaining bindings
- [../../backend/services/asset_definitions/readiness_report.py](../../backend/services/asset_definitions/readiness_report.py) — the hand-authored table this document cross-checks and finds one stale row in (FUND)
- [../../backend/services/asset_definitions/enforcement_decisions.py](../../backend/services/asset_definitions/enforcement_decisions.py) — the hand-authored table this document cross-checks and finds one imprecise row in (BOND)
- [../GLOSSARY.md](../GLOSSARY.md) — source of the illustrative (not governed) word lists cross-referenced in §6
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — where this milestone's findings and every future vocabulary extension are recorded
