# Portfolio Intelligence Roadmap

> Last Updated: 2026-07 (v2.0 — aligned with the constitutional domains)
>
> Current Status:
>
> **Phase 3 in progress**
>
> Phases 1–2 are complete: core investment engine, execution intelligence,
> AI evaluation, and accounting correctness. The Asset Registry — Phase 3's
> identity keystone — completed 2026-07.
>
> This roadmap states **what will be built, and in what order**. Why the
> platform is designed this way is stated once, in
> [platform_architecture.md](platform_architecture.md) (the constitution);
> this document is subordinate to it (constitution §11) and uses its domain
> vocabulary (§6, [GLOSSARY.md](../GLOSSARY.md)).

---

## Phase Map

Each phase advances one transition of the constitution's evolution arc (§9).

| Phase | Constitutional stage | Primary domains |
|---|---|---|
| 1 — Foundation ✅ | Portfolio Platform | Ledger & Accounting, Experience Platform |
| 2 — Investment Intelligence ✅ | Investment Intelligence | Portfolio Intelligence, Decision Intelligence, Trust & Evaluation |
| 3 — Platform Evolution | → Multi-Asset Platform (groundwork) | Asset Foundation, Market Intelligence, Portfolio Intelligence |
| 4 — SaaS Platform | (operational widening) | Experience Platform |
| 5 — Personal Wealth Platform | → Wealth Platform | Asset Foundation, Connectivity & Ingestion, Wealth Intelligence |
| 6 — Personal AI Wealth Advisor | → AI Wealth Advisor | Experience Platform, Decision Intelligence, Trust & Evaluation |

---

# Phase 1 — Foundation ✅ COMPLETE

Build a trustworthy investment platform.

## Platform

- ✅ Portfolio
- ✅ Watchlist
- ✅ Workspace
- ✅ User Wallet
- ✅ Billing
- ✅ Settings

## Infrastructure

- ✅ PostgreSQL
- ✅ VPS Deployment
- ✅ Vercel
- ✅ CI/CD Pipeline

## Portfolio Engine

- ✅ Transactions
- ✅ Replay Engine
- ✅ Portfolio Snapshots
- ✅ Portfolio Metrics Engine
- ✅ Ledger Validation
- ✅ Ledger Repair
- ✅ Benchmark Engine
- ✅ Performance History
- ✅ Accounting Rules

---

# Phase 2 — Investment Intelligence ✅ COMPLETE

Transform portfolio data into actionable investment intelligence.

_Recorded as achieved. Section names predate the constitution and are preserved as history. The optional analytics formerly pending here now live in Phase 3 under Portfolio Intelligence._

## Performance Analytics

- ✅ Total Return
- ✅ Annualized Return
- ✅ Volatility
- ✅ Max Drawdown
- ✅ Sharpe Ratio
- ✅ Alpha
- ✅ Beta
- ✅ Correlation
- ✅ Tracking Error
- ✅ Information Ratio
- ✅ Benchmark Comparison
- ✅ Cash Utilization

## Portfolio Optimizer

- ✅ Three-layer Optimizer
- ✅ Deterministic Scoring
- ✅ Confidence Calibration
- ✅ Funding-aware Execution
- ✅ Execution Optimization
- ✅ Recommendation Snapshot
- ✅ Recommendation Explainability

---

## Execution Intelligence

- ✅ Shadow Portfolio
- ✅ Shadow Portfolio Snapshots
- ✅ Execution Analysis
- ✅ Recommendation Report Card
- ✅ Plan Grading
- ✅ Horizon Grading

---

## AI Evaluation

- ✅ Human vs AI
- ✅ Opportunity Cost
- ✅ Three Portfolios
- ✅ Attribution Waterfall
- ✅ Trust Report
- ✅ AI Evaluation Hub

---

## Accounting Correctness

- ✅ Deterministic Replay
- ✅ NAV Conservation
- ✅ Cash Preservation
- ✅ Historical Regeneration
- ✅ Replay Validation
- ✅ Integration Consistency

---

# Phase 3 — Platform Evolution (in progress)

Lay the identity, valuation, and analytics groundwork the multi-asset
platform stands on.

## Asset Foundation

- ✅ Asset Registry — permanent identity, adjudication, classification
  consolidation, read-path adoption (completed 2026-07)
- Registry-Native Integration — ledger references and optimizer internals
  keyed to permanent identity
- Asset Definitions
- Asset Search
- Corporate Actions

## Market Intelligence

- Multiple Price Providers — provider independence behind one boundary
- Market Calendar
- Historical Services

## Portfolio Intelligence

- Rolling Analytics — rolling return, Sharpe, volatility
- Advanced Risk Metrics — including Sortino
- Position Attribution
- Sector Attribution Timeline

---

# Phase 4 — SaaS Platform

Scale from a personal platform to a production SaaS.

## Experience Platform — Multi-user

- Multi-workspace
- Team Accounts
- RBAC

## Experience Platform — Operations

- Usage Reports
- Credits
- Billing
- API Keys
- Audit Logs

---

# Phase 5 — Personal Wealth Platform

Expand from portfolio management to complete wealth management.

## Asset Foundation — Asset Classes

Each class arrives as an asset definition, never as engine surgery
(constitution §9).

- ✅ Stocks
- ETFs
- Mutual Funds
- Gold
- Crypto
- Cash (multi-currency)
- Property

## Connectivity & Ingestion

The doors through which a whole financial life enters
(architected in [BROKER_ACCOUNT_DOMAIN.md](BROKER_ACCOUNT_DOMAIN.md)).

- File & Statement Import
- Broker Account Integration
- Import Review & Reconciliation

## Wealth Intelligence — Financial Planning

- Net Worth
- Income
- Expenses
- Budget
- Cash Flow
- Emergency Fund

## Wealth Intelligence — Goals

- Retirement
- House
- Wedding
- Education
- Vacation
- FIRE

## Wealth Intelligence — Wealth Planning

- Debt Management
- Tax Planning
- Insurance Planning
- Estate Planning

---

# Phase 6 — Personal AI Wealth Advisor

Transform the platform from dashboards into an intelligent financial partner.

## Experience Platform — AI Experience

- Daily Portfolio Brief
- Natural Language Portfolio Review
- Portfolio Copilot

## Decision Intelligence

- Goal-aware Recommendations
- Tax-aware Suggestions
- Risk-aware Coaching
- Scenario Simulation

## Trust & Evaluation — Learning

Learning consumes the evaluation record and changes future behavior only
through the configuration gate (constitution §7.2).

- Recommendation Learning
- Confidence Calibration Learning
- Strategy Performance Learning
- Regime Learning
- Model Evaluation & Auto Calibration

---

# Open Engineering Backlog

These are important engineering improvements but are intentionally kept
outside the roadmap phases: the roadmap tracks product capabilities;
perpetual engineering quality work is tracked here
([ENGINEERING_PRINCIPLES.md](../engineering/ENGINEERING_PRINCIPLES.md),
"Capability vs. Quality").

## Accounting

- STATIC_FROZEN fallback correction
- Historical cash timeline fidelity

## Portfolio

- Decision → Transaction linkage
- System-deferral pricing

## Analytics

- Sector BHB attribution
- Multi-portfolio analytics

## Architecture

- Domain Modularization
- Event Bus
- Shared Analytics Library
- AI Routing Layer
- Prompt Layer Cleanup
- Internal API Simplification
- Cache Improvements

## Platform

- Accessibility (WCAG)
- UI consistency
- Performance optimization

---

# Governance

This roadmap is an implementation-level artifact under the constitution's
governance hierarchy ([platform_architecture.md](platform_architecture.md)
§11). The platform's guiding principles are the constitution's laws (§4)
and are deliberately not restated here. Where this document and the
constitution appear to disagree, the constitution states the intent and
this document states the schedule.