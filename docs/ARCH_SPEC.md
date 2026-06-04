# Architecture Specification
_Source of truth for system design, subsystem contracts, and implementation details._
_See [ROADMAP.md](ROADMAP.md) for phase history. See [DECISION_LOG.md](DECISION_LOG.md) for design decisions._

---

## Symbol Convention
- **US stocks**: `AAPL`, `GOOGL`, `TSLA`
- **Thai SET**: suffix `.BK` — `SCB.BK`, `PTT.BK`, `KBANK.BK`
- **DR stocks** (Depository Receipts): `AAPL01.BK`, `AMD08.BK` — pattern `^[A-Z]+\d{2}\.BK$`
- Always call `normalize_dr_symbol(symbol)` before yfinance calls; keep original symbol for DB/display
- Frontend uses `encodeURIComponent()` in URL paths

---

## Signal Enum (6 levels)
```
ACCUMULATE  FA strong, TA weak/neutral. Buy gradually via DCA.
BUY         FA strong AND TA positive. valuation_percentile < 92. TA must NOT be bearish.
WATCH       FA positive, TA not ready. valuation_percentile < 75.
HOLD        Mixed or insufficient signals.
REDUCE      TA strongly bearish OR valuation_percentile > 85.
SELL        FA deteriorating OR TA score ≤ −3 OR major negative catalyst.
```
Badge hex colors: ACCUMULATE=#0F6E56, BUY=#27500A, WATCH=#0C447C, HOLD=#444441, REDUCE=#854F0B, SELL=#791F1F

---

## Database Models (`models/database.py`)

| Model | Purpose |
|---|---|
| `Portfolio` | Named portfolio (id, name, strategy_persona) |
| `PortfolioItem` | Holdings (symbol, shares, avg_cost, allow_swap, sector) |
| `Watchlist` | Watchlist symbols (sector stored at add-time) |
| `Transaction` | Full transaction ledger: BUY/SELL/INITIAL_POSITION/DEPOSIT/WITHDRAW/DIVIDEND/INITIAL_CASH/QUANTITY_CORRECTION. `fees` = pre-VAT subtotal; `taxes` = VAT amount. |
| `PortfolioSnapshot` | Daily NAV snapshots with return decomposition columns |
| `AnalysisCache` | Latest signal per symbol (upserted, 12h staleness) |
| `AnalysisHistory` | Append-only analysis log (latency_ms, total_latency_ms) |
| `AgentCache` | Per-agent yfinance cache (tech=15m, news=1h, fa=24h) |
| `OptimizerHistory` | Full optimizer result JSON + per-layer latency |
| `Settings` | Key-value store for all user settings |
| `UserUsage` | Per-call AI token usage + cost + latency_ms |
| `SignalHistory` | Optimizer action log: session_id, symbol, action, signal_type(L1/L2), score_at_signal, price_at_signal, reasoning_snippet (≤200 chars) |
| `RecommendationSnapshot` | Full context of every 3L run: regime, envelope, policy, L1/L2/L3 outputs, consensus, DNA, drift, scores_map. 1:1 with OptimizerHistory. |
| `UserExecutionDecision` | User action on recommendation: APPROVED / REJECTED / PARTIAL_EXECUTION / MANUAL_OVERRIDE |
| `ShadowPortfolio` | Paper portfolio metadata: STATIC_FROZEN or ACTIVE_MODEL |
| `ShadowPortfolioSnapshot` | Daily paper-trading valuations: total_value, returns, benchmark, alpha |
| `AttributionMetric` | BHB alpha attribution: selection_alpha, allocation_alpha, interaction_effect, per-sector breakdown |
| `ConfidenceCalibrationRecord` | AI confidence → outcome calibration + feedback_context_json |
| `RegimeSnapshot` | Daily regime state: trend/vol/drawdown/momentum scores, duration, stability |
| `BenchmarkPrice` | Historical benchmark close prices for shadow/attribution math |

`migrate_legacy_data()` runs at startup for SQLite ALTER TABLE patches. PostgreSQL uses Alembic.

### PortfolioSnapshot columns (full)
```
total_value, cash_balance, equity_value, total_return_pct,
investment_return_pct, net_external_cash_flow,
imported_asset_value,          # INITIAL_POSITION market value in window (3B.9)
manual_adjustment_value,       # QUANTITY_CORRECTION market value in window (3B.9 hotfix)
period_realized_pnl,           # SELL P&L in window (3B.10, transparency only)
period_dividend_income,        # DIVIDEND cash in window (3B.10, transparency only)
period_fees_paid,              # BUY+SELL fees+taxes in window (3B.10)
realized_pnl, unrealized_pnl, benchmark_return_pct, alpha_vs_benchmark
```

### Performance formula (canonical)
```
investment_return_pct =
  (today_nav − prev_nav − net_external_cash_flow − imported_asset_value − manual_adjustment_value)
  / prev_nav × 100

# period_realized_pnl / period_dividend_income / period_fees_paid are TRANSPARENCY ONLY
# They are already embedded in today_nav via cash balances; not added/subtracted here.
```

### Transaction accounting invariants
- `fees` column = pre-VAT subtotal (commission + trading + clearing)
- `taxes` column = VAT amount
- `fees + taxes` = total fee burden
- `period_fees_paid += (tx.fees or 0) + (tx.taxes or 0)` — backward-compat: old rows have taxes=0

---

## Sector System
- **`THAI_SECTOR_MAP`** in `main.py`: static map for 60+ Thai SET stocks (instant, no API)
- **`_get_sector(symbol, fa_cache)`**: DR → FA cache, Thai → THAI_SECTOR_MAP, US → FA cache
- **`_fetch_sector(symbol)`**: async helper used at add-time only
- **Sector stored** in `PortfolioItem.sector` and `Watchlist.sector` at add-time
- GET endpoints read from DB column — never call `_get_sector()` on-the-fly
- `POST /admin/backfill-sectors`: fills missing columns (0.3s throttle between live calls)
- Sector colors: `frontend/lib/sectors.ts`

---

## API Endpoints

### Auth
```
POST /auth/login              { username, password } → { token, username }
```

### Portfolios & Holdings
```
GET    /portfolios
POST   /portfolios                   { name }
DELETE /portfolios/{id}
GET    /portfolios/{id}/holdings
POST   /portfolios/{id}/holdings     { symbol, shares, avg_cost }  → calls execute_initial_position()
DELETE /portfolios/{id}/holdings/{symbol}
PATCH  /portfolios/{id}/holdings/{symbol}/swap-permission   { allow_swap }
GET    /portfolios/{id}/prices
GET    /portfolios/{id}/sector-breakdown
GET    /portfolios/{id}/persona
PATCH  /portfolios/{id}/persona      { persona }
POST   /portfolios/{id}/analyze
POST   /portfolios/{id}/analyze/all
```

### Transactions
```
POST /portfolios/{id}/transactions/buy               { symbol, shares, price_per_share }
POST /portfolios/{id}/transactions/sell              { symbol, shares, price_per_share }
POST /portfolios/{id}/transactions/initial-position  { symbol, shares, price_per_share }
POST /portfolios/{id}/transactions/dividend          { symbol, amount }
POST /portfolios/{id}/transactions/deposit           { amount }
POST /portfolios/{id}/transactions/withdraw          { amount }
POST /portfolios/{id}/transactions/quantity-correction { symbol, shares_delta }
GET  /portfolios/{id}/transactions
```

### Watchlist
```
GET    /watchlist
POST   /watchlist                    { symbol }
DELETE /watchlist/{symbol}
POST   /watchlist/analyze/all
POST   /watchlist/analyze/all/stream  # NDJSON streaming
```

### Stocks & Analysis
```
GET  /stocks/{symbol}
GET  /stocks/{symbol}/chart          ?period=1d&interval=5m
GET  /analyze/{symbol}
GET  /analyze/{symbol}/technical
GET  /analyze/{symbol}/fundamental
GET  /analyze/{symbol}/news
GET  /analyze/{symbol}/consensus
POST /analyze/{symbol}/why-disagree
POST /analyze/{symbol}/opinion       { provider, model }
GET  /analysis/history/{symbol}
DELETE /analysis/history/{symbol}/{id}
```

### Optimizer & Strategy
```
POST /analyze/optimizer              { portfolio_id }
GET  /optimizer/history?portfolio_id={id}
GET  /optimizer/history/{id}
GET  /strategy-profiles
POST /optimizer/decisions
GET  /optimizer/decisions
GET  /optimizer/decisions/{id}
GET  /optimizer/snapshots/{id}
POST /optimizer/{snapshot_id}/decision
```

### Performance & Snapshots
```
GET  /portfolios/{id}/snapshots
GET  /portfolios/{id}/performance
```

### Analytics
```
GET  /analytics/market-regime
GET  /analytics/signals
GET  /analytics/shadow-portfolios
POST /analytics/shadow-portfolios
GET  /analytics/shadow-portfolios/{id}/performance
POST /analytics/shadow-portfolios/{id}/value
GET  /analytics/attribution/{shadow_id}
GET  /analytics/attribution-summary?portfolio_id=X
GET  /analytics/calibration
GET  /analytics/confidence-calibration
GET  /analytics/calibration-history
GET  /analytics/human-vs-ai
GET  /analytics/ai-vs-human-timeline
GET  /analytics/shadow-performance
GET  /analytics/regime-attribution
```

### Stats & Admin
```
GET  /stats/latency
GET  /stats/cost-estimate
POST /admin/backfill-sectors
POST /admin/fix-sectors
POST /admin/recalculate-cost-basis   ?from_date=2026-05-27&dry_run=false
GET  /admin/validate-portfolio/{id}
```

### Settings
```
GET/PATCH  /settings/ai-models
GET/PATCH  /settings/analysis-sources
GET/PATCH  /settings/optimizer-layers
GET/PATCH  /settings/portfolio
GET/PATCH  /settings/sector-limits
GET        /ai-models
```

---

## Caching Strategy
| Layer | TTL | Purpose |
|---|---|---|
| `AgentCache.technical` | 15 min | yfinance price/TA |
| `AgentCache.news` | 1 hour | News articles |
| `AgentCache.fundamental` | 24 hours | FA ratios |
| `AnalysisCache` | 12 hours | AI summary staleness |
| Analyze All | 60 min | Skip recently-analyzed |
| JWT token | 30 days | Auth session |
| Regime detection | 30 min | In-process `_global_` cache key |

---

## Deterministic Scoring (`services/scorer.py`)
All 0–100 scale, computed before AI call.
```
technical_score   : 50=neutral, >65=bullish, <35=bearish
fundamental_score : 50=fairly valued, >70=undervalued, <30=overvalued
news_sentiment    : 50=neutral, >65=positive, <35=negative
risk_score        : higher = more volatile/uncertain
valuation_percentile : PE rank vs batch peers (optimizer only)
    ≥92 → −12 to fundamental_score
    ≥80 → −6 to fundamental_score
```

---

## 3-Layer Optimizer (`agents/optimizer.py`)

### Layer roles and output schemas
| Layer | Role | Default Provider | Output Schema |
|---|---|---|---|
| L1 — Strategist | Swap targets + sector flags | Gemini Flash | `{swaps[], top_buys[], sector_flags[], priority}` |
| L2 — Challenger | Full allocation plan | Claude | `{agrees_with_layer1, disagreements, portfolio_assessment, cash_balance_target, allocations[]}` |
| L3 — Risk Auditor | Concentration risk audit | Claude | `{risk_flags[], safer_choice, final_risk_level, auditor_notes}` |
| Consensus | Pure Python, no AI call | — | See Consensus Strength Matrix below |

**L1 swaps items**: `sell`, `buy`, `score_delta`, `sector`, `type`  
**L2 allocations items**: `symbol`, `current_weight`, `target_weight`, `action`, `allocation_change_percent`, `reason`

### Mathematical alignment (invariants)
- `allocation_change_percent` = Python: `target_weight − current_weight` (never from AI)
- `estimated_amount` = Python: `change_pct / 100 × total_value` (never from AI)
- `pc_map` (real weights from DB) always overrides AI-reported `current_weight`

### Prompt injection order (L1 and L2)
`[ACTIVE OPTIMIZATION POLICY]` → `[MARKET REGIME]` (legacy fallback only) → `[STRATEGY CONTEXT]` → base prompt

### Post-AI enforcement (Python, deterministic)
1. Forced SELL entries applied
2. Locked stocks excluded from swap suggestions
3. Sector cap enforcement (per `EffectiveEnvelope.sector_limits`)
4. Emergency override: freeze all BUY/ACCUMULATE to HOLD when `emergency_override=True`
5. Cash floor: trim largest BUY allocations until `min_cash_pct` satisfied

---

## Consensus Strength Matrix

Computed by `_consensus_engine(l1, l2, l3)` in `agents/optimizer.py` — pure Python, no AI call.

### Intermediate scores
| Score | Range | Formula |
|---|---|---|
| `strategist_alignment_score` | 0–100 | Base 80 (agrees) or 30 (disagrees) − 12/disagreement ± 10 Jaccard |
| `risk_alignment_score` | 0–100 | 92 clean; 55–30 HIGH flags; 12 CRITICAL flag |
| `consensus_strength_score` | 0–100 | 65% × strategist + 35% × risk |

### 7 consensus types (first match wins)
| Type | Trigger | UI color |
|---|---|---|
| `RISK_CONFLICT` | CRITICAL flag OR (HIGH + ≥2 HIGH flags) | Orange/Red |
| `STRATEGIC_CONFLICT` | L2 disagrees AND stratAlign < 40 | Red |
| `NO_ACTION_CONSENSUS` | L2 status=NO_ACTION AND score < 40 | Teal |
| `STRONG_CONSENSUS` | stratAlign ≥ 70 AND riskAlign ≥ 65 | Green |
| `REFINED_CONSENSUS` | L2 agrees AND stratAlign ≥ 50 | Blue |
| `PARTIAL_CONSENSUS` | stratAlign ≥ 35 | Amber |
| `WEAK_CONSENSUS` | fallback (stratAlign < 35) | Gray |

### Governance scoring
Each governance flag = −6 from `consensus_strength_score` (max −20).  
Flags: `POLICY_VIOLATION`, `CONCENTRATION_BREACH`, `OVER_AGGRESSION`, `REGIME_MISMATCH`  
**Exception**: `"turnover"` / `"tier3_efficiency"` flags excluded when Tier 1 relaxation is active.

---

## Strategy Persona System (`services/optimizer/strategy_profiles.py`)

| Persona | Top Priority | Turnover | Aggressiveness |
|---|---|---|---|
| BALANCED | Equal (all 0.20) | 40% | 50% |
| GROWTH | Growth 40% → Momentum 30% | 70% | 75% |
| VALUE | Value 40% → Quality 30% | 20% | 25% |
| DIVIDEND | Dividend 45% → Quality 30% | 15% | 20% |
| MOMENTUM | Momentum 50% → Growth 25% | 90% | 90% |
| PASSIVE | Quality 30% → Value 25% | 10% | 10% |

### Portfolio DNA computation
- `momentum` ← ta_score (0–100)
- `quality` ← fa_score
- `growth` ← revenue_growth if available, else ta/fa composite
- `value` ← inverse P/E (P/E 5→90, P/E 25→58, P/E 50+→10)
- `dividend` ← proxy: P/E < 15 + ROE > 12% bonus

### Style drift
Euclidean distance between normalized DNA (0–1) and persona factor weights. Returns `drift_score` 0–100, `drift_severity` LOW/MEDIUM/HIGH/CRITICAL, `factor_alignment_score`, `rebalance_urgency`.

Always use `valid_persona(raw)` to normalize input. Default = `"BALANCED"`.  
`compute_portfolio_dna()` requires `market_value` on each item — call `_compute_portfolio_weights` first.

---

## Market Regime Detection (`services/analytics/regime_detector.py`)

### 7 regime states
`RISK_ON`, `RISK_OFF`, `SIDEWAYS`, `HIGH_VOLATILITY`, `DEFENSIVE_REGIME`, `TRANSITION_RISK_ON`, `TRANSITION_RISK_OFF`

### Classification algorithm
1. HIGH_VOLATILITY override: `vol_z > 2.0 OR VIX > 30 OR vol_score < 20 OR drawdown_score < 20`
2. Composite = `trend×0.40 + vol×0.25 + drawdown×0.20 + momentum×0.15 − dispersion_penalty`
3. RISK_ON: composite ≥ 68 AND trend ≥ 65 | RISK_OFF: composite ≤ 35 AND trend ≤ 40

### Hard constraints (post-AI Python enforcement)
- BUY/ACCUMULATE target_weight capped at `max_single_position_pct`
- If total deployed > (100 − `min_cash_pct`), trim largest BUY allocations
- Constraints from `_REGIME_CONSTRAINTS[regime]`

Benchmarks: ^GSPC, ^SET.BK, QQQ (optional ^VIX). 30-min in-process cache keyed `_global_`.

---

## Constraint Resolution (`services/optimizer/constraint_resolver.py`)

Merges 4 constraint sources into a single `EffectiveEnvelope`:
- **A) User Preferences** — `max_sector_pct`, per-sector `sector_limits`, persona volatility tolerance
- **B) Regime Policy** — `_REGIME_SECTOR_MULTIPLIERS` applied multiplicatively
- **C) Emergency Overrides** — `EMERGENCY_MAX_SECTOR=25`, `EMERGENCY_MAX_SINGLE_POSITION=15`, `EMERGENCY_MIN_CASH=20`, `EMERGENCY_MAX_TURNOVER=15`
- **D) Absolute System Safety** — `ABSOLUTE_SYSTEM_MAX_SECTOR=70`, `ABSOLUTE_SYSTEM_MAX_SINGLE_POSITION=40`
- Resolution: `effective = min(A, B, C, D)` for upper bounds; `max()` for cash floor

`effective_sector_cap(envelope, sector)` — single call for resolved ceiling.  
Resolver runs before `compute_policy()`; policy engine applies confidence discount on top.

---

## Adaptive Policy Engine (`services/optimizer/policy_engine.py`)

`compute_policy(persona_ctx, regime_ctx, portfolio_data, consensus, max_sector_pct)` → `PolicyEnvelope`

### PolicyEnvelope fields
`hard_constraints`, `soft_factor_tilts`, `deployment_bias`, `risk_budget`, `rebalance_aggressiveness`, `strictness_level`, `emergency_override`, `confidence_discount`, `violations`

### Emergency override triggers
- `vol_z_score ≥ 2.5` — extreme volatility
- `drawdown_score ≤ 15` — severe drawdown
- `HIGH_VOLATILITY` regime at confidence ≥ 65%
- `VOLATILE` stability + confidence < 40%

When emergency: max_new_positions=0, BUY/ACCUMULATE→HOLD, min_cash≥20%, max_position≤15%, aggressiveness≤0.12, strictness=EMERGENCY.

### Confidence discount
0–1 scale based on: regime confidence (50%), stability (35%), consensus strength (15%).  
Raises cash floor (+8%), tightens max position (−15%), reduces turnover ceiling, reduces aggressiveness.

---

## Broker Fee System (`services/broker_fees.py`)

### Thai SET Standard (also DR_STANDARD at same rates)
```
Commission   = Gross × 0.0015
Trading_Fee  = Gross × 0.00006
Clearing_Fee = Gross × 0.00001
VAT          = (Commission + Trading_Fee + Clearing_Fee) × 0.07
Total        ≈ Gross × 0.001680
```

### FeeProfile registry
- `SET_STANDARD`, `DR_STANDARD`, `FREE` built-in
- `resolve_fee_profile(symbol)` — auto-selects DR_STANDARD for `^[A-Z]+\d{2}\.BK$`, else SET_STANDARD
- `calc_fees(gross_amount, profile)` → `FeeBreakdown` with all components
- New profiles registered via `register_profile()` at startup (thread-unsafe, startup-only)

### Cost basis (fee-inclusive)
- BUY: `avg_cost = net_buy_amount / shares` where `net_buy_amount = gross + total_fees_incl_vat`
- Adding to position: `new_avg = (old_shares × old_avg + net_buy_amount) / new_shares`
- SELL P/L: `(sell_price − avg_cost) × shares − fees_incl_vat`

### Admin repair endpoints
- `POST /admin/recalculate-cost-basis?from_date=2026-05-27&dry_run=false` — re-splits fees/taxes columns, replays full cost-basis history, regenerates snapshots from date
- `GET /admin/validate-portfolio/{id}` — 4-check audit: NAV reconciliation, cash ledger, realized P/L, negative shares

---

## Decision Memory & Attribution System

### Services (`services/decision_memory/`)
- `snapshot_writer.py` — `write_recommendation_snapshot()`: auto-called after every optimizer run, idempotent, swallowed on failure
- `shadow_tracker.py` — paper portfolio math: `value_shadow_portfolio()`, `value_all_active_shadows()`, `create_static_frozen_shadow()`, `create_active_model_shadow()`
- `attribution.py` — BHB framework: `compute_attribution()`, idempotent on (shadow_id, period_start, period_end)
- `calibration.py` — `compute_calibration()`: regime stability LIVE; signal accuracy LIVE (14-day minimum holding period, directional evaluation)

### Services (`services/analytics/`)
- `attribution_engine.py` — `compute_portfolio_attribution()`: actual vs shadow returns, max drawdown, regret score
- `human_vs_ai.py` — `compare_human_vs_ai()`: per-decision shadow vs actual, hit rate, return delta, verdict
- `regime_attribution.py` — `compute_regime_attribution()`: per-regime daily return stats, optimizer run stats by regime
- `factor_engine.py` — Institutional factor exposure: Growth/Value/Momentum/Quality/Dividend

### Attribution auto-triggers
- On APPROVED decision: `compute_portfolio_attribution` fires in daemon thread (never blocks HTTP)
- Daily scheduler (17:45 ICT): `value_all_active_shadows` → `compute_portfolio_attribution` per portfolio

---

## Watchlist Analysis Pipeline

`POST /watchlist/analyze/all` and `POST /portfolios/{id}/analyze/all`:
- `asyncio.gather()` across all stale symbols, concurrency capped by `asyncio.Semaphore(10)`
- Each AI call wrapped in `asyncio.wait_for(timeout=10.0)`
- Result: ~32s for 68 stocks
- `_build_fallback_result()` — deterministic fallback via `determine_signal()`; does NOT write to `AnalysisCache`
- Streaming endpoint: `POST /watchlist/analyze/all/stream` — NDJSON, `start → N×progress → complete`

---

## AI Client (`services/ai_client.py`)

```python
call_ai(prompt, provider, model, max_tokens, usage_operation, usage_layer) -> dict
# Returns: {text, latency_ms, input_tokens, output_tokens, provider, model}
```
- Anthropic → anthropic SDK
- All others → OpenAI SDK with `base_url` from `ai-model.json`
- gpt-5/o1/o3/o4: uses `max_completion_tokens` instead of `max_tokens`
- DeepSeek R1 / GLM-Z1: checks `reasoning_content` when `content` is empty
- Always saves to `UserUsage` table (tokens + cost + latency_ms)
- Always use `safe_parse_json()` — never `json.loads()` on AI output

Available providers: anthropic, gemini, openai, deepseek, zhipu, groq

---

## Settings (DB `Settings` table, key-value JSON)
| Key | Default | Description |
|---|---|---|
| `analyze_provider` | anthropic | Provider for single-stock analysis |
| `analyze_model` | claude-sonnet-4-6 | Model for single-stock analysis |
| `optimizer_layers` | all anthropic/claude | Per-layer provider+model config |
| `analysis_sources` | all true | Which agents feed into AI summary |
| `portfolio_settings` | `{max_stocks:12, max_sector_pct:40}` | Optimizer constraints |
| `sector_limits` | Technology:35%, Financial:30%, … | Per-sector allocation caps |

---

## Chart Indicators (`agents/chart_data.py`)
- EMA(20) — orange dashed
- TEMA(9) — cyan dashed
- ZigZag(5%, 10 bars) — pink solid, custom with linear interpolation
- Bollinger Bands(20, 2σ) — gray dashed
- MACD EMA(12,26,9) — line + signal + histogram (sub-panel)
- RSI(14) — purple, 30/70 refs (sub-panel)
- Default period: 1Y/weekly
