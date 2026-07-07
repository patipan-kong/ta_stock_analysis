Version: 1.0
Status: Complete (M0–M7 shipped)
Owner: Portfolio Intelligence Platform
Phase: AI Evaluation & Execution Intelligence
Design Baseline: EXECUTION_INTELLIGENCE_UX.md v1.0 (approved)
Audience: Implementing agent (Claude Sonnet 5)
Last Updated: 2026-07-07

# AI Evaluation & Execution Intelligence — Implementation Plan

_Engineering blueprint translating the approved UX baseline into ordered, testable
milestones. This document decides **what to build, in what order, on which existing
assets** — it does not re-litigate the UX and it does not redesign the optimizer._

---

## 0. Working Agreement for the Implementing Agent

1. **Read first, every session**: CLAUDE.md required docs (ENGINEERING_PRINCIPLES.md,
   ARCHITECTURE.md, OPTIMIZER_PHILOSOPHY.md, PORTFOLIO_CALCULATION_RULES.md,
   DECISION_LOG.md), then EXECUTION_INTELLIGENCE_UX.md, then this plan.
2. **One milestone = one reviewable unit.** Do not start milestone N+1 in the same
   change-set as N. Each milestone ends with its tests green and its acceptance
   criteria checked.
3. **The UX doc wins on what the user sees; this plan wins on build order.** If
   implementation reveals a conflict with either, stop and surface it — update the
   document, don't drift (OPTIMIZER_PHILOSOPHY §0 applies to these docs too).
4. **Decisions get recorded.** Every "Planning Decision" (P-series, §3) that gets
   confirmed or changed during implementation is appended to DECISION_LOG.md.
5. **The optimizer is frozen.** `agents/optimizer.py`, `execution_optimizer.py`,
   policy/constraint/regime services are read-only for this phase unless a
   correctness bug is found — in which case: report it, log it, fix it in an
   isolated commit with its own tests.
6. Dev DB is **PostgreSQL — schema changes go through Alembic** (not SQLite patches).
   `migrate_legacy_data()` covers SQLite mirrors where the existing pattern does.

---

## 1. Current-State Inventory (verified 2026-07-06)

What already exists and is reused as-is. Do not rebuild any of this.

### Data (backend/models/database.py)
| Asset | State | Notes for this phase |
|---|---|---|
| `RecommendationSnapshot` | ✅ | Full run context incl. `projected_allocations_json`, 1:1 with `OptimizerHistory` |
| `UserExecutionDecision` | ✅ | `decision` ∈ APPROVED / REJECTED / PARTIAL_EXECUTION / MANUAL_OVERRIDE; UX.2D structured override columns (`override_type`, `original_symbol`, `replacement_symbol`, `reason_category`) |
| `ShadowPortfolio` / `ShadowPortfolioSnapshot` | ✅ | STATIC_FROZEN keyed to `execution_decision_id`; ACTIVE_MODEL cumulative (4C.6 Option B); SPS already has `recommendation_snapshot_id` |
| `AttributionMetric` | ✅ | BHB selection/allocation/interaction; per-sector part is a known stub |
| `ConfidenceCalibrationRecord`, `RegimeSnapshot`, `BenchmarkPrice` | ✅ | Feed calibration curve, regime tab, counterfactual/benchmark math |
| `Transaction` ledger | ✅ | Sacred; owned by rebuild/validator toolchain — see risk R4 before touching |

### Services
| Asset | State | Reuse |
|---|---|---|
| `decision_memory/` (snapshot_writer, shadow_tracker, attribution, calibration) | ✅ | Shadow creation + valuation + BHB |
| `analytics/attribution_engine.py`, `human_vs_ai.py`, `regime_attribution.py` | ✅ | Extended, not replaced (M5, M6) |
| Timing intelligence (4C.6A–E: timing_periods/performance/score) | ✅ | Feeds timing effect + timing deltas |
| `execution_plan.py`, `optimizer/execution_optimizer.py` | ✅ | Deterministic; plan is a **response-time view** re-derived from stored inputs (verified `main.py:2581, 2665`) |
| `operations_center/muji_translator.py` pattern | ✅ | Template model for verdict composer |
| `snapshot_scheduler.py` (daily 17:45 ICT chain) | ✅ | Grading jobs append to this chain |

### API & Frontend
- Existing analytics endpoints: `/analytics/human-vs-ai`, `/ai-vs-human-timeline`,
  `/shadow-performance`, `/attribution-summary`, `/calibration-history`,
  `/regime-attribution`, shadow CRUD. **Extend these; new endpoints only where no
  owner exists.**
- `/ai-analytics` page = **AI ops telemetry** (model leaderboard, cost, latency,
  tokens, reliability) — see Planning Decision P1.
- Reusable frontend: `PortfolioTabs` segmented pattern, `BackBreadcrumb`,
  `KPICard`, AttributionPanel cards (optimizer page), `DecisionActionPanel`,
  `ExecutionPlanCard` trade-class badges, sector colors.

---

## 2. Gap Analysis — what the UX needs that does not exist

| # | Gap | Consequence if unaddressed |
|---|---|---|
| G1 | **No horizon grading.** Nothing computes/persists 7/30/90/180D per-recommendation outcomes at fixed maturity dates | S1–S3 ledgers and Report Cards have no grades |
| G2 | **Counterfactual coverage is decision-gated.** STATIC_FROZEN shadows are created only when a decision is recorded (`main.py:5178–5204`). Recommendations never acted on have no counterfactual series | "Ignored recommendation" rows (S2, S5, S6) — the heart of opportunity cost — cannot be priced |
| G3 | **No terminal state for undecided recommendations** (no EXPIRED) | Ledger rows stay "pending" forever; acceptance stats silently biased |
| G4 | **No day-0 plan grade.** Plan-quality composite (necessity/funding/turnover/explanation) is not computed or persisted anywhere | S3 section 1, Execution-lens KPIs empty |
| G5 | **No plan-vs-actual execution analysis.** Timing/size/funding/completeness deltas and execution score don't exist; no explicit decision→Transaction linkage | S4 entirely; execution effect in S8 |
| G6 | **No opportunity-cost engine** (incl. the system's own deferrals) | S6 entirely |
| G7 | **Attribution has 3 of 7 effects.** BHB gives selection/allocation/interaction; timing, execution, funding, override effects missing | S8 waterfall incomplete |
| G8 | **No verdict composer** (deterministic TH/EN sentences shared Quant/MUJI) | S1 verdict strip, S9, per-card sentences |
| G9 | **No evaluation frontend.** Hub shell, 9 screens, component kit (MaturityChip, SampleSizeChip, CounterfactualValue, HorizonStrip, AsOfStamp, EffectWaterfall, …) | Everything visible |
| G10 | **No evaluation config.** Min-n thresholds, horizon set, expiry window need a home | Hardcoded constants violate ENGINEERING_PRINCIPLES |

---

## 3. Planning Decisions (P-series)

Resolved here so implementation doesn't stall; each is logged to DECISION_LOG.md when
its milestone ships. If the reviewer disagrees with any, say so before M0.

- **P1 — Route conflict (discovered in planning).** The UX baseline says "evolve
  `/ai-analytics` into the Evaluation hub," but the current page is *operational
  telemetry* (cost/latency/tokens), a different concern than investment evaluation.
  **Decision:** Evaluation hub takes the `/ai-analytics` root and sub-routes per the
  UX; the existing telemetry page moves intact to `/ai-analytics/system`, linked from
  the hub header (not a 7th segment). Rationale: preserves the approved IA; telemetry
  remains one click away; no nav item added.
- **P2 — Recommendation-level counterfactuals (fixes G2).** Extend
  `shadow_tracker.py` with recommendation-keyed STATIC_FROZEN creation
  (`execution_decision_id=NULL`, `recommendation_snapshot_id` set), auto-created in
  the existing post-optimizer background thread (pattern at `main.py:2501`). Every
  recommendation gets a counterfactual series from day 0 regardless of what the human
  does. Deactivate (`is_active=False`) once the 180D grade is issued to bound the
  daily valuation job.
- **P3 — Grades are re-derivable but persisted.** Horizon and plan grades are written
  to a new append-only `recommendation_grades` table. Persistence (not on-the-fly
  computation) is required for immutability ("grades never flicker") and cheap ledger
  queries. Unique `(recommendation_snapshot_id, grade_kind)`; rows never UPDATEd —
  a discovered grading bug is fixed by migration with a DECISION_LOG entry.
- **P4 — EXPIRED semantics (fixes G3).** A snapshot with no decision is EXPIRED when
  **superseded** (a newer snapshot for the same portfolio receives any decision) **or
  14 days old**, whichever first (window configurable). Written by the daily scheduler
  as a `UserExecutionDecision` row with `decision="EXPIRED"` and new column
  `is_system_generated=True`. EXPIRED counts as "ignored" in Human-vs-AI and
  opportunity cost.
- **P5 — Decision→Transaction linkage (fixes half of G5).** Add nullable
  `execution_decision_id` FK to `Transaction`, populated only when a trade is entered
  via the app after an APPROVED/PARTIAL decision. **Metadata-only**: canonicalizer,
  rebuilder, and both validators must ignore it (verified by running their full test
  suites unchanged). No heuristic matching in v1 — unlinked transactions simply leave
  timing/size deltas as "not measurable," shown honestly.
- **P6 — Evaluation is 100% deterministic. Zero AI calls.** Grading, scoring,
  opportunity cost, and verdict sentences are arithmetic + templates (§6 boundary:
  these are exact questions). `verdict_composer.py` follows the `muji_translator`
  template pattern, TH+EN, unit-tested for every branch.
- **P7 — Config home (fixes G10).** New Settings key `evaluation_settings`:
  `{horizons_days: [7,30,90,180], min_n_letter_grade: 8, min_n_win_rate: 5,
  tie_band_pct: 0.3, expiry_days: 14}`. Read through the existing settings service;
  no literals in services.
- **P8 — New endpoints live under `/analytics/evaluation/*`**; existing analytics
  endpoints are extended in place where they already own the data (human-vs-ai,
  shadow-performance, attribution-summary). New endpoints only for objects with no
  current owner: grades ledger, report card, execution ledger/detail, scorecard,
  opportunity cost.

---

## 4. Architecture Constraints & Invariants (must hold in every milestone)

1. **Evaluation only reads upstream.** No code path in `services/evaluation/` may
   mutate `RecommendationSnapshot`, `OptimizerHistory`, `UserExecutionDecision`
   (except the scheduler's EXPIRED writer, which is decision-recording, not
   evaluation), `Transaction`, or any shadow inception data. (PHILOSOPHY §16, Inv. 1–2.)
2. **Append-only grades** (P3). No UPDATE on `recommendation_grades`.
3. **No AI calls anywhere in this phase** (P6). Adding a model call to evaluation is
   a §3 Non-Goal ("maximize AI involvement") — reject the temptation.
4. **Optimizer pipeline untouched** (Working Agreement #5).
5. **Single source of truth for every metric.** Each number is computed in exactly one
   backend service and delivered via API; the frontend never recomputes returns,
   alphas, scores, or verdicts. Quant and MUJI consume the same verdict payload.
6. **Existing formulas are not re-derived.** Period returns come from
   `portfolio_metrics.py` outputs / existing snapshot fields; shadow math stays in
   `shadow_tracker.py`; fee math stays in `broker_fees.py`.
7. **Degraded modes observable.** Every grading job logs skips with reasons (missing
   price, immature horizon, no shadow); every API response carries `as_of` and
   per-section `status: ok|stale|unavailable` so the UI can render amber banners
   instead of silent zeros.
8. **Counterfactual vs realized never conflated in payloads.** Any hypothetical
   figure is delivered in a field explicitly named `counterfactual_*` — the API
   schema enforces what the UX enforces typographically.
9. **`datetime.utcnow()` convention** (DECISION_LOG) for storage; horizon maturity is
   evaluated against snapshot `created_at` dates in UTC; 17:45 ICT scheduling stays
   where it is.

---

## 5. Epics, Milestones, and Order

Dependency graph (backend core first; frontend consumes stabilized APIs; each
milestone independently shippable):

```
M0 groundwork ──► M1 horizon grading ──► M3 aggregation APIs ──► M4 hub + S1–S3
        │                 ▲                      ▲                     │
        └──► M2 plan & execution grading ────────┘                     ▼
                                          M5 HvA + opp-cost + S4–S6 ──► M6 portfolios
                                                                        + attribution
                                                                        + S7–S8 ──► M7 polish
```

---

### M0 — Groundwork: schema, config, route relocation

**Epic:** Foundations. Small, fully reviewable, unblocks everything.

**DB (one Alembic revision):**
- `recommendation_grades` table: `id, workspace_id, recommendation_snapshot_id (FK),
  portfolio_id, grade_kind (PLAN|H7|H30|H90|H180), graded_at, window_start,
  window_end, return_pct, benchmark_return_pct, alpha, max_drawdown_pct,
  directional_correct (bool, nullable), score (float, nullable — plan/exec scores),
  detail_json, created_at` + unique `(recommendation_snapshot_id, grade_kind)`.
- `user_execution_decisions.is_system_generated` (bool, default false) — for EXPIRED.
- `transactions.execution_decision_id` (nullable FK, metadata-only per P5).

**Backend:**
- `evaluation_settings` key + accessor (P7), following the existing settings service
  pattern; GET/PATCH `/settings/evaluation`.
- Skeleton package `services/evaluation/` with module docstrings citing the
  constraints in §4.

**Frontend:**
- Relocate telemetry page to `/ai-analytics/system` (move, don't rewrite); redirect
  `/ai-analytics` → temporary landing that links to System until M4 replaces it.
  Update `Navbar` match arrays for new sub-routes.

**Tests:**
- Alembic upgrade/downgrade round-trip.
- **Full existing ledger suites** (ledger_validator, portfolio_rebuilder,
  verify_snapshots, repair executor — all pass unchanged with the new Transaction
  column present). This is the gate for P5.

**Acceptance criteria:**
- [ ] Migration applies and reverses cleanly on PostgreSQL.
- [ ] All pre-existing test suites pass (known pre-existing failures noted in memory
      excepted and listed in the PR description).
- [ ] Telemetry reachable at `/ai-analytics/system`; no dead links from Ops Center.
- [ ] DECISION_LOG.md entries for P1, P3, P5.

---

### M1 — Horizon Grading Engine (backend)

**Epic:** Recommendation Evaluation core. Fixes G1, G2, G3.

**Backend:**
- `shadow_tracker.py`: add `create_recommendation_shadow(db, snapshot_id)` (P2);
  wire into the post-optimizer background thread beside the ACTIVE_MODEL refresh;
  idempotent (one per snapshot).
- `services/evaluation/horizon_grader.py`:
  `grade_due_recommendations(db, portfolio_id=None)` — for every snapshot whose age ≥
  a configured horizon and which lacks that grade row: read the recommendation
  shadow's SPS series (return, alpha via existing benchmark fields, max drawdown),
  directional correctness per trade from `projected_allocations_json` vs price moves
  (reuse the calibration module's 14-day directional convention where applicable),
  write the grade row. Missing data ⇒ skip with logged reason (constraint §4.7),
  retry next run.
- EXPIRED writer per P4 (same scheduler pass, before grading).
- Shadow deactivation after H180 grade (P2).
- **Backfill command**: one-shot CLI (manage.py subcommand, mirroring
  `verify_snapshots` conventions) that creates recommendation shadows retroactively
  where price history allows and grades all mature horizons for existing snapshots —
  the product must not launch empty for existing users.

**Scheduler:** append `grade_due_recommendations` + EXPIRED writer to the 17:45 ICT
chain in `snapshot_scheduler.py`, after `value_all_active_shadows`.

**Tests (unit, synthetic data):** maturity boundaries (day 29 vs 30), append-only
(second run writes nothing), EXPIRED supersession vs 14-day path, skip-with-reason on
missing prices, deactivation, backfill idempotency.

**Acceptance criteria:**
- [ ] Every new optimizer run yields a recommendation shadow within one scheduler cycle.
- [ ] Grades appear exactly at maturity; re-running the grader is a no-op.
- [ ] Undecided snapshots become EXPIRED per P4 and never regress.
- [ ] Backfill on the dev DB produces grades for historical snapshots (spot-check 3
      against hand-computed returns).

---

### M2 — Plan Grading & Execution Analysis (backend)

**Epic:** Execution Intelligence core. Fixes G4, G5.

**Backend:**
- `services/evaluation/plan_grader.py` — day-0 deterministic composite (0–100) with
  documented sub-scores: **necessity** (share of trades with Required-tier Reason or
  active funding Role), **funding efficiency** (cash released vs funding gap — the
  BH-incident metric), **turnover proportionality**, **explanation completeness**
  (every trade classified + reasoned). Inputs: the stored optimizer result +
  re-derived execution plan (`optimize_execution` on stored inputs — deterministic,
  hence reproducible; assert reproducibility in tests). Weights documented in the
  module docstring and surfaced in `detail_json` (UX `[breakdown ▾]`). Persist as
  `grade_kind=PLAN` from the post-optimizer background thread; backfill via M1 CLI.
- `services/evaluation/execution_analyzer.py` — per decision: **timing delta**
  (recommendation-date price vs linked Transaction fill price, per symbol),
  **size delta** (planned vs executed amounts), **funding fidelity** (planned funding
  sources vs actual sells/cash used), **completeness** (executed fraction of plan;
  PARTIAL warning payload per UX S4b). Composite execution score with documented
  weights. Unlinked/absent transactions ⇒ the affected delta is `null` + reason, and
  the composite marks itself partial — never a fabricated 100.
- Transaction linkage write-path: buy/sell endpoints accept optional
  `execution_decision_id`; `DecisionActionPanel` flow passes it (frontend wiring
  lands in M5, column populated from M2 for API callers).

**Tests:** plan grader on fixture plans (the BH incident as a fixture — must score
poorly on funding efficiency; a clean cash-funded plan scores high); reproducibility
(same stored inputs ⇒ identical grade); execution analyzer deltas incl. null-handling
and PARTIAL; linkage round-trip.

**Acceptance criteria:**
- [ ] New optimizer runs receive a persisted PLAN grade with inspectable breakdown.
- [ ] BH-incident fixture scores reflect the philosophy (funding-efficiency sub-score
      near floor) — this test is the phase's conscience.
- [ ] Execution scores computed for decisions with linked transactions; honest nulls
      otherwise.
- [ ] No write path from either service to any upstream table (constraint §4.1
      verified in review).

---### M3 — Aggregation APIs & Verdict Composer (backend)

**Epic:** The read layer the frontend consumes. Fixes G8; serves S1–S4 data.

**Backend (new, under `/analytics/evaluation/`, all portfolio-scoped, all returning
`as_of` + per-section status):**
- `GET …/scorecard?period=` — three-lens aggregates (belief: hit rate, avg alpha,
  calibration join; execution: avg plan score, funding efficiency, necessity,
  implementation shortfall = ACTIVE_MODEL vs ideal-series delta; outcome: three-
  portfolio returns + benchmark, win rate, net opportunity cost placeholder until M5,
  max drawdowns), verdict payload, recent-grades feed. Min-n gating applied
  server-side (P7): below threshold the field ships as
  `{status:"insufficient_evidence", n}`.
- `GET …/recommendations` (ledger: snapshot summary + decision + HorizonStrip cells
  incl. maturity dates + counterfactual flag) and
  `GET …/recommendations/{snapshot_id}` (Report Card: plan section, decision section,
  grades section, per-trade outcomes, verdict).
- `GET …/execution` and `GET …/execution/{decision_id}` (S4/S4b payloads incl.
  class-segmented acceptance — reuse trade classifications from the backend-owned
  ExecutionPlanCard classification).
- `services/evaluation/verdict_composer.py` (P6): deterministic TH/EN sentence
  builder consuming scorecard/report-card aggregates; single implementation used by
  scorecard, report card, and (M7) MUJI card.

**Tests:** endpoint contract tests on seeded fixtures (empty portfolio ⇒ rung-0
payloads, partial history ⇒ maturity fields, mature ⇒ full); min-n gating; verdict
composer branch coverage (AI ahead / human ahead / tie / insufficient evidence, TH+EN).

**Acceptance criteria:**
- [ ] All payload shapes documented in TypeScript types (`frontend/lib/` types added
      now, even before screens).
- [ ] Cold-start portfolio returns structured empty states, not errors or zeros.
- [ ] No endpoint triggers computation heavier than reads + in-memory aggregation
      (grading work stays in the scheduler).

---

### M4 — Frontend: Hub Shell, Component Kit, Screens S1–S3

**Epic:** Evaluation becomes visible.

**Frontend:**
- Hub shell at `/ai-analytics`: segmented sub-nav (6 segments per UX §2.2, System
  link in header), portfolio picker context, `BackBreadcrumb` wiring.
- Component kit (UX §6), built once, Storybook-style fixture page optional but
  encouraged: `VerdictSentence`, `LensGradeChip`, `HorizonStrip`, `MaturityChip`,
  `SampleSizeChip`, `CounterfactualValue`, `AsOfStamp`, `EvidenceLedger`,
  `DecisionStatusBadge` (reuse decision vocab), `GapAnnotation`.
- **S1 Scorecard** (verdict strip, three lens cards, mini three-portfolio chart from
  existing shadow-performance endpoint, KPI grid, recent grades).
- **S2 Recommendations ledger** and **S3 Report Card**.
- Empty/loading states for these three screens per UX §7–§8 (skeleton geometry,
  rung 0–2 copy).

**Tests:** `tsc` clean; component unit tests for the three tri-state components
(HorizonStrip, MaturityChip, CounterfactualValue) — these encode the design's honesty
rules and must not regress.

**Acceptance criteria:**
- [ ] All three screens render correctly against a cold, a partial, and a mature
      portfolio (manually verified against the backfilled dev DB, screenshots in PR).
- [ ] Counterfactual values visually distinct everywhere they appear; no unlabeled
      returns (each states its baseline).
- [ ] No frontend metric computation beyond formatting (constraint §4.5).
- [ ] Thai-primary labels consistent with existing pages.

---

### M5 — Human vs AI, Opportunity Cost, Execution screens (S4–S6)

**Epic:** The comparison layer. Fixes G6; extends human_vs_ai.

**Backend:**
- Extend `analytics/human_vs_ai.py`: verdicts sourced from grade rows (not ad-hoc
  valuation), segmentation by trade class and by structured override type (UX.2D
  columns), tie band from settings, maturity-aware scoreboard counts.
- `services/evaluation/opportunity_cost.py`: divergence events (REJECTED symbols,
  PARTIAL remainders, overrides, EXPIRED, late entries from timing deltas) priced
  against the recommendation shadow / price series; **plus the system's own deferred
  trades** (re-derived deferrals from `optimize_execution` on stored inputs) priced
  the same way. Output: waterfall rows (signed, sorted), net, maturity flags —
  `counterfactual_*` naming throughout (§4.8).
- `GET …/opportunity-cost`; extend `/analytics/human-vs-ai` +
  `/analytics/ai-vs-human-timeline` responses (additive fields only — existing
  consumers in the optimizer page must keep working; verify call sites per
  ENGINEERING_PRINCIPLES System Integration).
- `DecisionActionPanel` wiring: pass `execution_decision_id` on in-app buy/sell (P5).

**Frontend:** **S4/S4b Execution**, **S5 Human vs AI**, **S6 Opportunity Cost**
(EffectWaterfall component built here, reused in M6; ClassAcceptanceBars;
symmetric-tone copy per UX D14).

**Tests:** opportunity-cost engine on fixtures covering all six divergence types +
system deferral + symmetric signs; human_vs_ai segmentation; additive-compatibility
snapshot test for the extended endpoints.

**Acceptance criteria:**
- [ ] An ignored-BUY, an ignored-SELL-that-helped, and a PARTIAL each produce correct
      signed waterfall rows on the dev DB.
- [ ] System deferral strip renders (the deferred-trade honesty ledger).
- [ ] Existing AttributionPanel/optimizer-page consumers of extended endpoints
      unaffected.
- [ ] Acceptance rates render only class-segmented (no unsegmented total anywhere).

---

### M6 — Three Portfolios & Attribution (S7–S8)

**Epic:** The hero comparison and the "why." Fixes G7.

**Backend:**
- Ideal-portfolio series: derive a friction-free ideal trajectory per period from
  snapshot target weights + `BenchmarkPrice`/price history (new, in
  `services/evaluation/ideal_series.py`; read-only over snapshots). Extend
  `/analytics/shadow-performance` to return the three aligned series + Gap A/B with
  the §12 interpretation key.
- Extend `attribution_engine.py` with the effect waterfall: keep BHB
  selection/allocation/interaction; add **timing effect** (aggregate M2 timing
  deltas), **execution effect** (fees from `period_fees_paid` + completeness cost),
  **funding effect** (funding-fidelity deltas), **override effect** (from M5 per-
  decision deltas). Per-sector BHB keeps its `approx` status flag (known stub —
  surfaced, not hidden).
- Extend `/analytics/attribution-summary` (additive) with waterfall + generated
  sentence.

**Frontend:** **S7 Portfolios** (ThreePortfolioChart as line-set component,
allocation/risk/contribution/drawdown sections), **S8 Attribution** (waterfall +
sector/regime/holding tabs; regime tab reads existing regime-attribution endpoint).

**Tests:** ideal-series determinism + alignment (identical date axes, indexed base);
waterfall effects sum to total within tolerance, `approx` flags present; gap
interpretation strings match §12 readings.

**Acceptance criteria:**
- [ ] Three lines + named gaps render with correct values on dev DB; Gap A/B
      one-line interpretations correct for their sign/magnitude cases.
- [ ] Waterfall reconciles: benchmark + Σeffects = actual (± documented tolerance,
      residual shown as its own labeled row — never silently absorbed).
- [ ] Weak estimates carry `approx` chips end-to-end.

---

### M7 — MUJI Trust Report, Entry Points, Hardening

**Epic:** Integration, cold-start polish, closure.

**Frontend:**
- **S9 MUJI Trust Report** card (verdict composer payload; 3-sentence cap).
- Contextual entry points (UX §2.3): optimizer history detail → Report Card;
  DecisionActionPanel → execution detail; performance page → attribution; Ops Center
  tiles; ExecutionPlanCard → pre-filtered Human vs AI.
- Optimizer-page AttributionPanel → compact summary strip + deep links (UX D12).
- Cold-start ladder pass across all screens (rung copy, dates not "soon"); degraded
  banners bound to per-section status fields; mobile pass per UX §9.

**Backend:** nothing new; fix-ups only.

**Docs (required for phase completion):**
- ARCHITECTURE.md: new tables, services, endpoints, scheduler steps.
- DECISION_LOG.md: any P-series adjustments made along the way.
- Memory/roadmap notes per repo convention.

**Acceptance criteria:**
- [ ] Every entry-point link navigates with correct pre-filter context.
- [ ] MUJI card renders the same verdict as Quant S1 (one payload, two registers).
- [ ] All screens verified on mobile viewport (screenshots in PR).
- [ ] Docs updated; phase invariants (§4) re-checked in a final review pass.

---

## 6. Testing Strategy (cross-cutting)

- **Unit-first, pure-function bias**: grading/scoring/opportunity-cost services take
  plain data in, return plain data out (mirror the `portfolio_metrics.py` contract) —
  ORM only at thin call boundaries. Synthetic fixtures over DB fixtures.
- **The philosophy fixtures**: BH incident (plan grader floor), "do nothing"
  recommendation (graded vs market), good-decision-bad-outcome and
  bad-decision-lucky-outcome cases (three-lens independence visible in payloads).
- **Regression gates**: full ledger toolchain suites at M0 and again at M5 (the two
  milestones that touch `Transaction` semantics); optimizer test suite untouched and
  green at every milestone.
- **Known pre-existing failures** (4 `_consensus_engine` tests; asyncio test-ordering
  fragility) are quarantined context: do not chase, do not worsen, list in PRs.
- **Contract tests** for every extended endpoint (additive-only changes proven by
  before/after payload snapshots).

## 7. Out of Scope (explicit)

- Optimizer, policy, regime, constraint, or execution-optimizer behavior changes.
- Broker integration / real fill or slippage data (S4 fifth-delta slot reserved).
- Any auto-execution or delegation features (§16 future; not this phase).
- CSV/export functionality (UX lists "export" as a permitted verb — deferred; add a
  disabled affordance only if trivial).
- Multi-portfolio / "all portfolios" aggregate views.
- Comparative multi-model evaluation (component built line-set-ready; no product).
- Per-sector benchmark data acquisition (BHB sector tab ships with `approx`).
- Real-time/streaming values anywhere in evaluation (by design, UX D13).
- Historical grade *revision* tooling (grades immutable; corrections = migration).

## 8. Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Shadow-count growth** (one STATIC_FROZEN per recommendation) inflates the 17:45 valuation job | Deactivate after H180 (P2); job already batch-values; measure runtime in M1 and log it (observable) |
| R2 | **Counterfactual pricing gaps** (yfinance lag for Thai SET — known DECISION_LOG issue; delisted symbols) | Grades skip-with-reason and retry; UI shows maturity/unavailable states honestly; never interpolate silently |
| R3 | **Backfill quality** — historical snapshots may predate benchmark coverage or shadow linkage | Backfill CLI reports per-snapshot outcome (graded/skipped+reason); partial history is acceptable and visibly labeled |
| R4 | **Touching `Transaction`** (P5) collides with the sacred ledger toolchain | Column is nullable metadata; full toolchain suites are the M0 gate; canonicalizer explicitly ignores it |
| R5 | **Endpoint extension breaks existing consumers** (optimizer page panels) | Additive-only changes + snapshot contract tests (M5) |
| R6 | **Ideal-series methodology drift** — "friction-free ideal return" must be defined once | Single implementation in `ideal_series.py`, formula documented in module + ARCHITECTURE.md; attribution and Gap A both consume it (Single Source of Truth) |
| R7 | **Timezone/date-boundary bugs** in maturity math (UTC storage vs ICT schedule) | Follow the `datetime.utcnow()` convention; boundary unit tests at day 29/30/31 in M1 |
| R8 | **Verdict tone regressions** (Thai copy drifting from D14 symmetry) | All sentence templates centralized in verdict_composer with branch tests; UX doc §S5 tone rule quoted in the module docstring |
| R9 | **Scope creep toward redesigning analytics pages** | This plan's boundary: existing `/analytics` (portfolio analytics) and telemetry pages are untouched except the P1 relocation |

## 9. Milestone Summary

| M | Deliverable | Layer | Depends on | Status |
|---|---|---|---|---|
| M0 | Schema, config, telemetry relocation | DB + FE plumbing | — | ✅ Shipped 2026-07-06 |
| M1 | Horizon grading engine + EXPIRED + backfill | BE + scheduler | M0 | ✅ Shipped 2026-07-06 |
| M2 | Plan grader + execution analyzer + linkage | BE | M0 | ✅ Shipped 2026-07-06 |
| M3 | Evaluation APIs + verdict composer | BE | M1, M2 | ✅ Shipped 2026-07-06 |
| M4 | Hub shell + component kit + S1–S3 | FE | M3 | ✅ Shipped 2026-07-06 |
| M5 | Human-vs-AI ext. + opportunity cost + S4–S6 | BE + FE | M3, M4 | ✅ Shipped 2026-07-06 |
| M6 | Ideal series + attribution waterfall + S7–S8 | BE + FE | M5 | ✅ Shipped 2026-07-06 |
| M7 | MUJI card + entry points + hardening + docs | FE + docs | M6 | ✅ Shipped 2026-07-07 |

**Phase status: complete.** See DECISION_LOG.md's "AI Evaluation M0"–"AI Evaluation M7" entries for the full record of each milestone's decisions, scope deviations, and verification. Remaining engineering issues (pre-existing, out of this phase's scope) are tracked in DECISION_LOG.md's "Open Engineering Issues" list under "AI Evaluation Progress" — not repeated here to avoid a second copy going stale.
