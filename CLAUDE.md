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
| `RecommendationSnapshot` | Full context of every 3L run: regime, constraint envelope, policy, L1/L2/L3 outputs, consensus, DNA, drift, scores_map. 1:1 with `OptimizerHistory`. |
| `UserExecutionDecision` | User action on a recommendation: APPROVED \| REJECTED \| MANUAL_OVERRIDE. Chains to `RecommendationSnapshot`. |
| `ShadowPortfolio` | Paper portfolio: STATIC_FROZEN (frozen at decision) or ACTIVE_MODEL (refreshed each run). Tracks hypothetical performance. |
| `ShadowPortfolioSnapshot` | Daily paper-trading valuation per shadow: total_value, returns, benchmark comparison, alpha. |
| `AttributionMetric` | BHB alpha attribution stub: selection_alpha, allocation_alpha, interaction_effect, per-sector breakdown. |
| `ConfidenceCalibrationRecord` | AI confidence → outcome calibration stub: consensus/policy/regime score accuracy + `feedback_context_json` for prompt re-injection. |

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
_Last updated: 2026-05-25 (Phase 3B.9 + accounting hotfix). Update this section at the start of each new session._

### Phase 3B.9 Hotfix — Backdated Import Detection & Quantity Correction ✅ SHIPPED 2026-05-25

Fixes a critical bug in the Phase 3B.9 snapshot engine where `INITIAL_POSITION` transactions recorded with a historical `transaction_date` were invisible to the non-performance stripping logic.

**Root cause:** The snapshot window filter used `Transaction.transaction_date` for detecting INITIAL_POSITION imports. When a user calls `POST /portfolios/{id}/transactions/initial-position` with a backdated `transaction_date` (e.g. the original purchase date years ago), the filter `transaction_date >= prev_day_end` fails — the import silently escapes stripping and appears as investment gain.

**Fix:** All non-performance transaction queries in `portfolio_snapshots.py` now filter by `Transaction.created_at` (physical DB insert time) instead of `transaction_date`. `created_at` is always `datetime.utcnow()` at insert time regardless of what `transaction_date` the user supplied.

**Additional changes:**
- New `QUANTITY_CORRECTION` transaction type for manual share-count adjustments to existing positions.
- `PortfolioSnapshot.manual_adjustment_value` (new nullable Float column) — stores market value of QUANTITY_CORRECTION events in the period. Subtracted from the formula alongside `imported_asset_value`.
- `execute_quantity_correction()` in `services/portfolio_transactions.py` — adjusts `PortfolioItem.shares` (weighted avg cost on additions) and writes a `QUANTITY_CORRECTION` transaction.
- `POST /portfolios/{id}/transactions/quantity-correction` endpoint.
- Alembic migration `s3t4u5v6w7x8` + `migrate_legacy_data()` patch for SQLite.
- Frontend: "Portfolio Correction: Imported Holdings" → **"Imported Assets"** (purple chip); new **"Quantity Correction"** (orange chip); **"Investment Gain"** chip now shows amount + percentage side by side. History table External Events column shows "adj" entries in orange.
- 2 new tests: `test_backdated_import_still_excluded` (proves `created_at` fix), `test_quantity_correction_excluded`.

**Formula (unchanged structure, new `manual_adjustment_value` term):**
```
pure_market_gain = today_nav - prev_nav - net_external_cash_flow - imported_asset_value - manual_adjustment_value
```

### Phase 3B.9 — Position Import Accounting Fix ✅ SHIPPED 2026-05-25

Eliminates the "position import = trading gain" accounting distortion. Any manually imported holding (via `INITIAL_POSITION` or `POST /portfolios/{id}/holdings`) is now classified as a **NON-PERFORMANCE CAPITAL INFLOW** and excluded from all return, alpha, Sharpe, and attribution calculations.

**Root cause:** The previous snapshot engine only stripped `DEPOSIT`/`WITHDRAW` from the NAV delta. `INITIAL_POSITION` injected equity into the portfolio without a corresponding cash outflow — the snapshot treated the full market value as market gain.

**What was built:**

- **`PortfolioSnapshot.imported_asset_value`** (new nullable Float column) — market value of all `INITIAL_POSITION` transactions that occurred between the previous snapshot and today. Stored at **current market price** (not avg_cost) so that unrealised appreciation that pre-dated the import is also excluded.

- **Alembic migration `r2s3t4u5v6w7`** — adds `imported_asset_value` to `portfolio_snapshots`. SQLite patched via `migrate_legacy_data()`. Historical rows have NULL (engine defaults to 0.0).

- **`services/portfolio_snapshots.py` rewrite:**
  - `_CASH_INFLOW_TYPES = {"DEPOSIT", "INITIAL_CASH"}` — `INITIAL_CASH` (onboarding) now included in `net_external_cash_flow`, fixing a second unreported distortion.
  - `_ASSET_IMPORT_TYPES = {"INITIAL_POSITION"}` — new query computes `imported_asset_value` as `∑ shares × live_price` for all import transactions in the window.
  - **Corrected formula:** `pure_market_gain = today_nav − prev_nav − net_external_cash_flow − imported_asset_value`
  - `imported_asset_value` stored in snapshot row and returned in API response.

- **`main.py` — `add_holding` fixed:** was directly inserting a `PortfolioItem` with no transaction record. Now calls `execute_initial_position()`, ensuring every holding added via the UI leaves an `INITIAL_POSITION` trace that the snapshot engine can classify correctly.

- **`frontend/lib/api.ts`:** `PortfolioSnapshotRow.imported_asset_value: number | null` added.

- **`frontend/app/performance/page.tsx`:**
  - Disclosure banner now triggers on `imported_asset_value` as well as `net_external_cash_flow`.
  - Shows **"Portfolio Correction"** purple label with amount when position imports occurred.
  - History table "Cash Flow" column renamed to "External Events"; import rows appear as `+X import` in purple alongside `+X cash` in blue.

- **`backend/tests/test_position_import_accounting.py`** — 6 green tests:
  1. `test_import_does_not_create_return` — 1000-share import → 0% return
  2. `test_initial_cash_excluded_from_return` — onboarding cash → 0% return
  3. `test_deposit_regression_still_excluded` — DEPOSIT regression guard
  4. `test_mixed_import_and_market_gain` — import + real market gain: only gain counted
  5. `test_quantity_correction_upward_excluded` — upward quantity correction → 0% return
  6. `test_buy_transaction_is_performance_event` — BUY + price appreciation correctly reflected

**Performance formula before/after:**
```
# Before (bugged):
investment_return_pct = (today_nav - prev_nav - net_ecf) / prev_nav

# After (correct):
investment_return_pct = (today_nav - prev_nav - net_external_cash_flow - imported_asset_value) / prev_nav
#  where net_external_cash_flow now includes INITIAL_CASH (was missing before)
```

**Shadow portfolio & attribution engine are unaffected:** shadow portfolios are paper portfolios driven purely by market movement — they never receive `INITIAL_POSITION` events. Attribution metrics read `investment_return_pct` from actual snapshots which now correctly excludes imports.

### Phase 3B.7C — Execution Lifecycle Tracking & Shadow Portfolio Engine ✅ SHIPPED 2026-05-25

See full block at bottom of CURRENT ARCHITECTURE STATE section.

### Phase 3B.7B — Attribution Analytics & Human-vs-AI Benchmark Engine ✅ SHIPPED 2026-05-25

See full block below Phase 3B.7C entry.

### Phase 3B.7A — Decision Persistence & Shadow Benchmark Infrastructure ✅ SHIPPED 2026-05-25

See full block below Phase 3B.6 entry.

### Phase 3B.6 — Authorized Exception Semantics & Defensive Alignment Fix ✅ SHIPPED 2026-05-25

Eliminated "Defensive Alignment Collapse" — the tendency of L2/L3 AI agents and the Consensus Engine to misinterpret authorized operational relaxations (e.g. Turnover Relaxation Active) as failure conditions warranting `REVIEW` escalation.

**What was built:**

- **Extended `_t1_note`** (`agents/optimizer.py`) — The Tier 1 breach notice block injected into all 3 AI layer prompts now appends a mandatory "AUTHORIZED EXCEPTION SEMANTICS" section containing:
  - Explicit classification: `Turnover Relaxation Active` = SAFE AUTHORIZED STATE (not a failure)
  - Two semantic categories injected into agent reasoning:
    - **SAFE AUTHORIZED STATES** (must NOT escalate): Turnover Relaxation Active, Temporary Cash Deployment Override, Controlled Sector Rotation
    - **DANGEROUS FAILURE STATES** (may escalate): Unresolved concentration breach, contradictory allocations, unauthorized risk escalation, policy violations without authorization
  - Mandatory decision rule: if concentration violations are materially reduced + only concern is authorized turnover buffer → L2 MUST output `status=REBALANCE`; L3 MUST output `final_risk_level=low|medium`

- **Governance penalty filter** (`agents/optimizer.py` ~line 1724) — When `_t1_severity != "NONE"` (Tier 1 relaxation active), turnover-related governance flags (`"turnover"`, `"tier3_efficiency"` in flag text) are excluded from the `consensus_strength_score` penalty. Only genuine unresolved violations (concentration, sector, cash, aggression) still penalize. Authorized expansions contribute neutral confidence impact.
  - Log format: `[POLICY_GOV] flags=N penalizable=M strength_penalty=-P t1_severity=X`

- **`TurnoverRelaxationNotice`** (`components/ActivePolicyEnvelopeCard.tsx`) — Redesigned from amber/warning to blue/informational:
  - Title: "Turnover Relaxation Active" → **"Temporary Turnover Expansion Authorized"**
  - Color: amber → blue; language communicates intentionality, controlled risk management

- **`VIOLATION_FRIENDLY_NAME`** map (`ActivePolicyEnvelopeCard.tsx`) — All violation types now display human-friendly names:
  - `TURNOVER_BREACH` → "Temporary Turnover Expansion Authorized"
  - `CASH_BREACH` → "Cash Mandate Breach", etc.

- **`PolicyViolationList`** (`ActivePolicyEnvelopeCard.tsx`) — When all remaining violations are authorized operational types (TURNOVER_BREACH / TURNOVER_RELAXED), the section header reads **"Controlled Optimization Adjustment"** instead of "Policy Violations Detected". `TURNOVER_BREACH` uses teal/info styling instead of blue-warning.

- **`GOV_FLAG_COLOR`** (`ActivePolicyEnvelopeCard.tsx`) — `POLICY_VIOLATION` governance flags containing "turnover" now display with blue/informational styling instead of red/error.

**Key design decisions:**
- Authorized exception semantics injected via `_t1_note` (shared across all 3 layers) — no per-prompt duplication
- Governance penalty skips only flags matching "turnover"/"tier3_efficiency" keyword pattern; all Tier 1/Tier 2 flags still penalize normally
- `TURNOVER_BREACH` in `violation_details` only appears when turnover exceeds even the relaxed cap (genuine violation) — the informational display correctly softens genuine Tier 3 overages while not hiding real problems
- `hasOnlyAuthorized` check in `PolicyViolationList` preserves strict language when real Tier 1/2 violations co-exist with authorized Tier 3 expansions

### Phase 3B.5 — Deterministic Constraint Resolution Layer ✅ SHIPPED 2026-05-25

The optimizer now has a **single, deterministic source of truth** for all allocation constraints, eliminating overlapping and contradictory controls between user settings, regime policies, and system safety limits.

**What was built:**
- `services/optimizer/constraint_resolver.py` — pure Python resolver merging 4 constraint sources into `EffectiveEnvelope`:
  - **A) User Preferences** — `max_sector_pct`, per-sector `sector_limits`, persona volatility tolerance
  - **B) Regime Policy** — `_REGIME_SECTOR_MULTIPLIERS` (e.g. `HIGH_VOLATILITY → 0.70`) applied multiplicatively to user sector limits
  - **C) Emergency Overrides** — `EMERGENCY_MAX_SECTOR=25`, `EMERGENCY_MAX_SINGLE_POSITION=15`, `EMERGENCY_MIN_CASH=20`, `EMERGENCY_MAX_TURNOVER=15`
  - **D) Absolute System Safety** — `ABSOLUTE_SYSTEM_MAX_SECTOR=70`, `ABSOLUTE_SYSTEM_MAX_SINGLE_POSITION=40`, etc.
  - Resolution: `effective = min(A, B, C, D)` for upper bounds; `max()` for cash floor
- `ConstraintBreakdown` dataclass — per-constraint audit trail: `{user_pref, regime_policy, emergency_limit, system_safety, effective, binding_source, tightened_reason}`
- `EffectiveEnvelope` dataclass — holds `single_position`, `cash_min`, `turnover_max`, `beta_ceiling`, `sector_limits` (per-sector breakdowns), `global_sector_cap`, plus flat `effective_*` fields for quick access
- `effective_sector_cap(envelope, sector)` — single call to get the resolved sector ceiling for any sector name
- `envelope_to_dict(envelope)` — JSON-serializable dict including all breakdowns
- `services/optimizer/policy_engine.py` — updated `compute_policy()` to accept `effective_envelope` param; uses resolver output as pre-discount baseline; `compute_policy_alignment_score()` returns 5-tuple adding `violation_details: list[dict]`; `build_policy_prompt_block()` shows `RESOLVED_SECTOR_LIMITS:` when per-sector limits available; `_detect_violations()` checks sector weights via market_value-weighted computation
- `agents/optimizer.py` — `run_layered_optimizer()` gains `effective_envelope` param; L1 prompt uses resolved per-sector limits; L3 prompt uses `critical_pos_threshold`/`high_pos_threshold` derived from resolved max position (not hardcoded 30%); new post-AI **sector enforcement block** trims BUY/ACCUMULATE allocations when projected sector weight exceeds resolved limit; governance scoring uses 5-tuple; `effective_envelope` surfaced in return dict
- `main.py` — calls `resolve_constraints()` before `compute_policy()`, passes `effective_envelope` through both
- `frontend/lib/api.ts` — `ConstraintSource`, `ConstraintBreakdown`, `EffectiveEnvelope`, `PolicyViolationType`, `PolicyViolationDetail` types; `ActivePolicy.resolved_sector_limits`, `ActivePolicy.violation_details`, `OptimizerResult.effective_envelope`
- `frontend/components/ActivePolicyEnvelopeCard.tsx` — `ConstraintComparisonTable` (User Pref | Regime Policy | Effective | Source columns); `PolicyViolationList` with typed violation details; `SourceBadge` component
- `frontend/app/optimizer/page.tsx` — passes `effectiveEnvelope={result.effective_envelope}` to `ActivePolicyEnvelopeCard`

**Key design decisions:**
- Resolver outputs "pre-discount" baselines; policy engine's confidence discount applied on top (clean separation of concerns)
- `emergency_limit` stored as `float | None` (not `float("inf")`) for JSON serializability
- `_norm_sector()` duplicated inline in `policy_engine.py` to avoid circular import (optimizer.py → policy_engine.py)
- Sector enforcement (new): first deterministic post-AI trimming of BUY/ACCUMULATE when projected sector weight exceeds resolved limit
- All new parameters default to `None`; `effective_envelope=None` leaves all existing code paths unchanged
- Historical optimizer results without `effective_envelope` display normally; `PolicyViolationList` only renders when `violation_details` is present

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

### Phase 3B.7A — Decision Persistence & Shadow Benchmark Infrastructure ✅ SHIPPED 2026-05-25

Establishes the **Decision Attribution & Benchmark Intelligence** layer — a persistent memory of every optimizer recommendation, user execution decision, and the realized performance consequences. Provides the data foundation for selection/allocation alpha attribution and confidence calibration feedback loops.

**What was built:**

**Database schemas (`models/database.py` + Alembic `n8o9p0q1r2s3`):**

| Table | Purpose |
|---|---|
| `recommendation_snapshots` | Full context of every 3L optimizer run: regime, constraint envelope, policy, L1/L2/L3 raw outputs, consensus, portfolio DNA, drift, scores_map, projected allocations. 1:1 with `optimizer_history`. |
| `user_execution_decisions` | User action chained to a snapshot: `APPROVED \| REJECTED \| PARTIAL_EXECUTION \| MANUAL_OVERRIDE`. Records approved allocations, rejected symbols, override notes, execution timestamp. |
| `shadow_portfolios` | Paper portfolio metadata for two tracking modes: `STATIC_FROZEN` (frozen at decision time — tracks "what would have happened") and `ACTIVE_MODEL` (hypothetical 100%-compliant portfolio, updated each optimizer run). |
| `shadow_portfolio_snapshots` | Daily paper-trading valuations per shadow portfolio: total value, inception/daily return %, per-holding market values, benchmark return, alpha (shadow − benchmark). |
| `attribution_metrics` | Brinson-Hood-Beebower decomposition per shadow/period: `selection_alpha`, `allocation_alpha`, `interaction_effect`, `total_alpha`, per-sector breakdown JSON. **Structural stub** — awaits per-sector benchmark data. |
| `confidence_calibration_records` | Feedback loop: maps `consensus_strength_score`, `policy_alignment_score`, `regime_confidence` → realized outcomes. Produces `feedback_context_json` for re-injection into future AI prompts. **Structural stub** — regime stability dimension fully implemented; signal accuracy and policy compliance await >30-day history. |

**Services (`services/decision_memory/`):**
- `snapshot_writer.py` — `write_recommendation_snapshot()`: idempotent, called automatically after every optimizer run. Swallowed on failure — never blocks HTTP response.
- `shadow_tracker.py` — `value_shadow_portfolio()`, `value_all_active_shadows()`, `create_static_frozen_shadow()`, `create_active_model_shadow()`. Paper-trading math using live yfinance prices + `BenchmarkPrice` table for benchmark return.
- `attribution.py` — `compute_attribution()` / `get_attribution_summary()`: BHB framework structure, persists to `AttributionMetric`. Sector decomposition stub.
- `calibration.py` — `compute_calibration()` / `get_latest_calibration()`: three calibration dimensions + `feedback_context_json` block. Regime stability is live; signal/policy accuracy stubs noted.

**API endpoints (`main.py`):**
```
POST /optimizer/decisions                        # record APPROVED|REJECTED|PARTIAL_EXECUTION|MANUAL_OVERRIDE
GET  /optimizer/decisions                        # list decisions (filter: portfolio_id, decision)
GET  /optimizer/decisions/{id}                   # detail with linked snapshot metadata
GET  /optimizer/snapshots/{id}                   # full RecommendationSnapshot (all L1/L2/L3 JSON)
POST /analytics/shadow-portfolios                # create STATIC_FROZEN or ACTIVE_MODEL shadow
GET  /analytics/shadow-portfolios                # list shadows (filter: portfolio_id, shadow_type, active_only)
GET  /analytics/shadow-portfolios/{id}/performance  # daily history + today's valuation
POST /analytics/shadow-portfolios/{id}/value     # trigger immediate paper-valuation
GET  /analytics/attribution/{shadow_id}          # BHB attribution (+ history)
GET  /analytics/calibration                      # confidence calibration (refresh=true to recompute)
```

**Frontend (`frontend/lib/api.ts`):** `ExecutionDecisionType`, `ShadowPortfolioType`, `ExecutionDecision`, `ExecutionDecisionDetail`, `RecordDecisionPayload`, `RecordDecisionResult`, `RecommendationSnapshotFull`, `ShadowPortfolioSummary`, `ShadowPortfolioPerformance`, `ShadowDailySnapshot`, `ShadowValuationResult`, `AttributionResult`, `CalibrationDetail`, `CalibrationResponse` types exported. API functions: `recordExecutionDecision`, `listExecutionDecisions`, `getExecutionDecision`, `getRecommendationSnapshot`, `createShadowPortfolio`, `listShadowPortfolios`, `getShadowPortfolioPerformance`, `triggerShadowValuation`, `getAttribution`, `getCalibration`. `OptimizerResult.recommendation_snapshot_id` added.

**Scheduler integration (`services/snapshot_scheduler.py`):** `value_all_active_shadows()` called per-workspace in the daily 17:45 ICT job, after portfolio snapshots and before benchmark price fetch. Failure is caught and logged — never blocks the snapshot job.

**Auto-hook in `analyze_optimizer`:** `write_recommendation_snapshot()` is called automatically after every successful optimizer run (after `OptimizerHistory` commit). The resulting `recommendation_snapshot_id` is included in the API response. Failure is swallowed and logged.

**Key design decisions:**
- `recommendation_snapshots.optimizer_history_id` has a UNIQUE constraint — idempotent write per run
- `ShadowPortfolio.shadow_type` = `STATIC_FROZEN` (frozen at decision) vs `ACTIVE_MODEL` (refreshed each run, only one active per portfolio)
- `PARTIAL_EXECUTION` added alongside `APPROVED | REJECTED | MANUAL_OVERRIDE` to model partial follow-through
- Attribution and calibration are structural stubs with correct schema, working DB persistence, and well-typed stubs — completion requires accumulated price history and sector benchmark data
- All new FK columns default to `None`/nullable — no impact on existing optimizer runs without snapshots
- SQLite `migrate_legacy_data()` creates all 6 tables if missing; PostgreSQL uses Alembic migration

---

### Phase 3B.7B — Attribution Analytics & Human-vs-AI Benchmark Engine ✅ SHIPPED 2026-05-25

Transforms the Decision Memory infrastructure (3B.7A) into measurable intelligence. All calculations are **purely deterministic Python** from stored DB data — no yfinance calls, no AI inference. Observational analytics only.

**New Services:**

| File | Purpose |
|---|---|
| `services/analytics/attribution_engine.py` | `compute_portfolio_attribution()` — actual vs shadow returns, max drawdown, regret score, avoided drawdown, ai_outperformed flag. `compute_max_drawdown()` utility. |
| `services/analytics/human_vs_ai.py` | `compare_human_vs_ai()` — per-decision shadow vs actual comparison. Hit rate (% AI better), return delta, volatility delta, drawdown delta, verdict text. |
| `services/analytics/regime_attribution.py` | `compute_regime_attribution()` — groups portfolio daily_return_pct by RegimeSnapshot label. Per-regime avg return, total return, volatility, min/max. Also groups optimizer run stats (rebalance rate, avg opportunity score) by regime. |

**Calibration Enhancement (`services/decision_memory/calibration.py`):**
- `_compute_signal_accuracy()` now LIVE (was stub) — queries `AgentCache.technical` for current prices of symbols in `SignalHistory`
- Evaluates directional accuracy: BUY/ACCUMULATE correct if price went up, SELL/REDUCE correct if price went down
- 14-day minimum holding period before a signal is evaluated
- Groups by confidence bucket: HIGH (score ≥70), MEDIUM (40-69), LOW (<40) with per-bucket accuracy_pct
- `compute_calibration()` now surfaces bucket data in insights list and `feedback_context_json`

**DB Schema Extension (`AttributionMetric` table):**

New columns added (backward-compatible, all nullable):
- `portfolio_id` — FK to portfolios
- `recommendation_snapshot_id` — FK to recommendation_snapshots
- `evaluation_window_days` — evaluation period in days (default 30)
- `actual_return_pct` — real portfolio return over the window
- `static_shadow_return_pct` — STATIC_FROZEN shadow return
- `ai_model_return_pct` — ACTIVE_MODEL shadow return
- `avoided_drawdown_pct` — static_drawdown − actual_drawdown (positive = frozen had more drawdown)
- `regret_score` — ai_model_return − actual_return (positive = AI would have done better)
- `ai_outperformed` — bool: regret_score > 0

Migration: `p0q1r2s3t4u5_add_attribution_columns.py` (Alembic) + `migrate_legacy_data()` patches for SQLite.

**New API Endpoints (`main.py`):**
```
GET /analytics/attribution-summary?portfolio_id=X&evaluation_window_days=30
    → PortfolioAttributionResult (actual/static_shadow/ai_model metrics + history)

GET /analytics/human-vs-ai?portfolio_id=X&evaluation_days=90
    → HumanVsAIResponse (per-decision breakdown + summary with hit_rate, return_delta, verdict)

GET /analytics/regime-attribution?portfolio_id=X&lookback_days=90
    → RegimeAttributionResponse (per-regime return stats + optimizer run stats by regime)

GET /analytics/confidence-calibration?portfolio_id=X&lookback_days=30&refresh=false
    → Enhanced calibration with signal accuracy buckets (replaces /analytics/calibration v1)
```

**Frontend (`frontend/components/AttributionPanel.tsx`):**
4-card 2×2 grid rendered at the bottom of `ResultPanel` in `optimizer/page.tsx`:
1. **Shadow Benchmark Comparison** — 3-column return view (Actual / Static Shadow / AI Model), regret score, avoided drawdown, ai_better badge, interpretation text
2. **Human vs AI Decisions** — hit-rate gauge (circular), decision count, avg return delta, verdict text
3. **Performance by Market Regime** — per-regime badges sorted by avg daily return, best/worst labels, coverage %
4. **Confidence Calibration** — signal accuracy %, regime stability %, bucket bars (HIGH/MEDIUM/LOW confidence accuracy)

All cards: `useEffect` on `portfolioId` change, graceful empty states, no blocking on data absence.

**Key design decisions:**
- `compare_human_vs_ai` priority: linked shadow first → ACTIVE_MODEL second → no shadow (skip)
- `compute_max_drawdown` measures peak-to-trough in values list — used across all three services
- Attribution Engine persists to `AttributionMetric` idempotent on (shadow_portfolio_id, period_start, period_end)
- Regime attribution uses exact date-match between portfolio snapshot and regime snapshot; no interpolation
- Signal accuracy evaluates only signals with `price_at_signal IS NOT NULL` and `action IN (BUY, ACCUMULATE, SELL, REDUCE)`
- `getConfidenceCalibrationV2` is additive — `/analytics/confidence-calibration` is a new endpoint; original `/analytics/calibration` still exists

---

### Phase 3B.7C — Execution Lifecycle Tracking & Shadow Portfolio Engine ✅ SHIPPED 2026-05-25

Closes the decision attribution loop by wiring automatic attribution computation into approval events and the daily scheduler, adds portfolio-level shadow performance aggregation, and exposes a full execution lifecycle API surface.

**What was built:**

**Auto-attribution triggers:**
- `POST /optimizer/decisions` (record_execution_decision) now fires `compute_portfolio_attribution` in a background thread immediately after APPROVED shadow creation — attribution metrics are generated as soon as a decision is recorded, not just when the user navigates to the attribution panel.
- `snapshot_scheduler.py` daily job: after `value_all_active_shadows`, iterates all portfolios with active shadows and calls `compute_portfolio_attribution` for each. Attribution metrics are refreshed every trading day alongside shadow valuations.

**New API endpoints (`main.py`):**

| Endpoint | Purpose |
|---|---|
| `POST /optimizer/{snapshot_id}/decision` | Convenience endpoint — accepts snapshot_id from URL path; delegates to `POST /optimizer/decisions` |
| `GET /analytics/shadow-performance?portfolio_id=X` | Portfolio-level aggregate shadow summary: both STATIC_FROZEN + ACTIVE_MODEL in one call with inception_return_pct, alpha, last_valued_at |
| `GET /analytics/ai-vs-human-timeline?portfolio_id=X&evaluation_days=90` | Per-decision timeline from `compare_human_vs_ai`; ordered newest-first, capped at 50, includes aggregate summary |
| `GET /analytics/calibration-history?portfolio_id=X&limit=20` | Historical ConfidenceCalibrationRecord rows filtered to portfolio's snapshot chain; workspace-wide when portfolio_id omitted |

**Frontend (`frontend/lib/api.ts`):**
- `ShadowSummaryItem`, `ShadowPerformanceSummary`, `AIvsHumanTimelineEntry`, `AIvsHumanTimeline`, `CalibrationHistoryEntry` types exported
- `getShadowPerformanceSummary(portfolioId)` — calls `/analytics/shadow-performance`
- `getAIvsHumanTimeline(portfolioId, evaluationDays, limit)` — calls `/analytics/ai-vs-human-timeline`
- `getCalibrationHistory(portfolioId, limit)` — calls `/analytics/calibration-history`
- `recordDecisionBySnapshot(snapshotId, payload)` — calls `POST /optimizer/{snapshotId}/decision`

**Frontend (`optimizer/page.tsx`):**
- `ShadowReturnChip` helper component — colored +/− return pill
- `DecisionActionPanel` enhanced: when APPROVED, calls `getShadowPerformanceSummary` and renders a live shadow tracking status block showing:
  - "Shadow Tracking Active" teal badge with pulse dot
  - Inception date ("since YYYY-MM-DD")
  - Frozen return % + AI Model return % side by side
  - Alpha vs benchmark when available
  - "Performance data available after first daily valuation (17:45 ICT)" message when shadows exist but haven't been priced yet

**Key design decisions:**
- Attribution trigger on APPROVED uses a daemon thread (same pattern as calibration trigger) — never blocks HTTP response; failure logged and swallowed
- Scheduler attribution runs after shadow valuation (not before) so the latest snapshot prices are already committed when attribution is computed
- `get_shadow_performance_summary` returns `{has_shadows: false}` (not 404) when no shadows exist — frontend can gracefully skip display without error handling
- `get_ai_vs_human_timeline` delegates to the existing `compare_human_vs_ai` service without duplicating logic; the `total_decisions` field lets clients show "X of Y decisions shown"
- `get_calibration_history` filters via `RecommendationSnapshot.portfolio_id` join — no new foreign key needed
- `POST /optimizer/{snapshot_id}/decision` patches `body.recommendation_snapshot_id` before delegating — Pydantic model is mutable at endpoint level

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
