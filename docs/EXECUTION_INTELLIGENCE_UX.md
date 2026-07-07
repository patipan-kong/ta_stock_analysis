Version: 1.0 (Draft for review)
Status: Proposed
Owner: Portfolio Intelligence Platform
Phase: AI Evaluation & Execution Intelligence
Last Updated: 2026-07-06

# AI Evaluation & Execution Intelligence — UX Design

_UX architecture for the evaluation layer: the screens, components, and information
hierarchy that make the accountability loop of OPTIMIZER_PHILOSOPHY.md §11–§13 visible
to the user. This document contains no implementation; it defines what the user sees,
in what order, and why._

_Prerequisite reading: OPTIMIZER_PHILOSOPHY.md (§4, §9, §11, §12, §13), ARCHITECTURE.md
(Decision Memory & Attribution System)._

---

## 0. Design Thesis

The product this phase ships is **trust**, rendered as evidence.

Everything upstream already exists: beliefs are recorded, plans are classified, human
decisions are stored, shadow portfolios accumulate. What does not exist is the surface
where a user can ask — and get an honest, evidence-backed answer to — the only question
that matters long-term: *"Should I keep listening to this system?"*

Three commitments from the philosophy shape every screen below:

1. **Three lenses, never one number** (§12). Belief Quality, Execution Quality, and
   Outcome Quality are graded independently. No screen may present a return figure as
   *the* evaluation. Every outcome number appears alongside its decision-quality
   context, so "good decision, bad outcome" and "bad decision, lucky outcome" are both
   expressible — about the AI *and* about the human.

2. **Two objects, two report cards** (§4). The Belief (ideal portfolio) and the
   Execution Plan are evaluated separately. The gap between them — implementation
   shortfall — is a first-class displayed quantity, never an error to hide.

3. **The human is a participant, not an audience** (§13). Human decisions are data.
   The evaluation UI grades the human's calls on the same terms as the AI's, with the
   same honesty and the same protection against small-sample overconfidence. The tone
   is a shared scoreboard, never a scolding.

And one commitment from product craft:

4. **Honesty about evidence is the aesthetic.** Sample sizes, maturity states,
   "too early to say" — displayed plainly, in the same visual register as the wins.
   An evaluation page that only becomes confident when it has the right to be is the
   single strongest trust signal this product can emit. Bloomberg-grade density,
   Linear-grade restraint, zero gamification.

---

## 1. Information Architecture

### 1.1 The conceptual spine: The Three Portfolios

Every evaluation question in the phase brief reduces to comparisons among three
portfolio trajectories the system already produces:

```
  IDEAL (Belief)          what the AI believed capital should do
       │                  — recommendation snapshots / ideal weights, friction-free
       │  gap A = Implementation Shortfall  ("the price of practicality")
       ▼
  SHADOW (AI-executed)    what a 100%-compliant investor would hold
       │                  — ACTIVE_MODEL shadow portfolio
       │  gap B = Human Deviation           ("the price — or profit — of judgment")
       ▼
  HUMAN (Actual)          what the user actually holds
                          — real portfolio, real fills, real fees
```

- **Gap A** grades the *execution layer*: is the deterministic plan-maker giving away
  too much of the ideal (too timid) or nothing at all (not earning its existence)? (§12,
  Implementation Shortfall.)
- **Gap B** grades the *human-vs-AI question*: every reject, modify, delay, and override
  accumulates into this gap, and it can be positive — the UI must be genuinely neutral
  about who is winning.

This decomposition is the IA's backbone. The hero visualization of the entire phase is
one chart with these three lines and the two named gaps (screen S7). Every other module
is a drill-down into one line or one gap.

Per-recommendation counterfactuals ("was *that* call right?") use STATIC_FROZEN shadows;
the cumulative track record uses ACTIVE_MODEL. The UI vocabulary maps as:

| UI name (Quant) | UI name (MUJI/Thai) | System object |
|---|---|---|
| Ideal Portfolio | พอร์ตในอุดมคติของ AI | Recommendation snapshot target weights |
| AI Portfolio | พอร์ตเงา (ถ้าตามคำแนะนำ 100%) | ACTIVE_MODEL shadow |
| Your Portfolio | พอร์ตจริงของคุณ | Human portfolio |

### 1.2 The object model users navigate

```
Recommendation (immutable record, dated)
 ├─ Belief: ideal weights, conviction, regime & policy context
 ├─ Execution Plan: trades, each with Reason + Role + one-sentence cause
 ├─ Human Decision: APPROVED / REJECTED / PARTIAL / MODIFIED / OVERRIDE / EXPIRED
 ├─ Execution Record: what actually happened (fills, timing, sizes, funding)
 └─ Grades (append-only, issued at horizons)
     ├─ Decision Grade   — available day 0 (was it a good plan *as a plan*?)
     ├─ Horizon Outcomes — 7D → 30D → 90D → 180D returns, benchmark, alpha, drawdown
     └─ Counterfactuals  — frozen shadow vs actual; opportunity cost of the human delta
```

Two temporal rules govern everything users see:

- **Grades mature; they do not flicker.** A 30D outcome does not exist until day 30.
  Before that it is shown as *maturing* (with the date it unlocks), not as a live
  number that flips verdicts daily. Recommendation Stability (§12) applies to the
  evaluator too: an evaluation that reverses every morning is noise relayed at cost.
- **History is append-only.** No screen offers any action that edits a recommendation,
  a decision, or a grade. The evaluation layer only reads (§16). The only verbs in
  this entire phase are: navigate, filter, change period, export.

### 1.3 Module → screen map

The brief's seven modules organize into six screens plus one simple-mode view. Two
modules merge: Opportunity Cost is the quantitative half of Human vs AI (an ignored
recommendation *is* a human decision), but it earns its own screen because its visual
form (a counterfactual ledger) is distinct.

| Brief module | Screen | ID |
|---|---|---|
| 7. AI Scorecard | **Scorecard** — landing page, the whole system in one screen | S1 |
| 1. Recommendation Evaluation | **Recommendations** — ledger + per-recommendation Report Card | S2, S3 |
| 2. Execution Intelligence | **Execution** — decision ledger + execution quality detail | S4 |
| 3. Human vs AI | **Human vs AI** — cumulative scoreboard + override analysis | S5 |
| 4. Opportunity Cost | **Opportunity Cost** — counterfactual ledger | S6 |
| 5. Shadow Portfolio Analytics | **Portfolios** — the Three Portfolios comparison | S7 |
| 6. Attribution Analytics | **Attribution** — why performance happened | S8 |
| (MUJI mode) | **Trust Report** — plain-language summary for MUJI dashboard | S9 |

### 1.4 Where it lives

**Evolve `/ai-analytics` into the Evaluation hub.** Do not create a parallel page
(Reuse Before Create). The existing AI Analytics dashboard already aggregates
calibration/shadow/attribution fragments; this phase gives it a real IA. The four
AttributionPanel cards currently embedded in the optimizer page become deep links into
this hub, leaving a compact summary strip behind (the optimizer page stays focused on
*making* decisions; this hub is for *judging* them — two objects, two rooms).

---

## 2. Navigation Hierarchy

### 2.1 Top navigation — unchanged

The 4-item Thai top nav stays. The Evaluation hub joins the AI hub's match array:

```
พอร์ตโฟลิโอ        → /portfolio /performance /analytics /stock
รายการเฝ้าดู       → /watchlist
AI                → /operations-center /optimizer /portfolio-intelligence /ai-analytics  ← hub lives here
📚 คู่มือ          → /system-guide
```

Rationale: evaluation is the AI's report card — users will look for it where the AI
lives, not where their portfolio lives. Adding a 5th top-level item would undo the
4C.2A simplification for a feature used weekly, not hourly.

### 2.2 Hub sub-navigation

Inside `/ai-analytics`, a persistent segmented control (same pattern as
`PortfolioTabs`), Scorecard as default tab:

```
[ สรุปผลงาน (Scorecard) | คำแนะนำ (Recommendations) | การตัดสินใจ (Execution) |
  คน vs AI (Human vs AI) | พอร์ตเปรียบเทียบ (Portfolios) | ที่มาผลตอบแทน (Attribution) ]
```

Opportunity Cost is reached from within Human vs AI (tab or prominent card link), not
as a 7th segment — six segments is already the ceiling for a segmented control; beyond
that it degrades into a junk drawer.

Routes:

```
/ai-analytics                       → Scorecard (S1)
/ai-analytics/recommendations       → Ledger (S2)
/ai-analytics/recommendations/{id}  → Report Card (S3)
/ai-analytics/execution             → Execution ledger (S4)
/ai-analytics/execution/{id}        → Execution detail (S4b)
/ai-analytics/human-vs-ai           → Scoreboard (S5)
/ai-analytics/opportunity-cost      → Counterfactual ledger (S6)
/ai-analytics/portfolios            → Three Portfolios (S7)
/ai-analytics/attribution           → Attribution (S8)
```

All routes carry the active-portfolio context from the global portfolio picker, as the
rest of the app already does.

### 2.3 Contextual entry points (how people actually arrive)

Evaluation is rarely a destination; it is a question that occurs elsewhere. Each
existing surface gets exactly one link into the hub, at the moment the question arises:

| Surface | Moment | Link target |
|---|---|---|
| Optimizer history detail | "How did this run turn out?" | Report Card (S3) for that snapshot |
| DecisionActionPanel (after deciding) | "Track this decision" | Execution detail (S4b) |
| Performance page | "Why this return?" | Attribution (S8) |
| Ops Center Quant dashboard | headline verdict tile | Scorecard (S1) |
| Ops Center MUJI dashboard | Trust Report card (S9) | Scorecard (S1), framed gently |
| Execution Plan Card (new rec) | "AI's track record on calls like this" | Human vs AI (S5), pre-filtered |

The last row is the trust loop closing: at the moment of a new decision, the user can
see the graded history of similar past calls. That is the entire point of the phase.

### 2.4 Breadcrumbs

Reuse `BackBreadcrumb`. Detail pages: `AI → สรุปผลงาน → คำแนะนำ #142`.

---

## 3. Dashboard Layout (Scorecard as hub landing)

### 3.1 Layout skeleton

Desktop, 12-col grid, max-width aligned with existing pages. Vertical order = the
order of the questions a skeptical user asks:

```
Row 0  Context bar     portfolio • period selector (90D default | 180D | 1Y | All) • as-of stamp
Row 1  Verdict strip   one plain sentence + three lens grades (the whole page in 80px)
Row 2  Three lenses    Belief Quality │ Execution Quality │ Outcome Quality  (3 equal cards)
Row 3  Hero chart      Three Portfolios mini (Ideal / AI / You) + the two named gaps
Row 4  KPI grid        8–10 stat tiles (the brief's scorecard KPIs), grouped under lens headers
Row 5  Evidence feed   most recent graded events ("Rec #141 reached 30D: +4.2% vs SET +1.1%")
```

### 3.2 The verdict strip (Row 1)

One sentence, generated from the same data as the tiles, stating the current state of
the relationship in natural language, with the three lens grades beside it:

> "ในช่วง 90 วันที่ผ่านมา คำแนะนำของ AI ให้ผลดีกว่าตลาด และการตัดสินใจของคุณ
> ทำผลงานได้ดีกว่าการทำตาม AI ทั้งหมดเล็กน้อย"
> (Over the last 90 days, AI recommendations beat the benchmark, and your own
> decisions slightly outperformed full compliance.)
>
> `Belief A− (n=14)` `Execution B+ (n=11)` `Outcome — maturing (68% graded)`

Rationale: §1 — a recommendation (or an evaluation) nobody understands has zero value.
The sentence is the MUJI translation surfacing in Quant mode too; both modes share one
source of truth for the verdict (Single Source of Truth). Letter-grade chips are used
*only* here and on lens cards, only when n clears a minimum, and always with n shown.

### 3.3 KPI grid contents (Row 4)

Grouped under lens headers so no KPI floats free of its epistemic status:

- **Belief** — Recommendation Accuracy (hit rate at 30D, directional), Average Alpha
  per recommendation, Confidence Calibration (stated vs realized), Ideal Portfolio
  return vs benchmark.
- **Execution** — Plan Quality score (necessity/funding/turnover/explanation composite),
  Funding Efficiency, Trade Necessity ratio, Implementation Shortfall (Gap A).
- **Outcome** — Your return vs AI Portfolio return vs Ideal return (three numbers, one
  tile), Win Rate (AI beat human / human beat AI), Net Opportunity Cost, Max Drawdown
  (all three portfolios).

Every tile: value, period delta, sparkline where trend matters, `n=` chip, maturity
chip when the window is partially graded.

---

## 4. Card Hierarchy

Five levels, strict. Each level answers one question and defers detail to the next:

```
L1  PAGE      the question       "Is the AI good?"                (Scorecard)
L2  SECTION   the lens           "Are its ideas good?"            (Belief Quality)
L3  CARD      the claim          "Recommendation accuracy 71%"    (KPI card / verdict card)
L4  METRIC    the number         value • delta • n • maturity     (stat tile row inside card)
L5  EVIDENCE  the receipts       per-recommendation rows, charts  (drawer / detail page)
```

Rules:

1. **A claim without receipts doesn't ship.** Every L3 card either contains its L5
   evidence inline (ledger rows) or links to exactly one place that has it. Mirrors
   Invariant 6 — no unexplained trades; here, no unexplained *grades*.
2. **A number without epistemic status doesn't ship.** Every L4 metric carries `n`,
   period, and maturity. Below minimum n, the verdict chip is replaced by
   `หลักฐานยังไม่พอ (n=3)` — "insufficient evidence" — in neutral gray, same size, no
   apology. False precision is a §8 sin; it applies to metrics too.
3. **Color is direction-only.** Muted green/red for better/worse *than the comparison
   stated on the card* — never for decoration. Verdict chips use the existing muted
   badge palette (signal-badge hexes). Everything else: grayscale + one accent.
   Numbers in tabular figures, right-aligned in tables.
4. **One verdict per card, sentence-first.** The generated sentence leads; numbers
   support. Never two competing headline numbers on one card.
5. **Comparisons are explicit.** Every return states its baseline inline: "vs SET",
   "vs AI Portfolio", "vs doing nothing". An unlabeled +4.2% is meaningless and
   erodes exactly the trust this phase exists to build.

---

## 5. Screen-by-Screen Wireframes

Wireframes are desktop Quant mode; Thai labels abbreviated to EN for legibility here.
Production labels follow the bilingual pattern of existing pages (Thai primary,
EN metric vocabulary).

### S1 — AI Scorecard  `/ai-analytics`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Portfolio: Main ▾            Period: [7D][30D][90D*][180D][1Y][All]          │
│                                              as of 2026-07-06 17:45 ICT      │
├──────────────────────────────────────────────────────────────────────────────┤
│ VERDICT  "Over 90D, AI recommendations beat the benchmark; your decisions    │
│           slightly outperformed full compliance."                            │
│           Belief A− (n=14)   Execution B+ (n=11)   Outcome ◐ maturing (68%)  │
├────────────────────────┬────────────────────────┬────────────────────────────┤
│ BELIEF QUALITY         │ EXECUTION QUALITY      │ OUTCOME QUALITY            │
│ Were the ideas good?   │ Were the plans good?   │ Did it work?               │
│                        │                        │                            │
│ Rec accuracy   71% ▲   │ Plan quality   86/100  │ You        +6.8%           │
│ Avg alpha    +1.9% ▲   │ Funding eff.   94%     │ AI Port.   +6.1%           │
│ Calibration  said 74%  │ Necessity      82%     │ Ideal      +7.4%           │
│              hit 71% ✓ │ Shortfall    −0.6%/90D │ SET        +3.2%           │
│ n=14 · 10 graded       │ n=11 plans             │ Max DD  −7.1/−6.4/−8.0%    │
│              [detail →]│             [detail →] │                [detail →]  │
├────────────────────────┴────────────────────────┴────────────────────────────┤
│ THE THREE PORTFOLIOS (90D)                                        [full → S7]│
│   ┈┈┈ Ideal      ─── AI Portfolio      ━━━ You                               │
│   ▁▂▃▃▄▅▄▅▆▆▇  (indexed to 100)                                              │
│   Gap A  Ideal−AI   −0.6%  implementation shortfall                          │
│   Gap B  AI−You     +0.7%  your decisions added value                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ RECENT GRADES                                                                │
│ • Jul 04  Rec #141 reached 30D — +4.2% vs SET +1.1% · APPROVED       [→ S3]  │
│ • Jul 01  Override on BH graded — you avoided −2.3%                  [→ S5]  │
│ • Jun 28  Rec #139 EXPIRED ungraded (no decision within window)      [→ S4]  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### S2 — Recommendations ledger  `/ai-analytics/recommendations`

A dense, Bloomberg-style table. Every recommendation snapshot ever made, newest first.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Filters: [Period ▾] [Decision: All ▾] [Consensus: All ▾] [Regime: All ▾]     │
├──────────────────────────────────────────────────────────────────────────────┤
│  #   Date    Consensus  Trades  Decision   7D     30D     90D    180D  Alpha │
│ 142  Jul 02  STRONG      3      APPROVED  +1.2%   ◐ 12d   ◌      ◌     —     │
│ 141  Jun 04  REFINED     2      APPROVED  +0.8%  +4.2%    ◐ 32d  ◌    +3.1%  │
│ 140  May 28  STRONG      0      (no action recommended)  — market +2.0% —    │
│ 139  May 21  PARTIAL     4      PARTIAL   −0.4%  +1.1%   +5.0%   ◌    +1.8%  │
│ 138  May 12  WEAK        2      REJECTED  +0.3%  −2.1%*  −1.4%*  ◌    −3.9%* │
│                                  * counterfactual — plan was not executed    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Column key: ◌ not yet due · ◐ maturing (days remaining) · % graded at horizon│
└──────────────────────────────────────────────────────────────────────────────┘
```

Design notes:
- **"Do nothing" rows are first-class** (row 140): the recommendation *not to trade*
  is graded too — against what the market did. §8 says silence must be informative;
  the ledger is where its track record lives.
- Rejected/ignored rows show *counterfactual* returns, typographically marked
  (asterisk + muted style) so real and hypothetical money are never confusable.
- Row click → S3.

### S3 — Recommendation Report Card  `/ai-analytics/recommendations/{id}`

The page that answers "was recommendation #141 right?" — in three lenses, on one page.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Recommendations        REC #141 · Jun 04 2026 · REFINED_CONSENSUS          │
│ Context at decision time: RISK_ON · Policy: BALANCED · Confidence 74%        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 1 · THE PLAN (immutable record)                                              │
│  BUY  CENTEL  30,000 THB  Reason: Portfolio Improvement  · funded from cash  │
│  REDUCE BH   deferred     Reason: Portfolio Improvement  · no funding need   │
│  Plan grade (day 0): 92/100 — necessary, funded from cash, 2 trades, all     │
│  explained. [breakdown ▾]                                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2 · WHAT HAPPENED                                                            │
│  Your decision: APPROVED (executed Jun 05, 1 day later)                      │
│  Timing delta: −0.3% (price moved against you before execution)              │
│  Size delta: none · Funding delta: none                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ 3 · OUTCOME (frozen shadow vs benchmark, from Jun 04)                        │
│   7D    +0.8%   vs SET +0.2%   alpha +0.6%          ✓ graded                 │
│   30D   +4.2%   vs SET +1.1%   alpha +3.1%          ✓ graded                 │
│   90D   ◐ maturing — grades Sep 02                                           │
│   180D  ◌ due Dec 01                                                         │
│   Max drawdown within window: −2.9%                                          │
│   Confidence check: stated 74% · this call ✓ correct at 30D                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ VERDICT (30D): "A good plan, well executed, that worked. CENTEL contributed  │
│ +3.4%; deferring the BH sale avoided fees with no cost so far."              │
└──────────────────────────────────────────────────────────────────────────────┘
```

The three sections *are* the three lenses, in pipeline order: plan → execution →
outcome. Section 1 is graded on day 0 (§11: quality is assessable when made); its
grade never changes. Sections 2–3 fill in as reality arrives.

### S4 — Execution Intelligence  `/ai-analytics/execution`

Ledger of human decisions and how execution compared to the plan.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SUMMARY (90D)                                                                │
│  Decisions: 11   APPROVED 6 · PARTIAL 2 · REJECTED 2 · OVERRIDE 1            │
│  Acceptance by trade class:   ← the only honest way to read acceptance (§9)  │
│    Mandatory Risk   ████████████ 100% (2/2)                                  │
│    Policy           ████████████ 100% (1/1)                                  │
│    Improvement      ████████░░░░  67% (6/9)                                  │
│    Rebalancing      ████░░░░░░░░  33% (1/3)                                  │
│  Avg execution score 84 · Avg timing delta −0.2% · Funding fidelity 96%      │
├──────────────────────────────────────────────────────────────────────────────┤
│  Date    Rec   Decision   Exec score  Timing   Size Δ   Funding   Outcome Δ  │
│  Jul 02  #142  APPROVED       91      −0.1%    exact    as plan   ◐          │
│  Jun 21  #140  —              —       —        —        —         —          │
│  Jun 04  #141  APPROVED       88      −0.3%    exact    as plan   +0.0%      │
│  May 21  #139  PARTIAL        62      −0.5%    58% of   improvised −1.1%     │
│  May 12  #138  REJECTED       —       —        —        —         +3.9%*     │
└──────────────────────────────────────────────────────────────────────────────┘
```

Detail page (S4b) for one decision: plan vs actual side-by-side per trade, the four
deltas (timing / size / funding / completeness) each with its cost or benefit in %,
and — for PARTIAL — the §8 warning made visible: *"Partial execution produced a
portfolio nobody designed: 2 of 4 trades executed, leaving sector X overweight."*

Note the class-segmented acceptance bars: a 67% acceptance rate means nothing; 100%
acceptance of Mandatory trades plus 33% of Rebalancing trades means the user trusts
the risk logic and finds the discretionary suggestions too chatty — exactly the signal
§12 says only classification makes readable.

### S5 — Human vs AI  `/ai-analytics/human-vs-ai`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ THE SCOREBOARD (since inception · n=23 graded decisions)                     │
│                                                                              │
│   You beat AI      9 ██████████░░░░░░░░░  AI beat you      11                │
│   ties (±0.3%)     3                                                         │
│   Net effect of your judgment vs full compliance:  +0.7% (90D)               │
│   ◐ 5 decisions still maturing — scoreboard updates as they grade           │
├──────────────────────────────────────────────────────────────────────────────┤
│ WHERE EACH SIDE WINS (by trade class · by override type)                     │
│   Your rejections of Rebalancing trades:  right 4/5 times  (+1.9% saved)     │
│   Your rejections of Improvement trades:  right 1/4 times  (−2.2% missed)    │
│   Your timing overrides:                  right 2/3 times  (+0.4%)           │
│   Your size reductions:                   right 1/3 times  (−0.8%)           │
├──────────────────────────────────────────────────────────────────────────────┤
│ TIMELINE  cumulative Gap B (AI Portfolio − You), with decision markers       │
│   ▲ marks = your interventions · hover = that decision's story               │
├──────────────────────────────────────────────────────────────────────────────┤
│ [→ Opportunity Cost ledger: every ignored/modified call, priced]             │
└──────────────────────────────────────────────────────────────────────────────┘
```

Tone rule: symmetrical language, always. "You were right about BH" and "the AI was
right about CENTEL" render identically. The moment this page reads as the machine
keeping score *against* the user, it stops being consulted — and unconsulted
evaluation is dead weight. The framing is: *"where is each of you strong?"* — which is
also the actually useful question, since its answer changes future behavior (trust the
AI on X, trust yourself on Y).

### S6 — Opportunity Cost  `/ai-analytics/opportunity-cost`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ NET OPPORTUNITY COST (90D):  −1.4%                                           │
│ "Not following AI recommendations cost about 1.4% this quarter — mostly one  │
│  ignored BUY. Ignoring two SELL calls helped."                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ WATERFALL (what each divergence did, vs full compliance = 0)                 │
│                                                                              │
│   Ignored BUY  AOT      ▼▼▼▼▼▼▼▼  −2.6%   missed rally                      │
│   Late entry   CENTEL   ▼ −0.3%            1-day delay                       │
│   Partial exec #139     ▼▼ −1.1%           unexecuted half underperformed    │
│   Ignored SELL BH       ▲▲▲ +1.9%          BH recovered — good call          │
│   Size override PTT     ▲ +0.4%            smaller size, stock fell          │
│   Ignored SELL KBANK    ▲ +0.3%            avoided fees, flat stock          │
│   ───────────────────────────────────                                       │
│   NET                    −1.4%                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Each row: [→ decision detail]      ◐ 2 divergences still maturing            │
└──────────────────────────────────────────────────────────────────────────────┘
```

Design commitments:
- **Symmetric by construction.** Green rows (ignoring helped) and red rows (ignoring
  cost) in one waterfall, sorted by magnitude. §12: "a philosophy that cannot measure
  its own downside is dogma" — same rule for the user's downside *and* the AI's.
- This is also the honesty ledger for the deferral doctrine: a companion strip shows
  what the *system's own* deferred trades (e.g., the deferred BH reduce) would have
  done — the Opportunity Cost metric of §12 pointed at the machine.
- Counterfactual typography (muted, marked) throughout: none of these numbers are
  realized money.

### S7 — Portfolios (Three Portfolios / Shadow Analytics)  `/ai-analytics/portfolios`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ PERFORMANCE (indexed, 90D)          [90D ▾]      ┊ inception markers shown   │
│    Ideal ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈╱╲┈┈┈┈ +7.4%                                         │
│    AI    ────────────╱─────╲── +6.1%                                         │
│    You   ━━━━━━━━╱━━━━━━━━━━━ +6.8%    SET ····· +3.2%                       │
│                                                                              │
│    Gap A (Ideal−AI)  −0.6% — the price of practical execution                │
│    Gap B (AI−You)    +0.7% — the effect of your decisions                    │
├──────────────────────────────┬───────────────────────────────────────────────┤
│ ALLOCATION (side-by-side)    │ RISK                                          │
│  sector bars ×3 portfolios   │            Ideal    AI      You               │
│  Tech    32% · 30% · 35%     │  Max DD    −8.0%   −6.4%   −7.1%              │
│  Fin     18% · 18% · 15%     │  Vol (ann) 14.2%   12.8%   13.5%              │
│  Health  12% · 12% · 12%     │  Cash       6%      9%      11%               │
│  …                           │  Beta       0.92    0.88    0.90              │
├──────────────────────────────┴───────────────────────────────────────────────┤
│ CONTRIBUTION (90D, per holding)   who created the alpha, in which portfolio  │
│  CENTEL  +2.1% (all three) · AOT +1.8% (Ideal & AI only — you didn't buy) …  │
├──────────────────────────────────────────────────────────────────────────────┤
│ DRAWDOWN (underwater chart, 3 lines)                                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

The gap annotations do the teaching. A persistent large Gap A means execution is too
timid; a ~zero Gap A means the execution layer isn't earning its keep; a negative
Gap A means the belief engine has a problem (§12 gives exactly this reading — the UI
prints the applicable interpretation under the number as a one-liner).

### S8 — Attribution  `/ai-analytics/attribution`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ WHY YOUR RETURN HAPPENED (90D)                                               │
│ "You returned +6.8% vs SET +3.2%. Most of the +3.6% difference came from     │
│  stock selection. Execution timing cost a little; your overrides added."     │
├──────────────────────────────────────────────────────────────────────────────┤
│ WATERFALL   Benchmark → You                                                  │
│   SET                    +3.2%  ─┐                                           │
│   Selection effect       +2.9%   ▲▲▲▲▲▲                                      │
│   Allocation effect      +0.6%   ▲                                           │
│   Timing effect          −0.4%   ▼                                           │
│   Execution effect       −0.2%   ▼   (fees, partial fills)                   │
│   Funding effect         +0.0%   ·                                           │
│   Your overrides         +0.7%   ▲▲                                          │
│   ───────────────────────────                                                │
│   You                    +6.8%                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ BY SECTOR (BHB table) · BY REGIME (returns per regime state) · BY HOLDING    │
│  [three tabs, dense tables, each row → evidence]                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

The waterfall's leading sentence is generated with it and says the same thing — a user
should be able to read *only* the sentence and leave correctly informed. Effects whose
estimation is structurally weak (per-sector BHB awaits per-sector benchmark data — see
DECISION_LOG) are shown with an `approx` chip rather than silently rendered precise.

### S9 — MUJI Trust Report (card on MUJI dashboard)

MUJI users get one calm card, not the hub:

```
┌───────────────────────────────────────────────┐
│  รายงานความน่าเชื่อถือของ AI                     │
│                                               │
│  ใน 3 เดือนที่ผ่านมา คำแนะนำของ AI              │
│  ให้ผลดีกว่าตลาด +2.9%                          │
│                                               │
│  คุณทำตามคำแนะนำ 8 จาก 11 ครั้ง                 │
│  การตัดสินใจของคุณเองก็ทำได้ดี (+0.7%)           │
│                                               │
│  สิ่งที่น่าสนใจ: ครั้งที่คุณไม่ทำตาม คำแนะนำ        │
│  ประเภท "ปรับสมดุล" มักเป็นการตัดสินใจที่ถูก       │
│                                               │
│  ดูรายละเอียดทั้งหมด →                          │
└───────────────────────────────────────────────┘
```

Three sentences maximum: how the AI did, how the human did, one insight. Generated
from the same verdict source as S1 (`muji_translator` pattern already exists). No
numbers beyond two; no grades; no jargon.

---

## 6. Component System

New components, each mapped to where it appears. All follow the existing card/table
idiom; nothing introduces a new visual language.

| Component | Purpose | Spec highlights |
|---|---|---|
| `VerdictSentence` | L3-level generated plain-language claim | Always paired with the data that produced it; bilingual; single source shared by Quant + MUJI |
| `LensGradeChip` | Belief/Execution/Outcome grade | Letter grade + `n=`; renders as neutral "insufficient evidence" below min n; muted badge palette |
| `HorizonStrip` | 7/30/90/180D returns for one recommendation | Three states per cell: graded ✓ (number), maturing ◐ (days left), not due ◌ (date); grades never restyle after issuance |
| `MaturityChip` | `◐ maturing — grades Sep 02` | The single mechanism for "too early"; used everywhere, styled once |
| `SampleSizeChip` | `n=14` | Mandatory on every aggregate metric; tooltip explains the minimum-n rule |
| `CounterfactualValue` | Any hypothetical return | Muted color + asterisk + tooltip "not realized money — what would have happened"; the ONLY way hypothetical numbers may render |
| `GapAnnotation` | Named Gap A / Gap B figure | Value + one-line interpretation drawn from the §12 reading rules |
| `ThreePortfolioChart` | Hero comparison line chart | Indexed to 100; Ideal dashed, AI solid, Human bold, benchmark dotted gray; decision markers on hover |
| `EffectWaterfall` | Attribution & opportunity-cost decomposition | Horizontal bars, sorted by |magnitude|, net row pinned; `approx` chip for weak estimates |
| `ClassAcceptanceBars` | Acceptance rate segmented by trade Reason | Reuses trade-class badges from ExecutionPlanCard; never renders an unsegmented total alone |
| `CalibrationCurve` | Stated confidence vs realized frequency | Diagonal reference; dots sized by n; already partially exists in calibration cards — consolidate |
| `EvidenceLedger` | Dense sortable table (S2/S4/S6 rows) | Tabular figures, right-aligned numerics, row → detail; virtualized beyond ~100 rows |
| `AsOfStamp` | Data freshness | Every page header; shows last valuation/attribution run; stale (>24h) turns amber with reason (observable degraded mode) |
| `DecisionStatusBadge` | APPROVED/REJECTED/PARTIAL/OVERRIDE/EXPIRED | Reuse the existing decision vocabulary from DecisionActionPanel — same words end-to-end |

Reused as-is: `BackBreadcrumb`, segmented tab control (`PortfolioTabs` pattern),
signal badges, sector colors (`lib/sectors.ts`), existing card chrome.

Type & color discipline: existing app fonts; numerals in tabular lining figures.
Semantic color budget per screen: green/red for direction, amber for staleness/warning,
one accent for interactive — nothing else. Charts default to grayscale + accent;
the three portfolio lines are distinguished by weight/dash, not by rainbow.

---

## 7. Empty States — the Cold-Start Ladder

Evaluation has the hardest cold-start in the product: it is *supposed* to be empty for
weeks. The design treats immaturity as a first-class narrative, never as failure, and
never fakes or extrapolates.

**Rung 0 — no recommendations yet.**
Scorecard renders the three lens cards with their *questions* ("Were the ideas good?")
and one line each: "จะเริ่มประเมินได้หลังจากรันคำแนะนำครั้งแรก" plus a single CTA to the
optimizer. No zeros, no empty charts (an empty chart reads as a broken product; a
stated plan reads as a patient one).

**Rung 1 — recommendations exist, nothing graded (days 0–7).**
Ledgers fill; Report Cards show section 1 (plan grade — available day 0, by design the
first thing the product can honestly grade) with sections 2–3 as maturity chips:
"เกรดแรก (7 วัน) จะออกวันที่ 13 ก.ค." The Scorecard verdict strip says exactly that.
This rung teaches the product's core idea — *plans are gradeable before outcomes* —
precisely because nothing else is available yet.

**Rung 2 — first horizons graded (weeks 1–6).**
Numbers appear with low-n chips; verdict sentences stay deliberately modest ("ยังเร็ว
เกินไปที่จะสรุป — 3 จาก 14 คำแนะนำได้เกรดแล้ว"). Win-rate style aggregates remain
"insufficient evidence" until minimum n.

**Rung 3 — mature (90D+ of history).** Full experience as wireframed.

Rules across all rungs: every empty/immature slot states *what* will appear and *when*
(a date, not "soon"); the layout never reflows as data matures — chips are replaced by
numbers in place, so week 6 looks like week 1 grown up, not a different product.
Additional per-screen empties: no divergences yet on S6 → "คุณทำตามคำแนะนำทั้งหมด —
ยังไม่มีต้นทุนค่าเสียโอกาสให้วัด" (a *finding*, not an absence); no overrides on S5 →
scoreboard shows compliance track record only.

---

## 8. Loading States

- **Skeletons match final geometry.** Each card has a skeleton of identical size;
  numbers pulse as fixed-width blocks. No spinners inside metric positions, no layout
  shift on resolve. Ledgers skeleton 8 rows.
- **Ledger first, aggregates second.** On slow loads, raw evidence (recent rows)
  renders before computed aggregates — receipts before claims, even in loading order.
- **Everything is as-of, nothing is live.** Evaluation reads batch-computed artifacts
  (daily valuation at 17:45 ICT, attribution runs). The `AsOfStamp` makes this honest;
  there are no streaming numbers on any evaluation screen. This kills an entire class
  of "why did it change while I looked at it" trust bugs and matches the append-only
  model.
- **Degraded modes are labeled, not silent** (ENGINEERING_PRINCIPLES): if attribution
  hasn't run, or benchmark prices are stale, the affected card renders its last good
  data with an amber banner stating the reason and the recovery path — never a blank,
  never a silent zero.
- **Partial failure isolates.** Each L3 card fetches independently; one failed
  aggregate never blanks the page.

---

## 9. Mobile Considerations

Mobile evaluation is *review*, not analysis. One column, in the Scorecard's row order.

- **S1** verdict strip + three lens cards (stacked) + Recent Grades survive; hero
  chart collapses to three sparkline-and-number rows (Ideal/AI/You).
- **Ledgers (S2/S4/S6)** become stacked cards: line 1 identity + decision badge,
  line 2 `HorizonStrip` (horizontally scrollable strip is the one permitted
  horizontal scroll), line 3 verdict sentence.
- **S7** chart keeps all three lines but drops markers/hover; gap annotations move
  below as two plain rows. Allocation comparison becomes per-sector grouped bars,
  vertically stacked.
- **Waterfalls (S6/S8)** render natively as horizontal bars — they stack well; keep.
- **Tap = navigate, never hover-dependent.** All hover evidence has a tap path (row →
  detail page). Tooltips are supplementary everywhere, load-bearing nowhere.
- Thai-first labels are already mobile-economical; keep metric abbreviations (7D/30D)
  universal.

---

## 10. Future Scalability

The IA is built so growth lands in existing slots (§16: modules evolve, contracts
don't):

- **New metrics → existing lenses.** Any §12 metric not yet shipped (recommendation
  stability, explanation-truthfulness audits) is a new L3 card under the correct lens
  section. No new nav, no new page.
- **Broker integration** upgrades Execution Intelligence data (real fills, slippage)
  without changing S4's shape — the four deltas just get more precise, and a fifth
  (slippage) slots into the same table.
- **Delegated autonomy** (§16's revocable-delegation future): S4 gains a decision
  status `AUTO_EXECUTED (delegated)`, and the Human-vs-AI scoreboard gains a
  "delegated" segment. The evaluation UI is precisely the surface on which a user
  would *earn the confidence* to delegate — the delegation controls should one day
  live next to the track record that justifies them.
- **Multi-portfolio / household**: every screen is already portfolio-scoped via the
  global picker; an "all portfolios" aggregate is an additional picker entry, not a
  redesign.
- **New asset classes / wealth-advisor scope**: the three-lens, three-portfolio,
  horizon-graded structure is asset-agnostic; only contribution and allocation
  vocabularies extend.
- **Comparative model evaluation** (multiple AI configurations): the Ideal/AI lines
  generalize to N shadow lines; `ThreePortfolioChart` is specified as a line-set
  component, not a three-line component, for exactly this reason.

---

## 11. UX Rationale — Decision Register

| # | Decision | Rationale (philosophy anchor) |
|---|---|---|
| D1 | Three-lens structure everywhere; no outcome number without decision-quality context | §11–§12: outcome-only grading teaches gambling; layered grading makes diagnosis possible |
| D2 | Grades issued at fixed horizons; maturity chips; verdicts never flicker | §12 Recommendation Stability applied to the evaluator; trust requires stable statements |
| D3 | Hero = Three Portfolios chart with named Gaps A/B | §4 two objects + §12 implementation shortfall: the architecture's key quantities become the product's key picture |
| D4 | Plan grade rendered on day 0, before any outcome | §11: recommendation quality is assessable when made — the UI proves the claim by doing it |
| D5 | Acceptance rates only ever shown segmented by trade class | §12 Human Acceptance Rate: "the same overall rate can mean opposite things" |
| D6 | Opportunity cost waterfall is symmetric (human wins shown equally) and includes the system's own deferrals | §12 Opportunity Cost: the philosophy must measure its own downside; §13 evenhanded human-vs-AI scoring |
| D7 | Counterfactual numbers have a mandatory distinct typographic treatment | Fiduciary honesty: hypothetical and realized money must be unconfusable at a glance |
| D8 | Evaluation screens are 100% read-only; verbs = navigate/filter/export | §16: an evaluation layer that can nudge what it evaluates isn't one; Invariant 1 append-only history |
| D9 | Verdict sentences generated from the same source in Quant and MUJI | §1 explainability; Single Source of Truth; one verdict, two registers |
| D10 | Mandatory `n=` and insufficient-evidence states on all aggregates | §8 false precision; early-days honesty is the product's strongest trust signal |
| D11 | "Do nothing" recommendations appear and are graded in the ledger | §8: silence must be informative — so it must be scored |
| D12 | Hub lives inside AI nav at `/ai-analytics` (evolved, not duplicated); optimizer page keeps only a summary strip | Reuse Before Create; 4C.2A nav simplification preserved; deciding and judging are different rooms (§4) |
| D13 | All data as-of batch timestamps; no live numbers; degraded modes labeled | ENGINEERING_PRINCIPLES observable-degradation; append-only mental model; kills "it changed while I looked" trust bugs |
| D14 | Neutral, symmetric tone in Human-vs-AI language | §13: the human is the permanent decision maker; a scoreboard that scolds stops being consulted |

---

## Open Questions (for implementation planning, not blocking design)

1. **Minimum n for verdict chips** — proposal: n≥8 graded events for letter grades,
   n≥5 for win rates; below that, insufficient-evidence state. Needs a decision
   recorded in DECISION_LOG when fixed.
2. **Execution score composition** — S4 assumes a 0–100 composite of timing/size/
   funding/completeness. Weights are implementation's to define (philosophy: formulas
   belong to implementation) but must be documented and inspectable from the UI
   (`[breakdown ▾]`).
3. **EXPIRED decision status** — recommendations that received no decision within a
   window currently have no explicit terminal state; S2/S4 assume one exists. Schema
   question for the implementation phase.
4. **Per-sector BHB completeness** — attribution sector tab depends on per-sector
   benchmark data (known structural stub); ship with `approx` chip or hold the tab?
