# Portfolio Intelligence Platform

## Project Overview
Full-stack web application for analyzing US and Thai SET stocks. Generates 6-level trading signals (ACCUMULATE / BUY / WATCH / HOLD / REDUCE / SELL) via multi-provider AI with Technical Analysis, Fundamental Analysis, and News aggregation. Includes portfolio management, watchlist, a 3-layer AI optimizer with strategy persona & portfolio DNA, sector allocation tracking, multi-timeframe charting, and AI latency/cost statistics.

## Tech Stack
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, @tanstack/react-table v8, recharts
- **Backend**: Python FastAPI, SQLite (dev) / PostgreSQL (prod) via SQLAlchemy + Alembic
- **Data Source**: yfinance (free, no API key)
- **TA Library**: pandas_ta
- **AI**: Multi-provider — Anthropic, Gemini, OpenAI, DeepSeek, ZhiPu, Groq via `services/ai_client.py`
- **Auth**: JWT (python-jose), 30-day expiry — username: `takae` / password: `121226`

## Run Instructions
```bash
# Backend (Windows)
g:\work\ta\stock-analysis\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# DB migrations (PostgreSQL)
cd backend && alembic upgrade head
```

## Project Structure
```
stock-analysis/
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Dashboard
│   │   ├── portfolio/page.tsx        # Portfolio management + side-by-side pie charts
│   │   ├── watchlist/page.tsx        # Watchlist with sector column + filter
│   │   ├── stock/[symbol]/page.tsx   # Stock detail (chart, consensus, history, second opinion)
│   │   ├── optimizer/page.tsx        # 3-layer Portfolio Optimizer + persona selector + DNA/drift cards
│   │   ├── settings/page.tsx         # All settings + Data Management (sector backfill)
│   │   ├── stats/page.tsx            # AI latency + cost statistics
│   │   └── login/page.tsx            # Auth
│   ├── components/
│   │   ├── Navbar.tsx                # Grouped nav: main links + ⚙ Admin dropdown + mobile hamburger
│   │   ├── SignalBadge.tsx           # 6-level signal badge (inline hex colors)
│   │   ├── PortfolioTable.tsx        # Sortable table with sector badge + freshness dots
│   │   ├── PortfolioPieChart.tsx     # Stock allocation pie chart
│   │   ├── SectorPieChart.tsx        # Sector allocation pie chart with limit status
│   │   ├── AnalyzeAllButton.tsx      # Batch analyze (60-min cache)
│   │   ├── ConsensusCard.tsx         # Multi-model consensus + Why Disagree
│   │   ├── StockChart.tsx            # Multi-timeframe chart (EMA20, TEMA9, ZigZag, BB, MACD, RSI)
│   │   ├── AIBadge.tsx               # Provider/model display badge
│   │   ├── PortfolioSummary.tsx      # Portfolio totals row
│   │   └── StockCard.tsx             # Stock summary card
│   └── lib/
│       ├── api.ts                    # All API fetch functions + TypeScript types
│       ├── auth.ts                   # Token storage (localStorage)
│       ├── sectors.ts                # SECTOR_COLORS palette + sectorColor() helper
│       └── PortfolioContext.tsx      # Active portfolio state
│
├── backend/
│   ├── main.py                       # FastAPI app + all route handlers
│   ├── auth.py                       # JWT login endpoint + verify_token middleware
│   ├── ai-model.json                 # Available providers/models config (incl. cost/memo)
│   ├── agents/
│   │   ├── technical.py              # Dual-timeframe TA (short: 1mo/1d, long: 1y/1wk)
│   │   ├── fundamental.py            # FA — P/E, ROE, revenue growth, debt/equity, sector
│   │   ├── news.py                   # News via yfinance .news property
│   │   ├── summary.py                # AI summary → 6-level signal (returns latency_ms)
│   │   ├── optimizer.py              # 3-layer optimizer + sector weight helpers + consensus
│   │   └── chart_data.py             # OHLCV + EMA20, TEMA9, ZigZag, BB, MACD, RSI
│   ├── models/
│   │   └── database.py               # SQLAlchemy models + migrate_legacy_data()
│   ├── migrations/                   # Alembic migration scripts
│   │   └── versions/
│   │       ├── 5551f8b86e30_initial_schema.py
│   │       ├── a1b2c3d4e5f6_add_latency_columns.py
│   │       ├── b2c3d4e5f6a7_add_sector_to_watchlist_and_portfolio.py
│   │       └── l6m7n8o9p0q1_add_strategy_persona.py  # Portfolio.strategy_persona (3B.2)
│   └── services/
│       ├── data_fetcher.py           # yfinance wrapper + normalize_dr_symbol()
│       ├── scorer.py                 # Deterministic 0-100 scoring (no AI)
│       ├── ai_client.py              # call_ai() → dict{text, latency_ms, tokens, ...}
│       ├── json_utils.py             # safe_parse_json() — robust JSON from AI responses
│       ├── optimizer/
│       │   └── strategy_profiles.py  # 6 persona definitions + compute_portfolio_dna() + compute_style_drift()
│       └── analytics/
│           ├── factor_engine.py      # Institutional factor exposure (Growth/Value/Momentum/Quality/Dividend)
│           └── quant_engine.py       # Quantitative metrics + in-process cache
│
└── CLAUDE.MD
```

## Symbol Convention
- **US stocks**: `AAPL`, `GOOGL`, `TSLA`
- **Thai SET**: suffix `.BK` — `SCB.BK`, `PTT.BK`, `KBANK.BK`
- **DR stocks** (Depository Receipts on SET): `AAPL01.BK`, `AMD08.BK` — pattern `[A-Z]+\d{2}\.BK`
- DR stocks are normalized via `normalize_dr_symbol()` before yfinance calls; original symbol kept for DB/display
- Backend resolves `.BK` automatically; frontend uses `encodeURIComponent()` in URLs

## Signal Enum (6 levels)
```
ACCUMULATE  FA strong, TA weak/neutral. Buy gradually via DCA — not all at once.
BUY         FA strong AND TA positive. Top-20% opportunity, valuation_percentile < 92.
            TA must NOT be bearish. Do not assign BUY on FA alone.
WATCH       Good fundamentals, technicals not ready. Wait for better entry.
            valuation_percentile < 75 and FA positive but TA neutral.
HOLD        Mixed or insufficient signals. No strong reason to add or reduce.
REDUCE      Position overextended. Trim allocation.
            TA strongly bearish on holding OR valuation_percentile > 85.
SELL        Exit. FA deteriorating OR TA score ≤ −3 OR major negative catalyst.
```
Signal badge colors: ACCUMULATE=teal (#0F6E56), BUY=green (#27500A), WATCH=blue (#0C447C), HOLD=gray (#444441), REDUCE=amber (#854F0B), SELL=red (#791F1F).

## Database Models (`models/database.py`)
| Model | Purpose |
|---|---|
| `Portfolio` | Named portfolio (id, name, **strategy_persona**) |
| `PortfolioItem` | Holdings (symbol, shares, avg_cost, allow_swap, **sector**) |
| `Watchlist` | Watchlist symbols (**sector** stored at add-time) |
| `AnalysisCache` | Latest signal per symbol (upserted, 12h staleness check) |
| `AnalysisHistory` | Append-only log (includes **latency_ms**, **total_latency_ms**) |
| `AgentCache` | Per-agent yfinance cache (tech=15m, news=1h, fa=24h) |
| `OptimizerHistory` | Full optimizer result JSON + per-layer latency columns |
| `Settings` | Key-value store for all user settings |
| `UserUsage` | Per-call AI token usage + cost + **latency_ms** |
| `SignalHistory` | Append-only optimizer action log: `session_id` (ties rows to one optimizer run / `OptimizerHistory.id`), `symbol`, `action` (BUY/SELL/ACCUMULATE/REDUCE), `signal_type` (L1\|L2), `score_at_signal`, `price_at_signal`, `reasoning_snippet` (≤200 chars) |

`migrate_legacy_data()` runs at startup for SQLite ALTER TABLE patches. PostgreSQL uses Alembic.

## Sector System
- **`THAI_SECTOR_MAP`** in `main.py`: static map for 60+ common Thai SET stocks (instant, no API)
- **`_get_sector(symbol, fa_cache)`**: 3-way logic — DR stocks → FA cache (base ticker data), Thai → THAI_SECTOR_MAP first, US → FA cache
- **`normalize_dr_symbol(symbol)`** in `data_fetcher.py`: `AAPL01.BK → "AAPL"` for yfinance calls
- **`_fetch_sector(symbol)`** in `main.py`: async helper used at add-time — free for map stocks, yfinance for others
- **Sector stored in DB** on `PortfolioItem.sector` and `Watchlist.sector` at add-time
- GET /portfolio and GET /watchlist read sector **directly from DB column** — no on-the-fly computation
- **`POST /admin/backfill-sectors`**: fills missing sector columns with 0.3 s throttle between live calls
- **`POST /portfolios/{id}/sector-breakdown`**: reads from DB column → groups by sector → computes weight% vs limits
- **Sector colors** defined in `frontend/lib/sectors.ts` (Technology=#185FA5, Financial=#0F6E56, Energy=#BA7517, …)

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
GET    /portfolios/{id}/holdings     # returns sector from DB column
POST   /portfolios/{id}/holdings     { symbol, shares, avg_cost }  # fetches+saves sector at add-time
DELETE /portfolios/{id}/holdings/{symbol}
PATCH  /portfolios/{id}/holdings/{symbol}/swap-permission   { allow_swap }
GET    /portfolios/{id}/prices       # lightweight real-time price refresh
GET    /portfolios/{id}/sector-breakdown  # sector allocation vs limits (reads PortfolioItem.sector)
GET    /portfolios/{id}/persona      # returns { persona, profile }
PATCH  /portfolios/{id}/persona      { persona: "GROWTH" } → assigns strategy persona
POST   /portfolios/{id}/analyze      # full analyze (12h cache, skips fresh)
POST   /portfolios/{id}/analyze/all  # stale-only (60-min cache) → { total, analyzed, skipped, results }
```

### Watchlist
```
GET    /watchlist                    # returns sector from DB column
POST   /watchlist                    { symbol }  # fetches+saves sector at add-time
DELETE /watchlist/{symbol}
POST   /watchlist/analyze/all        # stale-only (60-min cache) → same structure
```

### Stocks & Analysis
```
GET  /stocks/{symbol}                # fast path: agent cache + cached summary
GET  /stocks/{symbol}/chart          # OHLCV + EMA20/TEMA9/ZigZag/BB/MACD/RSI
     ?period=1d&interval=5m          # periods: 1d/5d/1mo/3mo/1y/3y
GET  /analyze/{symbol}               # full re-analysis (bypasses 12h cache)
GET  /analyze/{symbol}/technical
GET  /analyze/{symbol}/fundamental
GET  /analyze/{symbol}/news
GET  /analyze/{symbol}/consensus     # last 5 analyses → signal agreement
POST /analyze/{symbol}/why-disagree  # AI explains disagreement
POST /analyze/{symbol}/opinion       { provider, model } → second opinion
GET  /analysis/history/{symbol}      # last 20 history records
DELETE /analysis/history/{symbol}/{id}
```

### Optimizer & Strategy
```
POST /analyze/optimizer              { portfolio_id } → 3-layer result + sector weights + consensus + DNA/drift
GET  /optimizer/history?portfolio_id={id}
GET  /optimizer/history/{id}
GET  /strategy-profiles              # all 6 persona definitions with factor_weights + policy params
```

### Stats & Admin
```
GET  /stats/latency          # avg/min/max/p95 per provider+model (analysis + optimizer)
GET  /stats/cost-estimate    # token usage + estimated cost per model
POST /admin/backfill-sectors # fill missing sector columns for all portfolio + watchlist items
POST /admin/fix-sectors      # patch FA agent_cache JSON entries with resolved sector field
```

### Settings
```
GET/PATCH  /settings/ai-models        { analyze_provider, analyze_model }
GET/PATCH  /settings/analysis-sources { use_ta, use_fa, use_news }
GET/PATCH  /settings/optimizer-layers { layer: "layer1"|"layer2"|"layer3", provider, model }
GET/PATCH  /settings/portfolio        { max_stocks, max_sector_pct }
GET/PATCH  /settings/sector-limits    { limits: { "Technology": 35, ... } }
GET        /ai-models                 # available model config from ai-model.json
```

## Caching Strategy
| Layer | TTL | Purpose |
|---|---|---|
| `AgentCache.technical` | 15 min | yfinance price/TA data |
| `AgentCache.news` | 1 hour | News articles |
| `AgentCache.fundamental` | 24 hours | FA ratios (change quarterly) |
| `AnalysisCache` | 12 hours | AI summary staleness (single-symbol analyze) |
| Analyze All button | 60 min | Skip recently-analyzed symbols |
| JWT token | 30 days | Auth session |

`_fetch_agents(db, symbol, sources)` checks AgentCache per agent type; only fetches stale ones in parallel.
After a cache hit: patches FA cache with sector from THAI_SECTOR_MAP if the field is missing (no API call).

## Deterministic Scoring (`services/scorer.py`)
All 0-100 scale; computed before AI call so AI can use them as objective anchors.
```
technical_score   : 50=neutral, >65=bullish, <35=bearish
fundamental_score : 50=fairly valued, >70=undervalued, <30=overvalued
news_sentiment    : 50=neutral, >65=positive, <35=negative
risk_score        : higher = more volatile/uncertain
valuation_percentile : PE rank vs batch peers (optimizer only)
                       ≥92 → −12 to fundamental_score
                       ≥80 → −6 to fundamental_score
```

## 3-Layer Optimizer (`agents/optimizer.py`)
```
Layer 1 — Strategist   : Main allocation plan (swap_suggestions + watchlist_ranking)
Layer 2 — Challenger   : Independent review — agrees or proposes alternative
Layer 3 — Risk Auditor : Concentration risk flags (LOW/MEDIUM/HIGH/CRITICAL) + safer_choice
Consensus Engine       : Pure Python — no AI call
```
- `run_layered_optimizer(...)` accepts optional `persona_context: dict` — injects strategy mandate into all 3 layer prompts
- Returns `layer1/2/3_latency_ms`, `total_latency_ms`, `current_sector_weights`, `projected_sector_weights`, `sector_warnings`
- Persona fields in result: `target_persona`, `persona_label`, `current_portfolio_dna`, `style_drift_score`, `style_drift_severity`, `factor_alignment_score`, `factor_drift`, `rebalance_urgency`
- Each layer has configurable provider/model (Settings → Optimizer Layers)
- Post-processing enforces: forced SELL entries, locked stock exclusion, sector caps, room cap
- PE percentiles computed batch-wide in `analyze_optimizer` endpoint; injected into `scores_map`
- **Sector Impact panel** in optimizer result shows before/after sector weights vs limits

## Strategy Persona System (`services/optimizer/strategy_profiles.py`)

**6 personas** stored per portfolio in `Portfolio.strategy_persona` column:

| Persona | Top Factor Priority | Turnover | Aggressiveness |
|---|---|---|---|
| BALANCED | Equal weight (all 0.20) | 40% | 50% |
| GROWTH | Growth 40% → Momentum 30% | 70% | 75% |
| VALUE | Value 40% → Quality 30% | 20% | 25% |
| DIVIDEND | Dividend 45% → Quality 30% | 15% | 20% |
| MOMENTUM | Momentum 50% → Growth 25% | 90% | 90% |
| PASSIVE | Quality 30% → Value 25% | 10% | 10% |

**`compute_portfolio_dna(portfolio_data)`** — lightweight factor exposure from optimizer scores:
- `momentum` ← `ta_score` (already 0–100)
- `quality` ← `fa_score`
- `growth` ← `revenue_growth` (if available) else ta/fa composite
- `value` ← inverse P/E (P/E 5→90, P/E 25→58, P/E 50+→10)
- `dividend` ← proxy from P/E < 15 + ROE > 12% bonus

**`compute_style_drift(dna, persona)`** — Euclidean distance between normalized DNA and target factor weights. Returns `drift_score` (0–100), `drift_severity` (LOW/MEDIUM/HIGH/CRITICAL), `factor_alignment_score`, `rebalance_urgency`.

**Prompt injection** — `persona_context` prepends a `[STRATEGY CONTEXT]` block to L1 and L2 prompts with:
- Target persona label + description
- Current DNA display (sorted by exposure)
- Style drift severity + score
- Factor priority order (`VALUE > QUALITY > GROWTH > DIVIDEND > MOMENTUM`)
- Turnover tolerance + rebalance urgency
- Explicit mandate: all proposed changes must increase the top-priority factor alignment

**Frontend (`optimizer/page.tsx`):**
- `PersonaSelector` — dropdown in controls row; saves immediately via PATCH on change
- `PortfolioDNACard` — factor bars with current (colored) vs target (gray marker) per factor
- `StyleDriftCard` — drift score, alignment score, urgency badge, top misaligned factors with pp delta bars
- Both cards shown in a 2-col grid above the layer sections when DNA is present in result

## AI Client (`services/ai_client.py`)
```python
call_ai(prompt, provider, model, max_tokens, usage_operation, usage_layer) -> dict
# Returns: {"text": str, "latency_ms": int, "input_tokens": int, "output_tokens": int, "provider": str, "model": str}
```
- Anthropic → anthropic SDK
- All others → OpenAI SDK with `base_url` from `ai-model.json`
- gpt-5/o1/o3/o4 models automatically use `max_completion_tokens` instead of `max_tokens`
- Fallback: checks `reasoning_content` when `content` is empty (DeepSeek R1, GLM-Z1)
- Every call saves tokens + cost + `latency_ms` to `UserUsage` table
- `safe_parse_json()` in `services/json_utils.py` — handles fenced/prose-wrapped JSON from any model

Available providers: anthropic, gemini, openai, deepseek, zhipu, groq (configured in `ai-model.json`)

## Latency & Cost Tracking
- `call_ai()` measures wall-clock latency per API call and saves to `UserUsage.latency_ms`
- `analyze_summary()` returns `latency_ms` in its result dict
- `_run_full_analysis_async()` measures `total_latency_ms` (TA+FA+News+AI) and saves to `AnalysisHistory`
- `run_layered_optimizer()` captures per-layer latency and saves to `OptimizerHistory`
- `GET /stats/latency`: aggregates avg/min/max/p95 from `UserUsage` grouped by provider+model
- `GET /stats/cost-estimate`: sums token counts + costs from `UserUsage` per model

## Settings (stored in DB `Settings` table as key-value JSON)
| Key | Default | Description |
|---|---|---|
| `analyze_provider` | anthropic | Provider for single-stock analysis |
| `analyze_model` | claude-sonnet-4-6 | Model for single-stock analysis |
| `optimizer_layers` | all anthropic/claude | Per-layer provider+model config |
| `analysis_sources` | all true | Which agents feed into AI summary |
| `portfolio_settings` | `{max_stocks:12, max_sector_pct:40}` | Optimizer portfolio constraints |
| `sector_limits` | Technology:35%, Financial:30%, … | Per-sector allocation caps |

## Confidence Capping
- All 3 sources available → max `high`
- 2 sources → max `medium`
- 1 source → max `low`

## Chart Indicators (`agents/chart_data.py`)
- EMA(20) — orange dashed
- TEMA(9) — cyan dashed (triple EMA, more responsive)
- ZigZag(5%, 10 bars) — pink solid, custom implementation with linear interpolation between pivots
- Bollinger Bands(20, 2σ) — gray dashed
- MACD EMA(12, 26, 9) close — line + signal + histogram (sub-panel)
- RSI(14) — purple line with 30/70 reference lines (sub-panel)
- Default period: 1Y/weekly

## Coding Rules
- **Python**: type hints on all functions; async FastAPI handlers; Pydantic for request bodies
- **Error handling**: if yfinance returns empty data → `{ "error": "..." }` — never crash
- **Dates**: use `datetime.utcnow().isoformat() + "Z"` for consistent ISO strings (NOT `datetime.now(timezone.utc)` — that appends `+00:00Z` which is invalid)
- **JSON from AI**: always use `safe_parse_json()` — never `json.loads()` directly on AI response
- **Frontend**: all pages are Client Components (`"use client"`); use `dynamic()` with `ssr:false` for recharts
- **Naming**: snake_case Python, camelCase TypeScript, kebab-case file names
- **DR symbols**: always call `normalize_dr_symbol(symbol)` before any yfinance `ticker.info` / `fetch_info` call in agents; keep original symbol for DB storage
- **Sector in GET endpoints**: read from `item.sector` DB column — do NOT call `_get_sector()` on-the-fly in list_holdings / list_watchlist / sector-breakdown
- **Alembic**: add new columns to both `migrate_legacy_data()` (SQLite) AND a new migration file in `migrations/versions/`
- **Strategy persona**: always use `valid_persona(raw)` to normalise input before storing; default is `"BALANCED"`; `compute_portfolio_dna()` requires `market_value` on each item (call `_compute_portfolio_weights` first)

## Environment Variables
```
# backend/.env
ANTHROPIC_API_KEY=your_key
GEMINI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
OPENAI_API_KEY=your_key
OPENAI_API_KEY=your_key
DATABASE_URL=sqlite:///./stocks.db   # or postgresql://user:pass@host/db

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Known Limitations
- yfinance Thai stock (`.BK`) fundamental data often incomplete — handled gracefully
- yfinance news limited to ~10 recent articles per symbol
- ZhiPu/DeepSeek reasoning models return output in `reasoning_content`, not `content` — handled in `ai_client.py`
- Optimizer runs 3 sequential AI calls — expect 30–60s per run
- Sector for DR/US stocks requires FA analysis to have run at least once; shows "Other" until then (use backfill endpoint)
- PostgreSQL GroupBy: ORDER BY must use `func.sum()` not bare column — already fixed in model cost report

## Data Pipeline & Integration Notes

### Yahoo Finance Price Lag — Thai SET Stocks

**Issue:** Yahoo Finance has an inherent **~15–20 minute delay** for Thai SET prices (`.BK` symbols) after the official exchange close. Prices retrieved immediately at or just after 16:30 ICT (market close) may still reflect the last automated auction price rather than the final ATC (At-The-Close) price published by the SET.

**Observed example:** `KBANK.BK` retrieved at 16:35 ICT showed `196.5` via yfinance while the official ATC settled at `197.0` — a 0.25% discrepancy that compounds across a portfolio snapshot.

**Impact:** Portfolio snapshots, P&L calculations, and optimizer weight inputs that are triggered immediately at market close will contain stale prices, causing incorrect allocation percentages and estimated amounts.

**Operational fix (implemented):** The APScheduler cron job in `backend/services/snapshot_scheduler.py` is configured to fire at **17:45 ICT** (Mon–Fri) — 15 minutes after the SET closes at 16:30 — giving Yahoo Finance time to publish final ATC settlement prices before the snapshot is written. This timing must not be moved earlier. Applies to:
- The automated daily snapshot job (APScheduler `daily_portfolio_snapshot`)
- Manual "Analyze All" runs on the portfolio/watchlist pages
- Optimizer runs that read `current_price` for weight calculations
- Any ad-hoc or backfill snapshot scripts

**Long-term solution (backlog):** Replace yfinance `.BK` close prices with a direct SET data feed or a delayed official price source that guarantees ATC settlement prices before the snapshot is taken.

## Claude Code Session Tips
- Run /compact when context exceeds 20%
- Always read CLAUDE.MD at start of new session
- Key files: `backend/main.py`, `backend/agents/optimizer.py`, `backend/agents/summary.py`, `frontend/lib/api.ts`
- DB migrations: add columns to both `migrate_legacy_data()` in `models/database.py` AND a new Alembic migration file
- Sector source of truth: `PortfolioItem.sector` / `Watchlist.sector` DB columns — populated at add-time
- When adding a new signal level: update `_VALID_SIGNALS` in summary.py, `SignalBadge.tsx`, api.ts union type, and all AI prompts

---

## CURRENT ARCHITECTURE STATE
_Last updated: 2026-05-24. Update this section at the start of each new session._

### Phase 3B.4 — Adaptive Optimizer Policy Engine ✅ SHIPPED 2026-05-24

The optimizer now operates inside a **deterministic, institutional-grade Policy Engine** that synthesizes Strategy Persona + Market Regime + Portfolio Risk + Confidence State into a single unified governance layer above all AI agents.

**What was built:**
- `services/optimizer/policy_engine.py` — pure Python `compute_policy(persona_ctx, regime_ctx, portfolio_data, consensus, max_sector_pct)` → `PolicyEnvelope` dataclass with `hard_constraints`, `soft_factor_tilts`, `deployment_bias`, `risk_budget`, `rebalance_aggressiveness`, `strictness_level`, `emergency_override`, `confidence_discount`, `violations`.
- `build_policy_prompt_block(envelope)` — generates `[ACTIVE OPTIMIZATION POLICY — MANDATORY GOVERNANCE]` block injected into L1/L2/L3 prompts.
- `compute_policy_alignment_score(final_allocations, envelope, total_value)` → `(policy_alignment_score, regime_compliance_score, risk_governance_score, governance_flags)`.
- `envelope_to_dict(envelope)` — JSON-serializable dict including pre-built `prompt_block`.
- `agents/optimizer.py` — `run_layered_optimizer` gains `policy_context: dict | None` parameter; policy block injected into all 3 prompt builders; post-AI constraint enforcement now uses `policy_context.hard_constraints` (with legacy regime fallback when no policy_context); governance scoring added to `consensus` dict after constraint enforcement.
- `_make_envelope_from_dict(d)` helper reconstructs `PolicyEnvelope` from serialized dict for scoring.
- `main.py` — `analyze_optimizer` builds `policy_ctx` via `compute_policy()` immediately after persona + regime detection; `policy_ctx` passed to `run_layered_optimizer`; `active_policy` (sans `prompt_block`) surfaced in API result.
- `frontend/lib/api.ts` — `DeploymentBias`, `StrictnessLevel`, `PolicyHardConstraints`, `ActivePolicy` types; `OptimizerResult.active_policy` field; `OptimizerConsensus` gains `policy_alignment_score`, `regime_compliance_score`, `risk_governance_score`, `governance_flags`.
- `frontend/components/ActivePolicyEnvelopeCard.tsx` — color-coded deployment mode badge, strictness badge, emergency banner, hard constraints grid, risk budget bar, factor tilt bars, governance score bars, governance flags, portfolio violations, confidence discount note, policy narrative.
- `frontend/app/optimizer/page.tsx` — `ActivePolicyEnvelopeCard` rendered inside `ResultPanel` between `MarketRegimeCard` and Persona DNA cards.
- `scripts/verify_adaptive_optimizer.py` — 4 scenario simulations (Growth+RISK_ON, Growth+RISK_OFF, Dividend+HIGH_VOL emergency, Momentum+TRANSITION); 33/33 checks pass.

**Emergency override logic:**
- `vol_z_score ≥ 2.5` → emergency (extreme volatility)
- `drawdown_score ≤ 15` → emergency (severe drawdown)
- `HIGH_VOLATILITY` regime at confidence ≥ 65% → emergency (confirmed crisis)
- `VOLATILE` stability + confidence < 40% → emergency (unstable transition)

When emergency: `max_new_positions = 0`, all BUY/ACCUMULATE frozen to HOLD in Python, `min_cash ≥ 20%`, `max_position ≤ 15%`, aggressiveness ≤ 0.12, strictness = EMERGENCY.

**Dynamic scaling (confidence discount):**
Discount 0–1 based on: regime confidence (50% weight), stability (35%), consensus strength (15%). Discount raises cash floor (up to +8%), tightens max position (-15%), reduces turnover ceiling, reduces rebalance aggressiveness.

**Prompt injection order (L1 and L2):** `[ACTIVE OPTIMIZATION POLICY]` → `[MARKET REGIME]` (legacy, only when no policy block) → `[STRATEGY CONTEXT]` → base prompt.

**L3 policy note:** Adds policy compliance check instructions (cash mandate, max position, deployment mode) to L3 auditor prompt. Flags `POLICY_VIOLATION`, `CONCENTRATION_BREACH`, `OVER_AGGRESSION`, `REGIME_MISMATCH` for L3 to surface.

**Governance flags (post-AI, Python-computed):**
- `POLICY_VIOLATION` — cash below mandate or turnover exceeds ceiling
- `CONCENTRATION_BREACH` — position exceeds max_single_position_pct
- `OVER_AGGRESSION` — BUY allocations in DEFENSIVE/PRESERVATION mode
- `REGIME_MISMATCH` — new allocations during EMERGENCY override

Each governance flag penalty: −6 from `consensus_strength_score` (max −20 total).

**Backward compatibility:** `policy_context=None` leaves all existing behavior (prompt, enforcement, consensus) unchanged. Historical optimizer results without `active_policy` display normally.

### Phase 3B.3 — Market Regime Detection & Adaptive Portfolio Intelligence ✅ SHIPPED 2026-05-24

The optimizer is now **market-regime-aware** — it detects the current macro environment and adapts allocation behavior dynamically.

**What was built:**
- `services/analytics/regime_detector.py` — multi-signal engine using ^GSPC/^SET.BK/QQQ benchmark data. 7 regime states: `RISK_ON`, `RISK_OFF`, `SIDEWAYS`, `HIGH_VOLATILITY`, `DEFENSIVE_REGIME`, `TRANSITION_RISK_ON`, `TRANSITION_RISK_OFF`. Signals: EMA20/50 alignment, rolling vol z-score (20D vs 90D), max drawdown (30D rolling), momentum persistence, cross-benchmark return dispersion, optional ^VIX. 30-min in-process cache keyed `_global_`.
- `models/database.py` → `RegimeSnapshot` model — daily snapshots with trend/vol/drawdown/momentum scores, duration, stability, signals JSON.
- `migrations/versions/m7n8o9p0q1r2_add_regime_snapshots.py` — Alembic migration; SQLite handled via `migrate_legacy_data()`.
- `GET /analytics/market-regime` — returns active regime, confidence, all signal scores, duration, previous regime, transition stability, warnings, per-benchmark breakdown, 30-day history, hard allocation constraints.
- `run_layered_optimizer(..., regime_context)` — injects `[MARKET REGIME — MANDATORY ALLOCATION CONTEXT]` block into L1 and L2 prompts. Post-AI hard constraints applied in Python: caps BUY/ACCUMULATE target_weight at `max_single_position_pct`, enforces `min_cash_pct` by trimming largest BUY allocations.
- `analyze_optimizer` endpoint: calls `detect_regime()` before `run_layered_optimizer()`, surfaces compact `market_regime` dict in result (regime, confidence_pct, narrative, transition_warnings).
- `frontend/components/MarketRegimeCard.tsx` — color-coded regime badge, confidence meter (5-bar), 4 signal score bars, meta row (duration, prev regime, stability, VIX), 30-day history dot-trail, transition warnings. `compact` prop for inline use.
- `frontend/lib/api.ts` — `MarketRegime`, `RegimeState`, `RegimeConstraints`, `RegimeHistoryPoint`, `BenchmarkSignal` types; `getMarketRegime()`; `OptimizerResult.market_regime` field added.
- `optimizer/page.tsx` — `MarketRegimeCard` rendered inside `ResultPanel` between PortfolioMetricsBar and PersonaDNA cards.
- `scripts/seed_regime_scenarios.py` — 5 synthetic scenarios: bull (RISK_ON), crash (TRANSITION→HIGH_VOL→RISK_OFF), sideways chop, vol spike, defensive recession. `--scenario`, `--days`, `--clear` flags.

**Hard constraint logic (Python, post-AI):**
- Regime constraints from `_REGIME_CONSTRAINTS[regime]`: `min_cash_pct`, `max_single_position_pct`, `suppress_speculative`, etc.
- BUY/ACCUMULATE allocations capped at `max_single_position_pct`; surplus redistributed to implicit cash
- If total deployed > (100 - `min_cash_pct`), largest BUY allocations trimmed until cash floor satisfied

**Regime classification algorithm:**
- HIGH_VOLATILITY overrides all if: vol_z > 2.0 OR VIX > 30 OR vol_score < 20 OR drawdown_score < 20
- Composite = trend×0.40 + vol×0.25 + drawdown×0.20 + momentum×0.15 − dispersion_penalty
- RISK_ON: composite ≥ 68 AND trend ≥ 65; RISK_OFF: composite ≤ 35 AND trend ≤ 40; etc.
- Confidence = 0.40–0.95 based on distance from 50-neutral

**Backward compatibility:** `regime_context=None` leaves prompts and constraints unchanged.

### Phase 3B.2 — Strategy Persona & Policy-Driven Optimization ✅ SHIPPED 2026-05-23

The optimizer is now a **strategy-aware portfolio intelligence engine** driven by explicit investment philosophy.

**What was built:**
- `services/optimizer/strategy_profiles.py` — 6 persona profiles (BALANCED/GROWTH/VALUE/DIVIDEND/MOMENTUM/PASSIVE), `compute_portfolio_dna()`, `compute_style_drift()`, `build_persona_context()`
- `Portfolio.strategy_persona` column (TEXT, default `'BALANCED'`) — Alembic migration `l6m7n8o9p0q1` + SQLite `migrate_legacy_data()` patch
- `GET /strategy-profiles`, `GET /portfolios/{id}/persona`, `PATCH /portfolios/{id}/persona` endpoints
- `run_layered_optimizer(..., persona_context)` — injects `[STRATEGY CONTEXT]` block into L1, L2, L3 prompts; result carries `target_persona`, `current_portfolio_dna`, `style_drift_score`, `style_drift_severity`, `factor_alignment_score`, `factor_drift`, `rebalance_urgency`
- `analyze_optimizer` endpoint computes DNA → drift → persona_context before calling optimizer; uses `_compute_portfolio_weights` (imported locally) to get `market_value` for weighted averaging
- Frontend: `PersonaSelector`, `PortfolioDNACard`, `StyleDriftCard` in `optimizer/page.tsx`; `StrategyPersona`, `PortfolioDNA`, `DriftSeverity` types + `listStrategyProfiles`, `getPortfolioPersona`, `updatePortfolioPersona` in `api.ts`

**Key design decisions:**
- DNA computation is **lightweight** — uses `ta_score`, `fa_score`, `pe_ratio`, `roe`, `revenue_growth` already in `scores_map`; no extra yfinance calls
- Drift is a **Euclidean distance** between normalized DNA (0–1) and persona factor weights (0–1 fractions), giving `drift_score` 0–100
- Persona saved **per-portfolio** in DB — each portfolio can have a different strategy philosophy
- Backward compat: `persona_context=None` leaves all 3 prompts unchanged (no strategy block injected)

### Watchlist Analysis Pipeline — Optimized (as-built)

The `POST /watchlist/analyze/all` and `POST /portfolios/{id}/analyze/all` endpoints were fully overhauled from sequential to concurrent execution.

**Before:** sequential `for` loop + `asyncio.sleep(random.uniform(1.0, 2.0))` between stocks → ~4 minutes for 68 stocks (avg 3.8 s/stock, max 62.6 s).

**After:** `asyncio.gather()` across all stale symbols, concurrency capped by `asyncio.Semaphore(10)`, each AI call wrapped in `asyncio.wait_for(timeout=10.0)` → **~32 seconds for 68 stocks**.

**Key implementation details (`backend/main.py`):**
- `_ANALYZE_SEMAPHORE = asyncio.Semaphore(10)` — initialized in `lifespan`, shared across all requests
- `_analyze_one_concurrent(ws, sym, s, src)` — per-stock worker: opens its own `SessionLocal()`, fetches agents, calls AI with 10 s timeout, falls back gracefully on `TimeoutError` or any exception
- `_build_fallback_result(...)` — deterministic fallback using `determine_signal(ta_short, ta_long, fa_score)`; sets `ai_fallback_used: True` in the response; does NOT write to `AnalysisCache` (next run will retry AI)
- `_ndjson(obj)` — serializes a dict to a newline-terminated JSON string for the streaming endpoint
- `POST /watchlist/analyze/all/stream` — `StreamingResponse(application/x-ndjson)` endpoint; emits `start` → N×`progress` → `complete` events via `asyncio.Queue` as stocks finish in completion order
- `AnalyzeAllButton.tsx` — watchlist path streams via `analyzeWatchlistStream()` async generator, showing live `"17/68 analyzed…"` progress; done message includes fallback count when applicable

### Optimizer Layer Architecture (as-built) ✅ FULLY FIXED 2026-05-22

The optimizer has been refactored from a "swap engine" into a **3-layer Capital Allocation Engine**. Each layer has a distinct role and output schema:

| Layer | Role | Provider | Output Schema |
|---|---|---|---|
| L1 — Strategist | Swap targets + sector flags | Gemini Flash (configurable) | `{swaps[], top_buys[], sector_flags[], priority}` |
| L2 — Challenger | Full allocation plan + critique | Claude (configurable) | `{agrees_with_layer1, disagreements, portfolio_assessment, cash_balance_target, allocations[]}` |
| L3 — Risk Auditor | Concentration risk audit | Claude (configurable) | `{risk_flags[], safer_choice, final_risk_level, auditor_notes}` |
| Consensus | Pure Python — no AI call | — | `{consensus_type, consensus_strength_score, strategist_alignment_score, risk_alignment_score, disagreement_reasons, refinement_summary, …legacy fields}` |

**L1 output fields** (`swaps` array items): `sell`, `buy`, `score_delta`, `sector`, `type`
**L2 output fields** (`allocations` array items): `symbol`, `current_weight`, `target_weight`, `action`, `allocation_change_percent`, `reason`

**L1 Strategist prompt — active mandate (2026-05-22, persona-aware 2026-05-23):**
- Signature: `_layer1_prompt(c_pc, c_wc, sell_forced, swap_eligible, max_sector_pct, sector_limits, max_stocks, current_count, persona_context=None)`
- Role framing changed from passive "DIRECTOR" to active "STRATEGIST" — biased toward finding improvements
- **5-point evaluation mandate**: before deciding, must check (1) sector concentration, (2) watchlist BUY/ACCUMULATE candidates, (3) overweight positions >25%, (4) low-score swap-eligible holdings, (5) 2–5% shift opportunities
- **Prefers incremental actions**: REDUCE/ACCUMULATE over full SELL/BUY; explicitly instructs that small shifts (2–5%) are meaningful
- `priority="no_action"` is only valid when **all 5 checks** show no meaningful improvement
- Schema type enum extended: `"SELL|SWAP|REDUCE"` — one-sided partial actions (sell=null or buy=null) are encouraged
- `_normalize_l1_swaps()` converts raw L1 compact-key dicts (`sell`/`buy`) to full `swap_suggestions` format (`sell_symbol`/`buy_symbol`)

**Mathematical alignment — fully verified:**
- `allocation_change_percent` always computed by Python (`target_weight - current_weight`), never from AI
- `estimated_amount` always computed by Python (`change_pct / 100 * total_value`), never from AI
- `pc_map` (real portfolio weights from DB) always overrides AI-reported `current_weight`

### Consensus Strength Matrix ✅ SHIPPED 2026-05-22

Replaces the old binary `agrees: bool` with a **7-type Consensus Strength Matrix** computed in pure Python by `_consensus_engine(l1, l2, l3)` in `agents/optimizer.py` — no extra AI call.

#### How the scores are computed first

Three intermediate scores feed the type classification:

| Score | Range | How it's calculated |
|---|---|---|
| `strategist_alignment_score` | 0–100 | Base 80 (L2 agrees) or 30 (disagrees) − 12 per disagreement + ±10 Jaccard overlap of buy/sell symbols |
| `risk_alignment_score` | 0–100 | 92 → clean; 55–30 → HIGH flags present; 12 → CRITICAL flag |
| `consensus_strength_score` | 0–100 | 65% × strategist + 35% × risk |

#### The 7 types — evaluated top to bottom, first match wins

| # | Type | What it means | Trigger condition | UI color |
|---|---|---|---|---|
| 1 | `RISK_CONFLICT` | L3 found a serious concentration risk — act with caution | CRITICAL risk flag OR (final_risk=HIGH + ≥2 HIGH flags) | Orange/Red |
| 2 | `STRATEGIC_CONFLICT` | L1 and L2 fundamentally disagree on what to do | L2 disagrees **and** stratAlign < 40 | Red |
| 3 | `NO_ACTION_CONSENSUS` | All three layers agree: portfolio is fine, no trade needed | L2 status=NO\_ACTION **and** score < 40 **and** no critical risk | Teal |
| 4 | `STRONG_CONSENSUS` | All layers aligned — high confidence signal | stratAlign ≥ 70 **and** riskAlign ≥ 65 | Green |
| 5 | `REFINED_CONSENSUS` | L2 agrees with L1 but adds nuance/refinement | L2 agrees **and** stratAlign ≥ 50 | Blue |
| 6 | `PARTIAL_CONSENSUS` | Moderate agreement — consider the recommendations but stay alert | stratAlign ≥ 35 | Amber |
| 7 | `WEAK_CONSENSUS` | Layers diverge — treat output as exploratory only | stratAlign < 35 (fallback) | Gray |

> Risk conflicts (1) and strategic conflicts (2) are checked before positive consensus types so dangerous signals are never buried under a "STRONG" label.

#### Output fields added to the consensus dict

```python
{
    # New fields
    "consensus_type":             "STRONG_CONSENSUS|REFINED_CONSENSUS|PARTIAL_CONSENSUS|"
                                  "WEAK_CONSENSUS|RISK_CONFLICT|STRATEGIC_CONFLICT|NO_ACTION_CONSENSUS",
    "consensus_strength_score":   0-100,          # overall confidence gauge
    "strategist_alignment_score": 0-100,          # L1 vs L2 plan agreement
    "risk_alignment_score":       0-100,          # L3 risk severity
    "disagreement_reasons":       ["…"],          # forwarded from L2.disagreements
    "refinement_summary":         "…",            # one human-readable explainability sentence

    # Legacy fields — preserved for backward compatibility
    "agrees": bool,
    "consensus_decision": "REBALANCE|NO_ACTION|REVIEW",
    "confidence": "high|medium|low",
    "recommended": "layer1|layer2|neither|no_action|fallback",
    "final_risk_level": "low|medium|high",
    "risk_flag_count": int,
    "recommended_action": str,
}
```

**Backward compatibility:** `ConsensusSection` in `optimizer/page.tsx` detects missing `consensus_type` and renders the old 4-cell agree/disagree grid for historical rows — no data migration needed.

**Frontend `ConsensusSection` (new path):**
colored type badge → `consensus_strength_score` gauge → `strategist_alignment_score` + `risk_alignment_score` sub-bars → tinted `refinement_summary` → `disagreement_reasons` list → stats grid → recommended action footer.

**TypeScript (`frontend/lib/api.ts`):** `ConsensusType` union exported; `OptimizerConsensus` extended with 6 new optional fields.

### Signal History Pipeline ✅ SHIPPED 2026-05-22

Every optimizer run that produces actionable allocations (BUY/SELL/ACCUMULATE/REDUCE) now writes rows into `signal_history` automatically, laying the foundation for backtesting and AI tuning.

**How it works (as-built):**
- `analyze_optimizer` (`main.py`) inserts one `SignalHistory` row per actionable allocation after the `OptimizerHistory` entry is committed.
- `session_id` = `str(OptimizerHistory.id)` — groups all signals from the same optimizer run.
- `signal_type = "L2"` — rows reflect the Challenger's final allocation plan (the authoritative output).
- `score_at_signal` = `combined_score` from `scores_map` (0.4 × TA + 0.6 × FA), computed before the AI call.
- `price_at_signal` = live price at time of optimizer run (from `fetch_price_info`).
- `reasoning_snippet` = first 200 chars of the allocation `reason` field from L2.
- HOLD and WATCH actions are **not** recorded — only actionable changes.

**New endpoint:**
```
GET /analytics/signals
  ?symbol=      filter by symbol (optional)
  ?action=      BUY | SELL | ACCUMULATE | REDUCE (optional)
  ?signal_type= L1 | L2 (optional)
  ?session_id=  tie-break to one optimizer run (optional)
  ?limit=       max rows, default 100, cap 500
```
Returns rows ordered by `recorded_at DESC`. No auth required beyond existing JWT middleware.

**Alembic migration:** `j4k5l6m7n8o9_add_signal_history_action_fields.py` — adds `session_id`, `action`, `score_at_signal`, `signal_type`, `reasoning_snippet` to `signal_history`. SQLite handled via `migrate_legacy_data()`.

---

## FUTURE ARCHITECTURAL EVOLUTION (BACKLOG)
_Conceptual designs approved for future sprints. Do not implement until prerequisites are complete._

### ⚠ NEXT HIGH-PRIORITY: Background Job Queue Architecture

The 32-second watchlist analysis block still lives inside the HTTP request cycle — the client must hold the connection open for the full duration. The next phase moves execution entirely out of the request into **FastAPI `BackgroundTasks` with in-process job tracking**.

**Core decision:** `POST /analyze/watchlist` returns a `job_id` immediately (< 5 ms). Actual analysis runs in a background task. The client polls or streams for results independently of the initiating request.

**Target endpoint contract:**

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /analyze/watchlist` | — | Enqueues job, returns `{job_id, status: "queued", total: N, stale: M}` immediately |
| `GET /analyze/jobs/{job_id}` | polling | Returns current job state: `{status, done, total, results[], errors[], fallbacks}` |
| `GET /analyze/jobs/{job_id}/stream` | SSE | Real-time push — emits `progress` events as each stock finishes; closes with `complete` |

**Job state machine:** `queued → running → done | failed`

**In-process job store (no new DB table needed for v1):**
```python
_JOBS: dict[str, dict] = {}  # job_id → {status, done, total, results, errors, fallbacks, created_at}
```
Jobs expire from memory after 10 minutes. Use `uuid.uuid4()` for `job_id`.

**SSE stream format:**
```
data: {"type":"progress","done":17,"total":68,"symbol":"AAPL","signal":"BUY"}\n\n
data: {"type":"complete","done":68,"total":68,"fallbacks":2}\n\n
```

**Implementation split:**
1. **Job initialization** — validate inputs, build `stale_syms` list, create job record, enqueue `BackgroundTask`, return `job_id`
2. **Execution logic** — `_run_analysis_job(job_id, stale_syms, …)` async function that calls `_analyze_one_concurrent` in gather, writes each result into `_JOBS[job_id]` as it completes

### XAI Opportunity Score _(after Background Job Queue)_
Surface the `rebalance_opportunity_score` (0–100) more prominently: animated gauge on the optimizer run page, trend sparkline in history list, threshold-based push notification when a new run crosses 70+.
