# Portfolio Intelligence Platform

## Project Overview
Full-stack web application for analyzing US and Thai SET stocks. Generates 6-level trading signals (ACCUMULATE / BUY / WATCH / HOLD / REDUCE / SELL) via multi-provider AI with Technical Analysis, Fundamental Analysis, and News aggregation. Includes portfolio management, watchlist, a 3-layer AI optimizer, sector allocation tracking, multi-timeframe charting, and AI latency/cost statistics.

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
│   │   ├── optimizer/page.tsx        # 3-layer Portfolio Optimizer + sector impact panel
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
│   │       └── b2c3d4e5f6a7_add_sector_to_watchlist_and_portfolio.py
│   └── services/
│       ├── data_fetcher.py           # yfinance wrapper + normalize_dr_symbol()
│       ├── scorer.py                 # Deterministic 0-100 scoring (no AI)
│       ├── ai_client.py              # call_ai() → dict{text, latency_ms, tokens, ...}
│       └── json_utils.py             # safe_parse_json() — robust JSON from AI responses
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
| `Portfolio` | Named portfolio (id, name) |
| `PortfolioItem` | Holdings (symbol, shares, avg_cost, allow_swap, **sector**) |
| `Watchlist` | Watchlist symbols (**sector** stored at add-time) |
| `AnalysisCache` | Latest signal per symbol (upserted, 12h staleness check) |
| `AnalysisHistory` | Append-only log (includes **latency_ms**, **total_latency_ms**) |
| `AgentCache` | Per-agent yfinance cache (tech=15m, news=1h, fa=24h) |
| `OptimizerHistory` | Full optimizer result JSON + per-layer latency columns |
| `Settings` | Key-value store for all user settings |
| `UserUsage` | Per-call AI token usage + cost + **latency_ms** |

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

### Optimizer
```
POST /analyze/optimizer              { portfolio_id } → 3-layer result + sector weights + consensus
GET  /optimizer/history?portfolio_id={id}
GET  /optimizer/history/{id}
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
- `run_layered_optimizer(...)` returns `layer1/2/3_latency_ms`, `total_latency_ms`, `current_sector_weights`, `projected_sector_weights`, `sector_warnings`
- Each layer has configurable provider/model (Settings → Optimizer Layers)
- Post-processing enforces: forced SELL entries, locked stock exclusion, sector caps, room cap
- PE percentiles computed batch-wide in `analyze_optimizer` endpoint; injected into `scores_map`
- **Sector Impact panel** in optimizer result shows before/after sector weights vs limits

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

## Claude Code Session Tips
- Run /compact when context exceeds 20%
- Always read CLAUDE.MD at start of new session
- Key files: `backend/main.py`, `backend/agents/optimizer.py`, `backend/agents/summary.py`, `frontend/lib/api.ts`
- DB migrations: add columns to both `migrate_legacy_data()` in `models/database.py` AND a new Alembic migration file
- Sector source of truth: `PortfolioItem.sector` / `Watchlist.sector` DB columns — populated at add-time
- When adding a new signal level: update `_VALID_SIGNALS` in summary.py, `SignalBadge.tsx`, api.ts union type, and all AI prompts
