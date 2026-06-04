# Portfolio Intelligence Platform

## Reference Docs
- **Architecture & API specs:** [docs/ARCH_SPEC.md](docs/ARCH_SPEC.md)
- **Design decisions & why:** [docs/DECISION_LOG.md](docs/DECISION_LOG.md)
- **Phase history & roadmap:** [docs/ROADMAP.md](docs/ROADMAP.md)

---

## Project Overview
Full-stack web app for Thai SET and US stock analysis. Generates 6-level trading signals (ACCUMULATE / BUY / WATCH / HOLD / REDUCE / SELL) via multi-provider AI with TA, FA, and News. Includes portfolio management, 3-layer AI optimizer, strategy personas, market regime detection, attribution analytics, and shadow portfolio tracking.

**Current phase:** 3B.10+ (Broker-Grade Fee Hardening) ✅ — entering Stabilization Sprint.

---

## Tech Stack
- **Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind CSS, @tanstack/react-table v8, recharts
- **Backend:** Python FastAPI, SQLite (dev) / PostgreSQL (prod), SQLAlchemy + Alembic
- **Data:** yfinance (free, no API key needed)
- **TA:** pandas_ta
- **AI:** Anthropic, Gemini, OpenAI, DeepSeek, ZhiPu, Groq via `services/ai_client.py`
- **Auth:** JWT (python-jose), 30-day expiry — username: `takae` / password: `121226`

---

## Run Commands
```bash
# Backend (Windows)
g:\work\ta\stock-analysis\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests
cd backend && python -m pytest tests/ -v

# DB migrations (PostgreSQL only)
cd backend && alembic upgrade head
```

---

## Project Structure
```
stock-analysis/
├── docs/                         # ARCH_SPEC.md, DECISION_LOG.md, ROADMAP.md
├── frontend/
│   ├── app/                      # page.tsx, portfolio/, watchlist/, stock/[symbol]/,
│   │                             # optimizer/, performance/, settings/, stats/, login/
│   ├── components/               # Navbar, SignalBadge, PortfolioTable, StockChart,
│   │                             # ConsensusCard, ActivePolicyEnvelopeCard, AttributionPanel,
│   │                             # MarketRegimeCard, PortfolioDNACard, StyleDriftCard, …
│   └── lib/
│       ├── api.ts                # All API fetch functions + TypeScript types
│       ├── auth.ts               # Token storage
│       ├── sectors.ts            # SECTOR_COLORS + sectorColor()
│       └── PortfolioContext.tsx  # Active portfolio state
├── backend/
│   ├── main.py                   # FastAPI app + all route handlers
│   ├── auth.py                   # JWT login + verify_token
│   ├── ai-model.json             # Provider/model config (costs, base URLs)
│   ├── agents/                   # technical.py, fundamental.py, news.py, summary.py,
│   │                             # optimizer.py, chart_data.py
│   ├── models/database.py        # SQLAlchemy models + migrate_legacy_data()
│   ├── migrations/versions/      # Alembic migration scripts
│   └── services/
│       ├── broker_fees.py        # FeeProfile registry + calc_fees() + resolve_fee_profile()
│       ├── portfolio_transactions.py  # execute_buy/sell/dividend/deposit/withdraw/…
│       ├── portfolio_snapshots.py     # Daily NAV snapshot engine
│       ├── snapshot_scheduler.py      # APScheduler 17:45 ICT job
│       ├── ai_client.py          # call_ai() multi-provider wrapper
│       ├── scorer.py             # Deterministic 0-100 scoring
│       ├── json_utils.py         # safe_parse_json()
│       ├── data_fetcher.py       # yfinance wrapper + normalize_dr_symbol()
│       ├── optimizer/            # constraint_resolver.py, policy_engine.py, strategy_profiles.py
│       ├── analytics/            # regime_detector.py, factor_engine.py, attribution_engine.py,
│       │                         # human_vs_ai.py, regime_attribution.py, quant_engine.py
│       └── decision_memory/      # snapshot_writer.py, shadow_tracker.py, attribution.py, calibration.py
└── tests/                        # test_fee_accounting.py, test_position_import_accounting.py, …
```

---

## Coding Rules (Non-Negotiable)
- **Python:** type hints on all functions; async FastAPI handlers; Pydantic for request bodies
- **Dates:** `datetime.utcnow().isoformat() + "Z"` — NOT `datetime.now(timezone.utc)` (appends invalid `+00:00Z`)
- **AI JSON:** always use `safe_parse_json()` — never `json.loads()` directly on AI output
- **DR symbols:** always call `normalize_dr_symbol(symbol)` before any yfinance call; keep original for DB
- **Sector in GET endpoints:** read `item.sector` from DB column — do NOT compute on-the-fly
- **Alembic:** new columns go in BOTH `migrate_legacy_data()` (SQLite) AND a new migration file
- **Personas:** use `valid_persona(raw)` to normalize input; default = `"BALANCED"`
- **Fee profiles:** use `resolve_fee_profile(symbol)` + `calc_fees()` — never hardcode fee math
- **Transactions:** `fees` = pre-VAT subtotal; `taxes` = VAT; period_fees_paid = `fees + taxes`
- **Frontend:** all pages are Client Components (`"use client"`); `dynamic()` with `ssr:false` for recharts
- **Naming:** snake_case Python, camelCase TypeScript, kebab-case file names
- **Error handling:** yfinance empty data → `{"error": "..."}` — never crash

---

## Environment Variables
```
# backend/.env
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
OPENAI_API_KEY=...
DATABASE_URL=sqlite:///./stocks.db   # or postgresql://user:pass@host/db

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Key Invariants
- **NAV:** `cash + equity_value = total_value` — always true, logged on every snapshot
- **Performance formula:** `investment_return_pct = (today_nav − prev_nav − net_ecf − imported_asset_value − manual_adj) / prev_nav × 100`
- **Snapshot timing:** 17:45 ICT (never earlier) — yfinance `.BK` prices have ~15-min post-close lag
- **Sector source of truth:** `PortfolioItem.sector` / `Watchlist.sector` DB columns (set at add-time)
- **avg_cost is fee-inclusive:** `avg_cost = net_buy_amount / shares` (includes all BUY fees + VAT)

---

## Claude Code Session Tips
- Run `/compact` when context exceeds 20%
- Always read `CLAUDE.MD` at start of a new session
- Key files for most tasks: `backend/main.py`, `backend/agents/optimizer.py`, `frontend/lib/api.ts`
- Adding a new signal level: update `_VALID_SIGNALS` in `summary.py`, `SignalBadge.tsx`, `api.ts` union type, and all AI prompts
- Adding a new snapshot column: update `PortfolioSnapshot` model, `migrate_legacy_data()`, new Alembic migration, `_snapshot_row()` in `main.py`, `PortfolioSnapshotRow` in `api.ts`
- After any fee formula change: run `POST /admin/recalculate-cost-basis` on live DB; validate with `GET /admin/validate-portfolio/{id}`
