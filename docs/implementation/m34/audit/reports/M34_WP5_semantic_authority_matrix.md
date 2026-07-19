# M34-WP5 - Semantic Authority Matrix

**Date:** 2026-07-19

**Status:** Complete as an authority-evidence audit. No calculation was
evaluated, no owner was appointed, and no design, implementation, finding,
disposition, or runtime change was created.

**Recommendation:** **Semantic authority is not sufficiently established for
M34-WP6. Return the ownership namespace and unresolved primary claims to the
Architecture Review Board.** The platform constitution supplies a coherent
one-owner model, but the frozen WP1 audit owner names do not map explicitly to
that model, most product terms are absent from the canonical Glossary, and
several observable claims remain conflicted, stopped, or without an owner.

## 1. Boundary and method

WP5 consumes the frozen WP2 product evidence, WP3 surface/output inventory,
and WP4 read-contract lineage. It does not change their surface, claim,
contract, source, or candidate-owner classifications. The audited repository
revision is `531b01b17a34955a65dd45f5e9386763652938ab`.

The unit of analysis is one semantic claim family. Forty claim families cover
every visible output listed in WP3 without treating every field or card as a
new concept. A family is split when two source domains can own different
meanings; it remains grouped when several surfaces display the same concept.

Authority was evaluated in this order:

1. the ratified Platform Architecture and canonical Glossary;
2. domain constitutions and frozen accounting semantics;
3. ADRs and closed M32/M33 decisions;
4. technical/domain designs and approved UX contracts;
5. current implementation documentation; and
6. source and transport evidence from WP3/WP4.

This is the hierarchy in `platform_architecture.md` section 11. Running code,
route placement, a database table, a service name, or a TypeScript type can
show where a claim exists but cannot appoint its semantic owner.

Authority results use these values:

| Result | Meaning |
| --- | --- |
| `ALIGNED` | One constitutional owner is explicit and competing domains are only declared inputs or scopes. |
| `PROVISIONAL_MAPPING` | The constitutional owner is explicit, but the frozen WP1 audit-domain name has no approved mapping to it. |
| `CONFLICTED` | Two authority sources, scopes, or observable meanings compete and WP5 cannot select one. |
| `STOPPED_AUTHORITY` | A visible legacy claim exists, but M32/M33 explicitly deny the authority the unqualified term could imply. |
| `UNKNOWN_OWNERSHIP` | No existing authority establishes one owner for the material concept. |

Confidence measures confidence in the authority assessment, not confidence in
the displayed value. `HIGH` conflict confidence means the conflict is well
evidenced; it does not mean either candidate wins.

Evidence: `M34-E-0039` through `M34-E-0050`.

## 2. Governing authority and namespace result

The Platform Architecture is Constitution v1.1. It states that every concept
has exactly one domain home and defines these relevant owners:

| Constitutional owner | Exclusive semantic responsibility relevant to WP5 |
| --- | --- |
| Asset Foundation | asset identity and classification |
| Market Intelligence | canonical prices, histories, calendars, rates, regimes, and observation provenance |
| Ledger & Accounting | financial truth, ledger events, holdings/cash/cost derivation, and accounting inputs |
| Portfolio Intelligence | valuation, performance, benchmark, attribution, risk, exposure, and other derived-measure semantics |
| Decision Intelligence | beliefs, recommendations, plans, decision records, and policy envelope |
| Trust & Evaluation | grades, calibration, counterfactual tracks, and trust vocabulary |
| Wealth Intelligence | cross-portfolio and life-level goals, net worth, exposure, plans, and obligations |
| Experience Platform | rendering, interaction vocabulary, navigation, and operational shell; truth of nothing |

The frozen WP1 owner model instead uses `PORTFOLIO`, `ANALYTICS`,
`MARKET_DATA`, `LEDGER`, `PORTFOLIO_INTELLIGENCE`, `AI_EVALUATION`, and
`EXPERIENCE`. Several are obvious corpus categories, but WP1 also uses them as
owner rules. No frozen artifact explicitly approves this semantic mapping:

| WP1 audit owner name | Evidenced constitutional candidate | WP5 result |
| --- | --- | --- |
| `LEDGER` | Ledger & Accounting | clear lexical mapping; no conflict observed |
| `MARKET_DATA` | Market Intelligence | clear for prices/source state; Market Intelligence also owns regimes and broader observations |
| `ANALYTICS` | Portfolio Intelligence | responsibility aligns, domain name does not |
| `PORTFOLIO_INTELLIGENCE` | Decision Intelligence for recommendations/investigations; Portfolio Intelligence for derived measures | materially ambiguous |
| `AI_EVALUATION` | Trust & Evaluation | responsibility aligns, domain name does not |
| `PORTFOLIO` | portfolio scope model; underlying truth divides among Ledger & Accounting, Portfolio Intelligence, Decision Intelligence, and Wealth Intelligence | no single constitutional-domain mapping |
| `EXPERIENCE` | Experience Platform | aligned |

WP5 preserves both vocabularies. It does not reinterpret WP1 or amend the
constitution. Under WP1 stop conditions 1, 5, and 11, the material owner-name
conflict must return to the Architecture Review Board before dependent
semantic verification proceeds.

Evidence: `M34-E-0039`, `M34-E-0040`, `M34-E-0047`.

## 3. Semantic Authority Matrix

“Canonical definition source” follows Constitution v1.1 section 12: the
Glossary is the only canonical vocabulary. When an exact term is absent, the
table names the highest governing rule that constrains it and records the
Glossary gap rather than silently promoting another document.

### 3.1 Portfolio, ledger, and market-observation claims

| ID | Semantic concept and observable claim | Surfaces | WP1 candidate | Constitutional candidate | Supporting / competing authority | Canonical definition source | Result / confidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SA01` | Portfolio identity and selected portfolio: id, name, goal target, current selection | all portfolio-scoped routes | Portfolio | `UNKNOWN` at platform-domain level; Portfolio domain model owns scope | Ledger & Accounting owns truth; Decision/Wealth own some strategy/goal meanings; Experience owns selection only | No `Portfolio` Glossary entry; `PORTFOLIO_DOMAIN_MODEL.md` sections 1-3 is the governing design | `CONFLICTED` / `HIGH` | Constitutional home for portfolio identity and strategy container |
| `SA02` | Cross-portfolio combined symbol exposure and portfolio membership | `/` | Portfolio + Market Data | Wealth Intelligence for overall exposure | Portfolio domain model says cross-boundary exposure is Wealth; current route is a Portfolio-group entry and WP4 composes Portfolio/Market inputs | No exact Glossary entry; `PORTFOLIO_DOMAIN_MODEL.md` sections 7 and 10 | `CONFLICTED` / `HIGH` | Whether the current heatmap is a Wealth projection or a portfolio-list convenience |
| `SA03` | Holdings and quantities: current positions and shares | `/`, `/portfolio` | Portfolio + Ledger | Ledger & Accounting | Portfolio is authoritative scope; holdings are derived by ledger replay, never an editable independent truth | No `Holding` Glossary entry; `TRANSACTION_DOMAIN_MODEL.md` sections 1-5 and Portfolio model section 2 govern | `ALIGNED` / `HIGH` | Exact current-read conformance belongs to WP6, not WP5 |
| `SA04` | Cash balance and cash utilization | `/portfolio`, `/analytics` | Portfolio + Ledger / Analytics | Ledger & Accounting for cash; Portfolio Intelligence for utilization interpretation | Portfolio boundary scopes cash; analytics may interpret deployment without redefining balance | No exact Glossary entry; Portfolio calculation rules and Platform Architecture sections 6.3/6.5 | `ALIGNED` / `HIGH` | “Cash utilization” has no canonical Glossary definition |
| `SA05` | Transaction and ledger event history: buys, sells, deposits, withdrawals, dividends, corrections | `/portfolio`, evaluation detail consumers | Ledger | Ledger & Accounting | Transaction domain explicitly owns immutable economic facts and canonical event vocabulary | `GLOSSARY.md::Ledger` and `Canonical Ledger Event`; `TRANSACTION_DOMAIN_MODEL.md` | `ALIGNED` / `HIGH` | None at owner level |
| `SA06` | Cost basis, realized P/L, fees, and taxes | `/portfolio`, `/performance`, evaluation detail | Ledger + Portfolio | Ledger & Accounting | Portfolio calculation rules are the domain constitution for accounting semantics; Portfolio supplies scope | No exact Glossary entries; `PORTFOLIO_CALCULATION_RULES.md` sections 5 and 8 | `ALIGNED` / `HIGH` | None at owner level; formulas are intentionally unevaluated |
| `SA07` | Latest/current price, previous price, price change, chart observations | `/`, `/portfolio`, `/stock/[symbol]`, `/watchlist` | Market Data | Market Intelligence | Market Data Platform owns latest/historical observations, moment, currency, kind, provenance, and explicit freshness | No `Price` Glossary entry; `MARKET_DATA_PLATFORM.md` sections 2 and 7 | `ALIGNED` / `HIGH` | Runtime provider/cache branch remains WP4 unknown `L02` |
| `SA08` | Portfolio equity value and total value/NAV | `/`, `/portfolio`, `/performance` | Portfolio | Portfolio Intelligence | Ledger supplies holdings/cash; Market Intelligence supplies observations; Portfolio Intelligence owns valuation as derived knowledge | No portfolio-NAV Glossary entry; Portfolio domain section 2 and calculation rules section 9 | `PROVISIONAL_MAPPING` / `HIGH` | WP1 `PORTFOLIO` to constitutional Portfolio Intelligence mapping |
| `SA09` | Unrealized P/L | `/portfolio`, `/performance` | Portfolio / Analytics | Portfolio Intelligence | Derived measure depends on Ledger cost/quantity facts and Market Intelligence prices | No exact Glossary entry; Portfolio domain section 2 and current architecture accounting contract | `PROVISIONAL_MAPPING` / `MEDIUM` | Exact period/current distinction requires WP6 |
| `SA10` | Allocation weights, sector allocation, and concentration | `/portfolio`, `/analytics`, factors, three-portfolio views | Portfolio / Analytics | Portfolio Intelligence | Asset Foundation supplies identity/classification; Portfolio Intelligence owns exposure/risk derivation | No exact Glossary entries; Platform Architecture sections 6.1 and 6.5 | `PROVISIONAL_MAPPING` / `HIGH` | Whether every “allocation” refers to current, target, ideal, AI, or actual weights |
| `SA11` | Sector classification attached to holdings/watchlist | `/portfolio`, `/watchlist`, factor/attribution views | Market Data / Portfolio | Asset Foundation for canonical classification; Market Intelligence supplies metadata evidence | Market Data Platform calls sector candidate metadata for Registry stewardship; current read lineage stores sector on Portfolio/Watchlist rows | No exact Glossary entry; Platform Architecture section 6.1 and Market Data section 2 | `CONFLICTED` / `HIGH` | Which current sector value is canonical and which is cached evidence |
| `SA12` | Portfolio return and investment performance | `/performance`, `/analytics`, intelligence/evaluation consumers | Analytics | Portfolio Intelligence | Ledger/accounting constitution owns inputs/formula; Portfolio Intelligence owns performance meaning and presentation-ready derived measure | No `Return`/`Performance` Glossary entry; `PORTFOLIO_CALCULATION_RULES.md` and Platform Architecture section 6.5 | `PROVISIONAL_MAPPING` / `HIGH` | Audit-domain mapping; calculations not evaluated |
| `SA13` | Benchmark comparison, alpha, and indexed/equity curves | `/performance`, `/analytics`, `/ai-analytics/portfolios` | Analytics | Portfolio Intelligence | Portfolio strategy declares benchmark; Market Intelligence owns benchmark observations | No exact Glossary entries; Portfolio domain sections 6 and 10, Market Data section 2 | `PROVISIONAL_MAPPING` / `HIGH` | Curve base/index/period equivalence across surfaces |
| `SA14` | External flows, imported/manual adjustments, dividends, fees, and non-performance-event breakdowns | `/performance`, `/analytics` | Ledger + Analytics | Ledger & Accounting for events; Portfolio Intelligence for derived decomposition | Calculation constitution explicitly separates event truth from performance interpretation | No exact Glossary entries; Transaction model section 3 and Calculation Rules sections 4-8 | `ALIGNED` / `HIGH` | Surface vocabulary may omit the event/decomposition distinction |
| `SA15` | Portfolio drawdown, volatility, concentration, and policy-risk measures | `/analytics`, factors, intelligence/evaluation | Analytics | Portfolio Intelligence | Portfolio domain makes risk portfolio-scoped; Platform Architecture assigns risk/exposure semantics to Portfolio Intelligence | No exact Glossary entries; Portfolio domain sections 2 and 10 | `PROVISIONAL_MAPPING` / `MEDIUM` | Exact windows, bases, and distinction from instrument/AI risk |
| `SA16` | Freshness, “Updated”, analysis time, and batch “as of” | portfolio, stock, watchlist, operations, all evaluation pages | Market Data / source domains; Experience renders | Market Intelligence for observation age; each producing domain for batch/calculation time | Market Data defines price freshness; Evaluation UX defines batch AsOfStamp; WP3 records client refresh and analysis timestamps as separate visible claims | No `Freshness`, `Updated`, or `As Of` Glossary entry | `CONFLICTED` / `HIGH` | Which timestamp each label displays and which degraded state it implies |
| `SA17` | Portfolio snapshot and snapshot history | `/performance`; downstream analytics/evaluation | Portfolio / Analytics | Ledger & Accounting for derived historical state; Portfolio Intelligence consumes it | Transaction constitution says snapshots are derived and non-authoritative; Portfolio Snapshot is shared read material | `GLOSSARY.md::Portfolio Snapshot` | `ALIGNED` / `HIGH` | Immutable-record wording versus rebuildable-derivation wording needs later reconciliation, not a WP5 choice |

### 3.2 Analytical and instrument-investigation claims

| ID | Semantic concept and observable claim | Surfaces | WP1 candidate | Constitutional candidate | Supporting / competing authority | Canonical definition source | Result / confidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SA18` | Monthly returns and quantitative performance statistics | `/analytics` | Analytics | Portfolio Intelligence | Platform Architecture owns derived measures; calculation constitution governs base return only | No exact Glossary entry; current `ARCHITECTURE.md` is implementation documentation | `PROVISIONAL_MAPPING` / `MEDIUM` | Compounding, window, annualization, and statistic-specific definitions |
| `SA19` | Factor exposure, Portfolio DNA, style drift, and per-stock factor scores | `/portfolio/[id]/factors`, `/analytics` | Analytics / Portfolio Intelligence | Portfolio Intelligence | `ARCHITECTURE.md` defines current DNA/drift mechanics; platform constitution owns factor/risk knowledge | No matching Glossary entries | `PROVISIONAL_MAPPING` / `HIGH` | Whether “Portfolio DNA” and institutional factor exposure are one concept or related projections |
| `SA20` | Technical, fundamental, news, and signal analysis | `/stock/[symbol]`, `/portfolio`, `/analytics`, `/watchlist` | Portfolio Intelligence / Market Data | Decision Intelligence for beliefs; Market Intelligence for observations | Scorer/signal vocabulary is implementation-documented; facts and judgments must remain separate | No matching Glossary entries | `PROVISIONAL_MAPPING` / `MEDIUM` | Boundary between observed inputs, deterministic score, AI belief, and recommendation |
| `SA21` | Instrument upside, risk score, consensus, history, and source claims | `/stock/[symbol]`, `/watchlist` | unresolved stock/AI-analysis owner | `UNKNOWN` as one grouped product concept | Market Intelligence owns facts/provenance; Decision Intelligence owns belief/consensus; Portfolio Intelligence owns portfolio risk, not instrument-AI risk | No matching Glossary entries; current architecture documents fields only | `UNKNOWN_OWNERSHIP` / `HIGH` | Whether these are separate concepts requiring separate owners and vocabulary |
| `SA22` | Contribution and contributor rankings: sector contribution, position P/L, top contributors | `/analytics`, performance/intelligence/evaluation views | Analytics | Portfolio Intelligence | Portfolio Intelligence constitution owns contribution/attribution; current product uses several labels without a single registered meaning | No `Contribution`, `Sector Contribution`, or `Top Contributors` Glossary entries | `PROVISIONAL_MAPPING` / `HIGH` | Period, baseline, return-vs-P/L meaning, and whether ranking is attribution |
| `SA23` | Return attribution, effect waterfall, residual/unexplained amount | `/ai-analytics/attribution`, `/portfolio-intelligence`, `/optimizer` | Analytics / AI Evaluation presentation | Portfolio Intelligence for attribution; Trust & Evaluation may explain evaluated consequences | Portfolio domain makes attribution strategy-scoped; Evaluation UX specifies presentation and approximations but cannot become source truth | No `Attribution` Glossary entry; Portfolio domain section 10 and evaluation design are governing sources | `PROVISIONAL_MAPPING` / `HIGH` | Exact vocabulary and source ownership of each effect |
| `SA24` | Market regime and regime attribution | operations, intelligence, optimizer, attribution | Analytics / Portfolio Intelligence | Market Intelligence owns regime observation; Portfolio Intelligence owns attribution of performance by regime | Current architecture defines regime states and a regime-attribution service | No matching Glossary entries | `ALIGNED` / `MEDIUM` | Whether displayed regime is observation, policy context, or attribution bucket |

### 3.3 Decision, evaluation, operations, and explanatory claims

| ID | Semantic concept and observable claim | Surfaces | WP1 candidate | Constitutional candidate | Supporting / competing authority | Canonical definition source | Result / confidence | Unknowns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SA25` | Portfolio goal profile, persona, policy, and portfolio/sector limits | `/goal-wizard`, `/optimizer`, `/operations-center`, `/settings` | Portfolio / Portfolio Intelligence / configuration | Decision Intelligence for policy; Wealth Intelligence for life-level goals; portfolio scope design for strategy metadata | Portfolio model calls goal strategy metadata; optimizer constitution owns policy envelope; settings expose system-level constraints | No matching Glossary entries | `CONFLICTED` / `HIGH` | Boundary among portfolio strategy, Wealth goal, policy envelope, and system setting |
| `SA26` | Immutable optimizer recommendation / belief record, ideal weights, consensus | `/optimizer`, recommendation ledger/report, intelligence | Portfolio Intelligence / AI Evaluation | Decision Intelligence | Optimizer constitution owns belief and recommendation; Glossary defines frozen Recommendation Snapshot independent of user decisions | `GLOSSARY.md::Recommendation Snapshot`; `OPTIMIZER_PHILOSOPHY.md` | `PROVISIONAL_MAPPING` / `HIGH` | WP1 `PORTFOLIO_INTELLIGENCE` mapping to Decision Intelligence |
| `SA27` | Displayed execution-plan projection and proposed trades | `/optimizer`, recommendation report | Portfolio Intelligence | Decision Intelligence conceptually; no canonical runtime plan is active | Optimizer constitution defines plan as recommendation object, but M32 closeout says canonical execution planning remains NO-GO and current response is legacy | No `Execution Plan` Glossary entry; M32 closeout controls runtime authority | `STOPPED_AUTHORITY` / `HIGH` | What non-authoritative product term may safely describe the current projection |
| `SA28` | Human decision status and legacy `UserExecutionDecision` record | optimizer/evaluation ledgers and details | Portfolio Intelligence / AI Evaluation | Decision Intelligence conceptually; no M33 approval authority | Evaluation UX defines statuses; M33 says legacy rows are not approval authority and prospective approval runtime is stopped | No `Human Decision` Glossary entry; M33.11 controls authority | `STOPPED_AUTHORITY` / `HIGH` | Whether the record is a label, response, intent, or authorized decision |
| `SA29` | Execution record/detail, plan-vs-actual trades, timing/size/funding/completeness | execution ledger/detail, report card | AI Evaluation + Ledger | Trust & Evaluation for evaluation; Ledger & Accounting for actual events; Decision Intelligence for plan | Evaluation design describes comparison; M32 denies canonical plan activation; M33 denies approval authority | `GLOSSARY.md::Implementation Shortfall` covers one measure only; no `Execution Record` entry | `CONFLICTED` / `HIGH` | Which actual events are linked and what “execution” is permitted to assert |
| `SA30` | Decision memory and decision timeline | `/portfolio-intelligence`, `/optimizer` | Portfolio Intelligence / AI Evaluation | Decision Intelligence owns decision records; Trust & Evaluation may analyze them | Optimizer constitution says Decision Memory consumes recorded objects; current route also presents evaluation outputs | No `Decision Memory` Glossary entry | `PROVISIONAL_MAPPING` / `MEDIUM` | Whether memory is immutable decision record, analytical projection, or both |
| `SA31` | Shadow, Ideal, AI, and Your portfolio trajectories; Gaps A/B | intelligence, scorecard, portfolio comparison, report cards | AI Evaluation / Analytics | Trust & Evaluation | Glossary and Evaluation UX explicitly define Shadow, Ideal, AI, Gap A, and Gap B; actual portfolio facts remain Ledger/Portfolio Intelligence inputs | `GLOSSARY.md::Shadow Portfolio`, `Ideal Portfolio`, `AI Portfolio`, `Gap A`, `Gap B` | `PROVISIONAL_MAPPING` / `HIGH` | “Your Portfolio” still relies on current actual-performance authority |
| `SA32` | Recommendation grades, belief/execution/outcome lenses, scorecard, maturity states | scorecard, recommendations, report cards | AI Evaluation | Trust & Evaluation | Optimizer constitution and Evaluation UX require three independent lenses; Glossary defines Recommendation Grade | `GLOSSARY.md::Recommendation Grade` | `PROVISIONAL_MAPPING` / `HIGH` | Exact metric terms inside each lens are not all registered |
| `SA33` | Human-vs-AI comparison, scoreboard, return delta, regret | intelligence and `/ai-analytics/human-vs-ai` | AI Evaluation / Analytics | Trust & Evaluation | Glossary Gap B and Evaluation UX define symmetric comparison; actual and AI series remain source-domain inputs | `GLOSSARY.md::Gap B`; no `Human vs AI` entry | `PROVISIONAL_MAPPING` / `HIGH` | Relationship between legacy “regret” and Gap B/opportunity-cost vocabulary |
| `SA34` | Opportunity cost and divergence/deferral ledger | `/ai-analytics/opportunity-cost` | AI Evaluation | Trust & Evaluation | Glossary and optimizer constitution define counterfactual difference, not realized profit | `GLOSSARY.md::Opportunity Cost` | `PROVISIONAL_MAPPING` / `HIGH` | Input authority inherits the legacy-decision limitation |
| `SA35` | Confidence calibration and calibration history | intelligence, optimizer, scorecard | AI Evaluation / Portfolio Intelligence | Trust & Evaluation | Optimizer constitution defines calibration as honesty of confidence against realized frequency | No `Confidence Calibration` Glossary entry | `PROVISIONAL_MAPPING` / `HIGH` | Whether current historical and scorecard fields share one calibration contract |
| `SA36` | Operations status, station health, committee status, translation/action-required state | `/operations-center`, `/optimizer` | Portfolio Intelligence plus source domains | `UNKNOWN` as one semantic concept | Composite reads use Portfolio, Market, Decision, and Trust inputs; no constitution grants the aggregator ownership of their combined truth | No matching Glossary entries or governing definition | `UNKNOWN_OWNERSHIP` / `HIGH` | Meaning, severity, source authority, and degraded-state owner of each status |
| `SA37` | Trust report and verdict sentences | Operations Center and scorecard | AI Evaluation | Trust & Evaluation | Evaluation UX bounds Trust Report as a short evidence summary; constitution says trust is accumulated from records and writes only its own outputs | No `Trust Report` Glossary entry | `PROVISIONAL_MAPPING` / `HIGH` | Whether “trust” is clearly scoped to evaluation rather than all portfolio correctness/freshness |
| `SA38` | Watchlist membership as user-maintained product state | `/watchlist` | Watchlist/analysis candidate | `UNKNOWN` | Experience renders it; Market Intelligence supplies observations; Decision Intelligence supplies analysis, but none owns membership vocabulary | No `Watchlist` Glossary entry or domain constitution | `UNKNOWN_OWNERSHIP` / `HIGH` | Whether membership is Experience preference, Decision input, or another existing domain concept |
| `SA39` | AI model, analysis-source, optimizer-layer/fallback, portfolio and sector configuration | `/settings`, `/stock/[symbol]` | configuration / Portfolio / Portfolio Intelligence | Each affected constitutional domain, not one common semantic owner | Engineering Principles require authoritative source per setting; a storage table or Settings page is not a business owner | No general configuration Glossary entry; current `ARCHITECTURE.md` documents storage/defaults | `CONFLICTED` / `HIGH` | Owner and policy level of every setting family |
| `SA40` | System Guide explanations of navigation and product concepts | `/system-guide` | Documentation + Experience | Experience Platform owns rendering; each source domain owns the described meaning | WP1 and constitution forbid Experience/documentation from becoming portfolio truth | No independent authority; must reference Glossary/domain sources | `ALIGNED` / `HIGH` | Whether every current explanation is synchronized is deferred to documentation verification |

Evidence: `M34-E-0023`, `M34-E-0038`, `M34-E-0039` through
`M34-E-0048`.

## 4. One Concept -> One Owner Verification

The constitutional model itself passes the structural one-owner test. The
observable claims can be partitioned without making Experience or an
aggregator authoritative:

```text
Asset Foundation
  identity and classification

Market Intelligence
  observation value + kind + moment + currency + provenance + availability

Ledger & Accounting
  event fact -> replay -> holdings/cash/cost/accounting state

Portfolio Intelligence
  valuation + performance + benchmark + risk + exposure + attribution

Decision Intelligence
  belief + recommendation + plan + policy + decision record

Trust & Evaluation
  grade + calibration + counterfactual + comparison + trust explanation

Wealth Intelligence
  cross-portfolio exposure + life-level goal/plan/net-worth meaning

Experience Platform
  navigation + label + formatting + interaction + rendering of supplied failure state
```

The current audit record does **not** pass the operational verification needed
for WP6:

- 9 claim families align directly with an existing constitutional owner;
- 19 have a clear constitutional candidate but an unapproved WP1 audit-name
  mapping;
- 7 contain cross-domain ownership conflicts;
- 2 are constrained by stopped M32/M33 authority;
- 3 have unknown ownership.

The counts total the 40 matrix rows. They classify authority only; they do not
classify defects or severity.

Evidence: `M34-E-0048`, `M34-E-0049`.

## 5. Ownership Conflict Inventory

| Conflict | Claim families | Competing candidates | Why WP5 cannot choose |
| --- | --- | --- | --- |
| Audit-domain namespace versus constitutional domains | `SA08`-`SA13`, `SA15`, `SA18`-`SA20`, `SA22`-`SA23`, `SA26`, `SA30`-`SA37` | WP1 `ANALYTICS`/`PORTFOLIO_INTELLIGENCE`/`AI_EVALUATION` versus Portfolio/Decision/Trust constitutional domains | WP1 is frozen; the constitutional domain names are reserved and cannot be treated as aliases by inference |
| Portfolio identity and strategy container | `SA01`, `SA25` | Portfolio domain model, Ledger & Accounting, Decision Intelligence, Wealth Intelligence | Scope ownership is explicit, but platform-domain ownership is split or unstated |
| Cross-portfolio exposure | `SA02` | Wealth Intelligence versus current Portfolio/Experience composition | Portfolio domain model places overall exposure above Portfolio |
| Sector classification | `SA11` | Asset Foundation, Market Intelligence, current Portfolio/Watchlist storage | Evidence source, stewarded classification, and copied display field are distinct |
| Freshness and “Updated” | `SA16` | Market Intelligence, Analytics/Decision/Trust producers, Experience refresh state | Observation, computation, retrieval, and client-completion times are different concepts |
| Goal, persona, policy, and limits | `SA25`, `SA39` | Portfolio scope, Wealth Intelligence, Decision Intelligence, configuration storage | Similar settings answer different domain questions |
| Execution/decision vocabulary | `SA27`-`SA30` | Decision Intelligence, Trust & Evaluation, Ledger & Accounting, legacy records | Current projections exist, but canonical planning/approval authority is closed or stopped |
| Operations composite | `SA36` | every source domain plus current aggregator | Composition does not transfer semantic ownership of source status |
| Watchlist membership | `SA38` | Experience, Decision Intelligence, or another existing owner | No governing artifact appoints one |

This is an inventory, not an ARB disposition. Evidence: `M34-E-0049`.

## 6. Shared Terminology Inventory

| Term | Observable meanings in the frozen surfaces | Required authority distinction | Glossary status |
| --- | --- | --- | --- |
| Portfolio | actual accounting boundary; Ideal portfolio; AI portfolio; cross-portfolio collection | Always qualify actual, Ideal, AI, Shadow, or Wealth aggregation | Actual `Portfolio` absent; Ideal/AI/Shadow defined |
| Value / NAV | portfolio total value; equity value; fund NAV; shadow value | Portfolio-derived valuation versus Market Intelligence fund observation | Absent as general product terms |
| Price | market observation; transaction price; prior price; target price | Observation versus ledger execution term versus Decision belief | Absent |
| Return / performance | investment return; daily/monthly/cumulative return; benchmark/shadow/horizon return | Owner, period, basis, currency, and series must be explicit | Absent |
| Contribution / contributor | P/L ranking; sector contribution; return effect; attribution effect | Ranking is not assumed to be attribution | Absent |
| Attribution | portfolio-return decomposition; regime grouping; evaluation effect waterfall | Portfolio Intelligence owns source measure; Trust may explain it | Absent |
| Recommendation | immutable belief snapshot; displayed trade plan; historical ledger row | Belief and plan are distinct recorded objects | Recommendation Snapshot defined only |
| Execution | legacy plan projection; human decision; linked transaction; evaluation of plan versus actual | Plan, authority, ledger fact, and evaluation must remain separate | Absent; Implementation Shortfall defined |
| Decision | legacy label; immutable Decision Intelligence record; M33 approval act | Current legacy decision cannot imply M33 authority | Absent |
| Risk | portfolio drawdown/concentration; instrument risk score; optimizer risk flag; policy limit | Portfolio knowledge, Decision judgment, and instrument analysis are different | Absent |
| Signal / consensus / confidence | instrument analysis, optimizer layer consensus, recommendation confidence, calibration input | Observation, belief, and evaluated honesty are separate | Absent |
| Updated / as of / current | client refresh completion; observation time; analysis generation; snapshot date; batch evaluation time | Every visible time must name the event it dates | Absent |
| Status | portfolio lifecycle; optimizer run; station health; decision; session/resource status | Qualify the subject and owning domain | Absent |
| Trust | evaluation evidence summary; data correctness; freshness; authorization; system health | Trust Report cannot silently claim all trust dimensions | Absent; Observer Plane is defined |
| Goal / policy / limit | portfolio strategy metadata; life goal; decision envelope; system configuration | Scope and owner must be named | Absent |

The bounded exact-heading search found canonical entries for Portfolio
Snapshot, Recommendation Snapshot, Shadow Portfolio, Ideal Portfolio, AI
Portfolio, Gap A, Gap B, Opportunity Cost, Recommendation Grade, and several
architectural terms. The majority of user-facing nouns above are not
registered. Domain documents may constrain them, but Constitution v1.1 does
not permit those documents to become a second canonical vocabulary.

Evidence: `M34-E-0047`, `M34-E-0049`.

## 7. Cross-domain Semantic Dependency Map

```text
Asset Foundation classification
             |
             v
Market Intelligence observations ----+
                                      |
Ledger & Accounting facts ------------+--> Portfolio Intelligence measures
                                      |       valuation/performance/risk/attribution
                                      |                    |
                                      v                    v
                              Decision Intelligence --> Trust & Evaluation
                              belief/plan/decision      grade/counterfactual/trust
                                      |                    |
                                      +---------+----------+
                                                v
                                       Experience Platform
                                       renders; owns no truth

Portfolio scope constrains each portfolio-scoped read.
Wealth Intelligence owns cross-portfolio/life-level meaning above that scope.
```

Dependency does not create shared ownership. Each downstream domain may
derive a new concept only within its own vocabulary and must retain the
upstream concept's provenance and meaning. Evidence: `M34-E-0039`,
`M34-E-0049`.

## 8. Candidate Authority Violations

These are verification candidates, not findings, severity classifications, or
dispositions.

| Candidate | Evidenced concern | Required verifier |
| --- | --- | --- |
| `AV01` | Frozen WP1 owner names do not align explicitly with reserved constitutional domain names | Architecture Review Board |
| `AV02` | Cross-portfolio exposure is rendered under the Portfolio entry while governing design assigns overall exposure to Wealth | Wealth/Portfolio architectural owner |
| `AV03` | Sector appears in Portfolio/Watchlist persistence although classification authority belongs to Asset Foundation and Market supplies evidence only | Asset Foundation + Market owner |
| `AV04` | “Updated” and related freshness labels can name client completion, source observation, analysis generation, or batch computation | Each source domain + Experience reviewer |
| `AV05` | Contribution/contributor labels lack one registered definition across P/L, sector, and attribution contexts | Portfolio Intelligence owner |
| `AV06` | Factor exposure, Portfolio DNA, and style drift have implementation definitions but no registered vocabulary or approved owner mapping | Portfolio Intelligence + Decision Intelligence owners |
| `AV07` | Legacy “execution plan” presentation exists while M32 says no canonical plan is active | Architecture Review Board under M32 closeout |
| `AV08` | Legacy decision labels can be mistaken for authoritative M33 human approval | Architecture Review Board under `STOP_M33_RUNTIME` |
| `AV09` | Evaluation execution detail composes Decision and Ledger records while its plan/authority inputs remain bounded by `AV07`/`AV08` | Decision, Ledger, and Trust owners |
| `AV10` | Operations status may appear to own source-domain health and action meaning through composition | Source-domain owners + Experience reviewer |
| `AV11` | The Settings surface groups policy, model, source, portfolio, and sector configuration without one evidenced semantic owner | Relevant domain owners |
| `AV12` | System Guide prose can become a parallel definition source because most product nouns are absent from the canonical Glossary | Governance owner + source-domain owners |
| `AV13` | Watchlist membership and instrument-analysis semantics have no named constitutional owner | Architecture Review Board |

Evidence: `M34-E-0046`, `M34-E-0047`, `M34-E-0049`.

## 9. Unknown Semantic Ownerships

| Unknown | Affected claims | Evidence needed |
| --- | --- | --- |
| Constitutional home of portfolio identity/strategy container | `SA01` | ARB ruling or explicit constitutional/domain mapping |
| Meaning and owner of the grouped instrument-analysis product contract | `SA21` | Separate definitions for facts, scores, beliefs, consensus, history, and provenance |
| Owner of Watchlist membership | `SA38` | Existing-domain assignment; no new domain is authorized by WP5 |
| Owner and vocabulary of operations station/committee/action status | `SA36` | Source-status grammar and owner map |
| Approved mapping from WP1 audit domains to constitutional domains | all `PROVISIONAL_MAPPING` rows | ARB-approved alias/mapping table or WP1 synchronization decision |
| Canonical vocabulary for unregistered product terms | 33 of 40 claim families | Glossary entries approved by the owning domains; WP5 does not author them |
| Safe product meaning of legacy execution and decision records | `SA27`-`SA30` | M32/M33-consistent ruling that does not activate stopped authority |
| Ownership split among goal, portfolio policy, Wealth intent, and system limits | `SA25`, `SA39` | Portfolio/Decision/Wealth boundary ruling |

Unknowns are not combined into an inferred owner. Evidence: `M34-E-0047`,
`M34-E-0049`.

## 10. Authority Completeness Assessment

| Completeness dimension | Result | Basis |
| --- | --- | --- |
| Frozen surface/claim coverage | Complete | all WP3 visible-output groups reconcile to `SA01`-`SA40` |
| WP4 read-contract coverage | Complete | every semantic family references the frozen 43-GET/static lineage where applicable |
| Constitutional owner model | Complete as a model | Platform Architecture assigns exclusive domain responsibilities |
| WP1-to-constitution owner mapping | Incomplete and material | no approved mapping; one WP1 label can point to two constitutional domains |
| Exact canonical vocabulary | Incomplete | only 7 of 40 claim families have a directly applicable exact Glossary definition |
| Cross-domain conflict handling | Complete as inventory | conflicts remain visible and no winner was inferred |
| M32/M33 preservation | Complete | stopped plan/approval authority remains stopped |
| Runtime ownership evidence | Not collected | no runtime execution authorized or needed for this authority question |
| Calculation verification | Not performed | explicitly excluded from WP5 |
| Findings and decisions | None | authority candidates require domain/ARB review before classification |

The inventory is complete; semantic authority is not. Evidence:
`M34-E-0048`, `M34-E-0049`, `M34-E-0050`.

## 11. Recommendation for WP6

**No — semantic authority is not sufficiently established for full M34-WP6.**

Proceeding would require WP6 to choose among frozen audit labels,
constitutional domains, technical documents, and current implementations.
That would violate WP1 evidence rule 7, the one-concept/one-owner invariant,
and Constitution v1.1 governance rules G4, G6, V1, and V2.

The affected work must return to the Architecture Review Board for exactly
these bounded decisions:

1. approve the mapping from WP1 audit-domain names to constitutional domains,
   especially `ANALYTICS`, `PORTFOLIO_INTELLIGENCE`, and `AI_EVALUATION`;
2. assign the unresolved portfolio identity, Watchlist, instrument-analysis,
   operations-status, goal/policy, and configuration concepts to existing
   domains without adding a new domain;
3. decide which unregistered terms must become canonical vocabulary before
   correctness can be judged;
4. state the permitted non-authoritative meaning of legacy execution/decision
   claims without reopening M32 or M33; and
5. approve a bounded WP6 entry set only after every included claim has one
   owner and one governing definition.

This is not `PRODUCT_CASE_NOT_PROVEN` and not an M34 exit decision. It is a
WP1 stop-condition escalation. M34.1 remains NO-GO.

## 12. Register Impact

- New corpus records: `M34-C-0049` through `M34-C-0058`.
- New verified evidence records: `M34-E-0039` through `M34-E-0050`.
- New review events: `M34-R-0012` through `M34-R-0015`.
- Findings created: zero.
- Decisions approved: zero.
- Runtime or test evidence collected: zero.

## 13. Explicit Non-Adoption Statement

M34-WP5 does not:

- evaluate a formula, calculation, valuation, return, risk, attribution,
  grade, counterfactual, or freshness result;
- appoint, rename, merge, or create a domain;
- amend WP1, the Platform Architecture, Glossary, a domain constitution,
  M32, M33, or the Decision Log;
- decide that an owner candidate, conflict, or authority-violation candidate
  is a defect;
- redesign a route, contract, service, persistence model, vocabulary, user
  journey, or navigation structure;
- propose Portfolio Home, a UI, or implementation work;
- execute an endpoint, query runtime data, call a provider, or run tests;
- modify frontend, backend, database, configuration, or runtime behavior;
- activate canonical execution planning or prospective approval authority;
- authorize M34-WP6, M34.1, or any runtime slice; or
- reopen M32 or M33.

M34.1 remains NO-GO.
