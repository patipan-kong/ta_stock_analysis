# The Asset Definition Library

_The canonical library of Asset Definitions — the official, versioned registry of every kind of asset the platform can describe. Chartered by [asset_definitions.md](../architecture/asset_definitions.md) §4 ("the library"); every document in this directory is a governed artifact under that constitution's laws D1–D12._

| | |
|---|---|
| **Library version** | v1 |
| **Definitions** | 4 — [Cash](asset_definition_cash.md) v1 · [Equity](asset_definition_equity.md) v1 · [ETF](asset_definition_etf.md) v1 · [Fund](asset_definition_fund.md) v1 |
| **Vocabulary status** | Frozen — the seven axes and their words, per the ratified constitution (extended twice: M17 `ValuationQuestion.PERIODIC_NAV`, M21 `AcquisitionSemantics.NAV_WINDOW`) |

---

## 1. What this library is

Each document in this directory is one **definition**: the complete behavior contract of one kind of asset, written as declarations along the seven constitutional axes ([asset_definitions.md](../architecture/asset_definitions.md) §5.1) and nothing else. These are not examples, templates, or documentation *about* definitions — they are the definitions: the reviewable text that *is* what each kind of asset is, on this platform (constitution §2.4). The capability projection each document ends with is the truth engines consume; the prose around it is the reasoning governance reviews.

The library's own obligations, inherited as law:

- **No two definitions with identical declarations** (D1). Admission to this library requires demonstrating a declaration no existing definition makes.
- **Published versions are immutable** (D8). A definition document, once canonical, is amended only by publishing a successor version; recorded facts replay under the version that admitted them.
- **Declarations only** (D2, D11, D12). No formula, no judgment, no metadata, no classification ever appears in a definition — each document's Validation section attests to this, and review holds it.

---

## 2. Why these two definitions validate the architecture

Cash and Equity were chosen deliberately, and deliberately *unglamorously* ([asset_foundation.md](../architecture/asset_foundation.md) §8): the founding pair proves the mechanism, not the menu. Three arguments, in increasing order of importance:

**They are already true.** Cash and equity are the two kinds the platform has run in production for its entire life. Every declaration in both documents is behavior the engines already exhibit and the test corpus already encodes — which means the pair validates the *contract* at zero new accounting risk. What M8 changes is not behavior but **authority**: facts that lived as implicit assumptions inside engine code become declared, queryable, reviewable text. If either document had required an engine change, the constitution — not the engine — would have been wrong, and the failure would have surfaced on the cheapest possible classes.

**They span the axes.** Between them, the pair exercises both poles of every axis — each axis proven in a presence form and an absence form:

| Axis | Cash declares | Equity declares |
|---|---|---|
| Unit | continuous, quantity ≡ value | discrete share, instance-refined divisibility |
| Acquisition | not transactable | venue-traded |
| Settlement | instant | cycle-based |
| Valuation | identity — no question exists | continuous quotation |
| Flows | interest | dividend |
| Event families | none | the full listed-share surface |
| Existence | open-ended, no relationships | open-ended, three permitted relationship kinds |

No axis is idle, and no axis is exercised only positively. This matters because the constitution's hardest claim is that **absence is a declaration** (D7): a vocabulary is only proven expressive when the empty grant is as load-bearing as the full one — when "cash grants no event families" and "cash is not transactable" do real work (refusing misbooked flows, catching misclassified imports) rather than marking gaps.

**Together they close the conservation loop.** Cash is the numeraire: every equity BUY, SELL, DIVIDEND, and FEE has a cash counterleg. Two definitions are therefore the *minimum* set that exercises a complete double-sided transaction under declared — rather than assumed — semantics. One definition could describe a kind; only a pair can describe an economy. Every future kind joins this same loop through the same counterleg, which is why proving the loop once proves the pattern.

What the pair deliberately does **not** validate — recorded so nobody mistakes silence for coverage: NAV-window acquisition, appraisal valuation, scheduled-terminal existence, mandatory relationship participation, and every flow beyond interest and dividend. Those declarations are proven when the first kind that needs them arrives (bond, fund, option — the walks sketched in the constitution's §9), each by the same three-step ladder, each without touching this pair.

---

## 3. How future definitions are authored

The process is the constitution's evolution ladder (§8.1), operationalized. An author proposing a new definition follows these steps in order, and the review checklist at the end is mandatory.

_As of M19, this section's steps are also available as an eight-stage, tool-by-tool walkthrough — [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — with ETF v1's actual authoring run (M15–M18) worked through each stage, plus a formal pass/fail form, [definition_review_checklist.md](definition_review_checklist.md), to attach to the PR that admits a new definition. This section remains the conceptual statement; the guide is the operational one._

### 3.1 Before writing: two gates

1. **The individuation gate (D1).** State the declaration the new kind makes that no existing definition makes — axis and value, precisely. If none exists, there is no new definition: the "new class" is an existing kind plus classification (the fate of preferred shares and DRs inside Equity v1). This gate is checked *first* because it is the cheapest and the most often failed.
2. **The vocabulary gate (D3).** Every intended declaration must be an existing word on an existing axis. A missing word is not a blocker to route around — it is a governed extension (constitution §8.1 Step 2: behavioral difference stated, owning engine identified, implemented once, glossary-registered, DECISION_LOG-recorded) completed *before* the definition that needs it is admitted. A missing *axis* is a constitutional amendment, and stop.

### 3.2 The document

Every definition document carries the same nine parts, in order — the shape the founding pair establishes:

1. **Header block** — definition name, version, status, individuation statement.
2. **Purpose** — what the kind is, what it deliberately does not distinguish (the D1 reasoning), and what neighboring thing is *not* this kind.
3. **Axes 1–7** — one section per axis, every declaration stated in bold and then **explained**: why this value, what was challenged, what was rejected and where the rejected fact lives instead. An unexplained declaration is an unreviewed one; absences are explained with the same care as presences, because absences are declarations (D7).
4. **Capability Projection** — the complete table of what engines can learn. If a truth about the kind is not derivable from this table, it is not a definitional truth — move it or delete it.
5. **Validation** — the five attestations, each argued, not asserted: no engine change required; constitutional vocabulary only; no metadata; no classification; no implementation logic.

### 3.3 Style laws for authors

- **Challenge in the text.** The founding pair records its rejected alternatives (should cash be continuously valued? should equity grant interest?) *inside* the document. This is deliberate and binding: the next author must be able to see that a question was weighed, not missed — a definition's silences must be legible as decisions.
- **No proper nouns** (§7.2 of the constitution). The moment a draft needs a country, venue, vendor, or wrapper name to state a declaration, the fact under the pen is classification or an instance fact, not a declaration.
- **No speculative grants.** Grant what the kind can undergo *and an instance could face*; defer what is merely conceivable (Cash v1's redenomination reasoning is the precedent). Widening later is additive and cheap; retracting a grant engines began honoring is the sharp case (§8.2).
- **Name the version's scope.** Where a known future question is deliberately out of scope (FX for single-currency Cash v1, shorting for Equity v1), say so in place, so the future widening starts from a recorded question rather than an archaeology.

### 3.4 Versioning in the library

Per constitution §8.2, applied to these files: a canonical definition document is never edited in meaning. A new version is a new canonical state — published whole, with its predecessor retained and marked superseded, its delta recorded in [DECISION_LOG.md](../engineering/DECISION_LOG.md), and the recorded past forever governed by the version that admitted it (D8). Wording clarifications that change no declaration are ordinary maintenance; when in doubt, it is a version.

---

## 4. Conformance

Any implementation of the definition mechanism — enums, dataclasses, storage, the projection surface — is a level-6 realization of this library (constitution §11, rule G6): the library states what each kind *is*; code states how the platform currently spells it. Where an implementation and this library disagree on a declaration, the library states the intent and the implementation conforms — never the reverse, and never by drift. The M5 Track B technical design's v1 sketch ([M5_TRACK_B_NATIVE_INTEGRATION_TDD.md](../implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md) §8) predates this library; its equity and cash contents are superseded by the two canonical documents here, per the constitution's own conformance ruling (asset_definitions.md §11).

## Related Documents

- [asset_definitions.md](../architecture/asset_definitions.md) — the constitution: the seven axes, laws D1–D12, the evolution ladder
- [asset_definition_cash.md](asset_definition_cash.md) — Cash v1
- [asset_definition_equity.md](asset_definition_equity.md) — Equity v1
- [asset_definition_etf.md](asset_definition_etf.md) — ETF v1, the first definition admitted after the founding pair (M18); differs from Equity v1 by exactly one axis (periodic NAV valuation, M17's vocabulary extension)
- [asset_definition_fund.md](asset_definition_fund.md) — Fund v1, the second definition admitted after the founding pair (M22); differs from ETF v1 by exactly one axis (NAV-window acquisition, M21's vocabulary extension)
- [asset_definition_authoring_guide.md](asset_definition_authoring_guide.md) — the governed authoring workflow (M19), §3 above operationalized stage by stage
- [definition_review_checklist.md](definition_review_checklist.md) — the same workflow as a formal pass/fail checklist (M19)
- [asset_foundation.md](../architecture/asset_foundation.md) — the parent domain constitution; §8 states why the founding pair is deliberately two
- [../engineering/DECISION_LOG.md](../engineering/DECISION_LOG.md) — where every future vocabulary extension and definition version is recorded
