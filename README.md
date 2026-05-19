# Stock Analysis System

## Project Overview
Full-stack web application for analyzing US and Thai SET stocks. Generates 6-level trading signals (ACCUMULATE / BUY / WATCH / HOLD / REDUCE / SELL) via multi-provider AI with Technical Analysis, Fundamental Analysis, and News aggregation. Includes portfolio management, watchlist, a 3-layer AI optimizer, and multi-timeframe charting.

## Tech Stack
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, @tanstack/react-table v8, recharts
- **Backend**: Python FastAPI, SQLite via SQLAlchemy
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
```

## Project Structure
```
stock-analysis/
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Dashboard
│   │   ├── portfolio/page.tsx    # Portfolio management
│   │   ├── watchlist/page.tsx    # Watchlist
│   │   ├── stock/[symbol]/page.tsx  # Stock detail (chart, consensus, history, second opinion)
│   │   ├── optimizer/page.tsx    # 3-layer Portfolio Optimizer
│   │   ├── settings/page.tsx     # All settings
│   │   └── login/page.tsx        # Auth
│   ├── components/
│   │   ├── SignalBadge.tsx        # 6-level signal badge
│   │   ├── PortfolioTable.tsx     # Sortable table with freshness dots
│   │   ├── AnalyzeAllButton.tsx   # Batch analyze (60-min cache)
│   │   ├── ConsensusCard.tsx      # Multi-model consensus + Why Disagree
│   │   ├── StockChart.tsx         # Multi-timeframe chart (EMA20, TEMA9, ZigZag, BB, MACD, RSI)
│   │   ├── AIBadge.tsx            # Provider/model display badge
│   │   ├── PortfolioSummary.tsx   # Portfolio totals row
│   │   ├── PortfolioPieChart.tsx  # Allocation pie chart
│   │   └── StockCard.tsx          # Stock summary card
│   └── lib/
│       ├── api.ts                 # All API fetch functions + TypeScript types
│       ├── auth.ts                # Token storage (localStorage)
│       └── PortfolioContext.tsx   # Active portfolio state
│
├── backend/
│   ├── main.py                   # FastAPI app + all route handlers
│   ├── auth.py                   # JWT login endpoint + verify_token middleware
│   ├── ai-model.json             # Available providers/models config
│   ├── agents/
│   │   ├── technical.py          # Dual-timeframe TA (short: 1mo/1d, long: 1y/1wk)
│   │   ├── fundamental.py        # FA — P/E, ROE, revenue growth, debt/equity
│   │   ├── news.py               # News via yfinance .news property
│   │   ├── summary.py            # AI summary → 6-level signal
│   │   ├── optimizer.py          # 3-layer optimizer + consensus engine
│   │   └── chart_data.py         # OHLCV + EMA20, TEMA9, ZigZag, BB, MACD, RSI
│   ├── models/
│   │   └── database.py           # SQLAlchemy models + migrate_legacy_data()
│   └── services/
│       ├── data_fetcher.py       # yfinance wrapper (fetch_history, fetch_price_info)
│       ├── scorer.py             # Deterministic 0-100 scoring (no AI)
│       ├── ai_client.py          # call_ai() — unified multi-provider AI client
│       └── json_utils.py         # safe_parse_json() — robust JSON from AI responses
│
└── CLAUDE.md
```

## Symbol Convention
- **US stocks**: `AAPL`, `GOOGL`, `TSLA`
- **Thai SET**: suffix `.BK` — `SCB.BK`, `PTT.BK`, `KBANK.BK`
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
Signal badge colors: ACCUMULATE=teal, BUY=green, WATCH=blue, HOLD=gray, REDUCE=amber, SELL=red.

## Database Models (`models/database.py`)
| Model | Purpose |
|---|---|
| `Portfolio` | Named portfolio (id, name) |
| `PortfolioItem` | Holdings (symbol, shares, avg_cost, allow_swap) |
| `Watchlist` | Watchlist symbols |
| `AnalysisCache` | Latest signal per symbol (upserted, 12h staleness check) |
| `AnalysisHistory` | Append-only log for consensus timeline |
| `AgentCache` | Per-agent yfinance cache (tech=15m, news=1h, fa=24h) |
| `OptimizerHistory` | Full optimizer result JSON per run |
| `Settings` | Key-value store for all user settings |

`migrate_legacy_data()` runs at startup for ALTER TABLE migrations.

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
POST   /portfolios/{id}/holdings     { symbol, shares, avg_cost }
DELETE /portfolios/{id}/holdings/{symbol}
PATCH  /portfolios/{id}/holdings/{symbol}/swap-permission   { allow_swap }
GET    /portfolios/{id}/prices       # lightweight real-time price refresh
POST   /portfolios/{id}/analyze      # full analyze (12h cache, skips fresh)
POST   /portfolios/{id}/analyze/all  # stale-only (60-min cache) → { total, analyzed, skipped, results }
```

### Watchlist
```
GET    /watchlist
POST   /watchlist                    { symbol }
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
POST /analyze/optimizer              { portfolio_id } → 3-layer result + consensus
GET  /optimizer/history?portfolio_id={id}
GET  /optimizer/history/{id}
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
Layer 3 — Risk Auditor : Concentration risk flags + safer_choice verdict
Consensus Engine       : Pure Python — no AI call
```
- `run_layered_optimizer(portfolio_data, watchlist_data, ..., layers, max_stocks, max_sector_pct, sector_limits)`
- Each layer has configurable provider/model (Settings → Optimizer Layers)
- Post-processing enforces: forced SELL entries, locked stock exclusion, sector caps, room cap
- PE percentiles computed batch-wide in `analyze_optimizer` endpoint; injected into `scores_map`

## Chart Indicators (`agents/chart_data.py`)
- EMA(20) — orange dashed
- TEMA(9) — cyan dashed (triple EMA, more responsive)
- ZigZag(5%, 10 bars) — pink solid, custom implementation with linear interpolation between pivots
- Bollinger Bands(20, 2σ) — gray dashed
- MACD EMA(12, 26, 9) close — line + signal + histogram (sub-panel)
- RSI(14) — purple line with 30/70 reference lines (sub-panel)
- Default period: 1Y/weekly

## Multi-Provider AI (`services/ai_client.py`)
```python
call_ai(prompt, provider, model, max_tokens) -> str
```
- Anthropic → anthropic SDK
- All others → OpenAI SDK with `base_url` from `ai-model.json`
- Fallback: checks `reasoning_content` when `content` is empty (DeepSeek R1, GLM-Z1)
- `safe_parse_json()` in `services/json_utils.py` — handles fenced/prose-wrapped JSON from any model

Available providers: anthropic, gemini, openai, deepseek, zhipu, groq (configured in `ai-model.json`)

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

## Coding Rules
- **Python**: type hints on all functions; async FastAPI handlers; Pydantic for request bodies
- **Error handling**: if yfinance returns empty data → `{ "error": "..." }` — never crash
- **Dates**: use `datetime.utcnow().isoformat() + "Z"` for consistent ISO strings (NOT `datetime.now(timezone.utc).isoformat() + "Z"` — that appends +00:00Z which is invalid)
- **JSON from AI**: always use `safe_parse_json()` — never `json.loads()` directly on AI response
- **Frontend**: all pages are Client Components (`"use client"`); use `dynamic()` with `ssr:false` for recharts
- **Naming**: snake_case Python, camelCase TypeScript, kebab-case file names

## Environment Variables
```
# backend/.env
ANTHROPIC_API_KEY=your_key
GEMINI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
OPENAI_API_KEY=your_key
DATABASE_URL=sqlite:///./stocks.db

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Known Limitations
- yfinance Thai stock (`.BK`) fundamental data often incomplete — handled gracefully
- yfinance news limited to ~10 recent articles per symbol
- ZhiPu/DeepSeek reasoning models return output in `reasoning_content`, not `content` — handled in `ai_client.py`
- Optimizer runs 3 sequential AI calls — expect 30–60s per run
- Sector classification in optimizer comes from AI output, not a fixed taxonomy

## Claude Code Session Tips
- Run /compact when context exceeds 20%
- Always read CLAUDE.md at start of new session
- Key files: `backend/main.py`, `backend/agents/optimizer.py`, `backend/agents/summary.py`, `frontend/lib/api.ts`
- DB migrations: add columns to `migrate_legacy_data()` in `models/database.py`
- When adding a new signal level: update `_VALID_SIGNALS` in summary.py, `SignalBadge.tsx`, api.ts union type, and all AI prompts
