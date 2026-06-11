from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Text, ForeignKey, UniqueConstraint, Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stocks.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Workspace(Base):
    """Top-level tenant boundary. Single default workspace in single-user mode."""
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Default")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolios = relationship("Portfolio", back_populates="workspace", cascade="all, delete-orphan")
    watchlist_items = relationship("Watchlist", back_populates="workspace", cascade="all, delete-orphan")
    settings = relationship("Settings", back_populates="workspace", cascade="all, delete-orphan")
    analysis_cache_items = relationship("AnalysisCache", back_populates="workspace", cascade="all, delete-orphan")
    analysis_history_items = relationship("AnalysisHistory", back_populates="workspace", cascade="all, delete-orphan")
    optimizer_history_items = relationship("OptimizerHistory", back_populates="workspace", cascade="all, delete-orphan")
    signal_history_items = relationship("SignalHistory", back_populates="workspace", cascade="all, delete-orphan")
    recommendation_snapshots = relationship("RecommendationSnapshot", back_populates="workspace", cascade="all, delete-orphan")
    execution_decisions = relationship("UserExecutionDecision", back_populates="workspace", cascade="all, delete-orphan")
    shadow_portfolios = relationship("ShadowPortfolio", back_populates="workspace", cascade="all, delete-orphan")
    attribution_metrics = relationship("AttributionMetric", back_populates="workspace", cascade="all, delete-orphan")
    calibration_records = relationship("ConfidenceCalibrationRecord", back_populates="workspace", cascade="all, delete-orphan")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    cash_balance = Column(Float, nullable=False, default=0.0)
    strategy_persona = Column(String, nullable=True, default="BALANCED")
    goal_target_value = Column(Float, nullable=True)  # Phase 4C.1: portfolio value goal (NULL = no goal set)
    # Phase 4C.3 Goal Discovery Wizard — all nullable, NULL = not configured yet.
    goal_type = Column(String, nullable=True)         # WEDDING|HOUSE|EDUCATION|RETIREMENT|FINANCIAL_FREEDOM|WEALTH_GROWTH|OTHER
    goal_priority = Column(String, nullable=True)     # ESSENTIAL|IMPORTANT|ASPIRATIONAL
    goal_target_date = Column(String, nullable=True)  # YYYY-MM-DD
    risk_personality = Column(String, nullable=True)  # AGGRESSIVE|MODERATE|CONSERVATIVE
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="portfolios")
    items = relationship("PortfolioItem", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")
    snapshots = relationship("PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    shares = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    allow_swap = Column(Boolean, nullable=False, default=True)
    sector = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="items")

    __table_args__ = (UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),)


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, index=True, nullable=False)
    sector = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="watchlist_items")

    __table_args__ = (UniqueConstraint("workspace_id", "symbol", name="uq_watchlist_ws_symbol"),)


class AgentCache(Base):
    """Caches raw agent results (TA / FA / News) with per-agent TTLs. Shared across workspaces."""
    __tablename__ = "agent_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    agent = Column(String, nullable=False)   # "technical" | "fundamental" | "news"
    result_json = Column(Text, nullable=False)
    cached_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("symbol", "agent", name="uq_agent_cache"),)


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, index=True, nullable=False)
    signal = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    reasoning = Column(Text, nullable=False)
    risks = Column(Text, nullable=False)
    executive_summary = Column(Text, nullable=True)  # plain-Thai "what the company is" (80-120 words)
    ai_summary = Column(Text, nullable=True)         # plain-Thai investment-interpreter narrative (80-120 words)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ta_score = Column(Integer, nullable=True)
    fa_score = Column(Integer, nullable=True)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    sources_used = Column(Text, nullable=True)

    workspace = relationship("Workspace", back_populates="analysis_cache_items")

    __table_args__ = (UniqueConstraint("workspace_id", "symbol", name="uq_analysis_cache_ws_symbol"),)


class OptimizerHistory(Base):
    __tablename__ = "optimizer_history"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_name = Column(String, nullable=False)
    analyzed_at = Column(DateTime, nullable=False)
    swap_count = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=False)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    layer1_latency_ms = Column(Integer, nullable=True)
    layer2_latency_ms = Column(Integer, nullable=True)
    layer3_latency_ms = Column(Integer, nullable=True)
    total_latency_ms = Column(Integer, nullable=True)
    optimizer_status = Column(String, nullable=True)          # REBALANCE | NO_ACTION
    rebalance_opportunity_score = Column(Integer, nullable=True)  # 0-100
    no_action_reason = Column(String, nullable=True)          # enum: WELL_BALANCED | LOW_CONFIDENCE | …
    no_action_summary = Column(Text, nullable=True)
    blocked_opportunities_json = Column(Text, nullable=True)  # JSON array

    workspace = relationship("Workspace", back_populates="optimizer_history_items")


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, index=True, nullable=False)
    signal = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    reasoning = Column(Text, nullable=False)
    risks = Column(Text, nullable=False)
    executive_summary = Column(Text, nullable=True)  # plain-Thai "what the company is" (80-120 words)
    ai_summary = Column(Text, nullable=True)         # plain-Thai investment-interpreter narrative (80-120 words)
    ta_score = Column(Integer, nullable=True)
    fa_score = Column(Integer, nullable=True)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    sources_used = Column(Text, nullable=True)
    scores = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    total_latency_ms = Column(Integer, nullable=True)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="analysis_history_items")


class Transaction(Base):
    """Records individual transactions for a portfolio.

    transaction_type values:
      BUY, SELL             — equity transactions (symbol required)
      DEPOSIT, WITHDRAW     — cash movements (symbol is null)
      INITIAL_POSITION      — onboarding: import existing holding (symbol required)
      INITIAL_CASH          — onboarding: set starting cash (symbol is null)
      QUANTITY_CORRECTION   — manual share-count adjustment (symbol required)
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, nullable=True, index=True)        # null for cash-only transactions
    transaction_type = Column(String, nullable=False, index=True)
    shares = Column(Float, nullable=True)
    price_per_share = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    fees = Column(Float, nullable=False, default=0.0)
    taxes = Column(Float, nullable=True, default=0.0)
    currency = Column(String, nullable=True, default="THB")
    exchange_rate = Column(Float, nullable=True, default=1.0)
    transaction_date = Column(DateTime, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    sector = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="transactions")


class PortfolioSnapshot(Base):
    """Daily snapshot of portfolio total value for historical charting."""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(String, nullable=False, index=True)  # "YYYY-MM-DD"
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False, default=0.0)
    total_invested = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=True)
    unrealized_pnl_pct = Column(Float, nullable=True)
    realized_pnl = Column(Float, nullable=True)           # cumulative realized P/L from all SELL txs
    daily_return_pct = Column(Float, nullable=True)           # cash-flow-adjusted day-over-day return
    net_external_cash_flow = Column(Float, nullable=True)     # deposits - withdrawals this period
    investment_return_pct = Column(Float, nullable=True)      # same as daily_return_pct (semantic alias)
    investment_return_amount = Column(Float, nullable=True)   # absolute pure market gain/loss
    imported_asset_value = Column(Float, nullable=True)       # market value of INITIAL_POSITION imports this period
    manual_adjustment_value = Column(Float, nullable=True)    # market value of QUANTITY_CORRECTION adjustments this period
    # Period-level return decomposition (for transparency / debugging)
    period_realized_pnl = Column(Float, nullable=True)        # realized P&L from SELL transactions in this window
    period_dividend_income = Column(Float, nullable=True)     # dividend income received in this window
    period_fees_paid = Column(Float, nullable=True)           # total brokerage fees paid on trades in this window
    sector_breakdown_json = Column(Text, nullable=True)  # JSON {"Technology": 35.2, ...}
    holdings_json = Column(Text, nullable=True)          # JSON [{symbol, shares, market_value, ...}]
    holdings_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="snapshots")

    __table_args__ = (UniqueConstraint("portfolio_id", "snapshot_date", name="uq_portfolio_snapshot_date"),)


class BenchmarkPrice(Base):
    """Daily closing price for an index or ETF benchmark (e.g. ^SET, QQQ)."""
    __tablename__ = "benchmark_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    price_date = Column(String, nullable=False, index=True)  # "YYYY-MM-DD"
    close_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Phase S.3: data freshness / provenance (set by sync_prices.py)
    updated_at = Column(DateTime, nullable=True)
    data_source = Column(String, nullable=True)   # "yfinance_github_actions" | "yfinance_local"
    sync_status = Column(String, nullable=True)   # "ok" | "error" | "stale"

    __table_args__ = (UniqueConstraint("symbol", "price_date", name="uq_benchmark_symbol_date"),)


class SignalHistory(Base):
    """Append-only log of every AI-confirmed optimizer action for backtesting."""
    __tablename__ = "signal_history"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)       # ties rows to one optimizer run
    symbol = Column(String, nullable=False, index=True)
    sector = Column(String, nullable=True, index=True)
    action = Column(String, nullable=True)                        # BUY/SELL/SWAP/ACCUMULATE/REDUCE
    signal = Column(String, nullable=False)                       # current signal at time of record
    prev_signal = Column(String, nullable=True)
    signal_type = Column(String, nullable=True)                   # "L1" | "L2"
    confidence = Column(String, nullable=True)
    ta_score = Column(Integer, nullable=True)
    fa_score = Column(Integer, nullable=True)
    score_at_signal = Column(Float, nullable=True)                # combined_score (0-100)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    price_at_signal = Column(Float, nullable=True)
    reasoning_snippet = Column(Text, nullable=True)               # first 200 chars of allocation reason
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    workspace = relationship("Workspace", back_populates="signal_history_items")


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False)

    workspace = relationship("Workspace", back_populates="settings")

    __table_args__ = (UniqueConstraint("workspace_id", "key", name="uq_settings_ws_key"),)


class MarketDataCache(Base):
    """DB-backed cache for raw yfinance responses.

    Keyed by (symbol, cache_type) where cache_type encodes both the data kind
    and the fetch parameters, e.g. "quote", "fundamental", "history:1y:1wk".
    Shared across all workspaces — market data is not user-specific.
    """
    __tablename__ = "market_data_cache"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    cache_type = Column(String, nullable=False)   # "quote"|"fundamental"|"history:1y:1wk"|…
    payload_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    hit_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("symbol", "cache_type", name="uq_market_data_cache"),)


class RegimeSnapshot(Base):
    """Daily market regime detection snapshot for historical tracking and backtesting."""
    __tablename__ = "regime_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(String, nullable=False, index=True)   # "YYYY-MM-DD"
    regime = Column(String, nullable=False)                       # RISK_ON | RISK_OFF | ...
    confidence = Column(Float, nullable=False)                    # 0.0–1.0
    trend_score = Column(Float, nullable=True)                    # 0–100
    volatility_score = Column(Float, nullable=True)               # 0–100
    drawdown_score = Column(Float, nullable=True)                 # 0–100
    momentum_score = Column(Float, nullable=True)                 # 0–100
    vol_z_score = Column(Float, nullable=True)                    # signed z-score
    ema_alignment = Column(Float, nullable=True)                  # 0–100
    regime_duration_days = Column(Integer, nullable=True)
    previous_regime = Column(String, nullable=True)
    transition_stability = Column(String, nullable=True)          # STABLE | TRANSITIONING | VOLATILE
    signals_json = Column(Text, nullable=True)                    # per-benchmark signal details
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("snapshot_date", name="uq_regime_snapshot_date"),)


class RecommendationSnapshot(Base):
    """Full context of a 3-layer optimizer run — regime, constraints, L1/L2/L3 outputs, DNA."""
    __tablename__ = "recommendation_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    optimizer_history_id = Column(Integer, ForeignKey("optimizer_history.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    persona = Column(String, nullable=True)                        # strategy persona at run time
    total_portfolio_value = Column(Float, nullable=True)           # total equity value at run time
    regime_snapshot_json = Column(Text, nullable=True)             # MarketRegime dict
    constraint_envelope_json = Column(Text, nullable=True)         # EffectiveEnvelope dict
    active_policy_json = Column(Text, nullable=True)               # PolicyEnvelope dict
    layer1_output_json = Column(Text, nullable=True)               # raw L1 strategist output
    layer2_output_json = Column(Text, nullable=True)               # raw L2 challenger output (allocations)
    layer3_output_json = Column(Text, nullable=True)               # raw L3 risk audit output
    consensus_json = Column(Text, nullable=True)                   # consensus result dict
    portfolio_dna_json = Column(Text, nullable=True)               # PortfolioDNA at snapshot time
    style_drift_json = Column(Text, nullable=True)                 # StyleDrift metrics at snapshot time
    scores_map_json = Column(Text, nullable=True)                  # per-symbol scores used by optimizer
    projected_allocations_json = Column(Text, nullable=True)       # L2 target allocations list
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="recommendation_snapshots")
    decisions = relationship("UserExecutionDecision", back_populates="snapshot", cascade="all, delete-orphan")
    shadow_portfolios = relationship("ShadowPortfolio", back_populates="recommendation_snapshot")


class UserExecutionDecision(Base):
    """Records the explicit action a user took after reviewing an optimizer recommendation."""
    __tablename__ = "user_execution_decisions"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_snapshot_id = Column(Integer, ForeignKey("recommendation_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    optimizer_history_id = Column(Integer, ForeignKey("optimizer_history.id", ondelete="SET NULL"), nullable=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    # APPROVED | REJECTED | MANUAL_OVERRIDE
    decision = Column(String, nullable=False, index=True)
    approved_allocations_json = Column(Text, nullable=True)        # what the user actually executed
    rejected_symbols_json = Column(Text, nullable=True)            # symbols user explicitly declined
    override_notes = Column(Text, nullable=True)                   # free-text note for MANUAL_OVERRIDE
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="execution_decisions")
    snapshot = relationship("RecommendationSnapshot", back_populates="decisions")
    shadow_portfolios = relationship("ShadowPortfolio", back_populates="execution_decision")


class ShadowPortfolio(Base):
    """Paper portfolio for tracking hypothetical performance of optimizer recommendations."""
    __tablename__ = "shadow_portfolios"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    # STATIC_FROZEN: frozen snapshot of state at decision time
    # ACTIVE_MODEL:  hypothetical 100%-compliant 3L portfolio, updated each run
    shadow_type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    inception_date = Column(String, nullable=False)                # "YYYY-MM-DD"
    inception_value = Column(Float, nullable=True)
    recommendation_snapshot_id = Column(Integer, ForeignKey("recommendation_snapshots.id", ondelete="SET NULL"), nullable=True)
    execution_decision_id = Column(Integer, ForeignKey("user_execution_decisions.id", ondelete="SET NULL"), nullable=True)
    inception_holdings_json = Column(Text, nullable=True)          # holdings[] at creation time
    paper_cash_balance = Column(Float, nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    last_valued_at = Column(DateTime, nullable=True)
    current_value = Column(Float, nullable=True)
    inception_return_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="shadow_portfolios")
    recommendation_snapshot = relationship("RecommendationSnapshot", back_populates="shadow_portfolios")
    execution_decision = relationship("UserExecutionDecision", back_populates="shadow_portfolios")
    daily_snapshots = relationship("ShadowPortfolioSnapshot", back_populates="shadow_portfolio", cascade="all, delete-orphan")
    attribution_metrics = relationship("AttributionMetric", back_populates="shadow_portfolio", cascade="all, delete-orphan")


class ShadowPortfolioSnapshot(Base):
    """Daily paper-trading valuation for a shadow portfolio."""
    __tablename__ = "shadow_portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    shadow_portfolio_id = Column(Integer, ForeignKey("shadow_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(String, nullable=False, index=True)     # "YYYY-MM-DD"
    total_value = Column(Float, nullable=False)
    return_pct_since_inception = Column(Float, nullable=True)      # cumulative %
    daily_return_pct = Column(Float, nullable=True)
    holdings_json = Column(Text, nullable=True)                    # per-holding values
    benchmark_symbol = Column(String, nullable=True)               # e.g. "^SET.BK" or "^GSPC"
    benchmark_return_pct = Column(Float, nullable=True)            # benchmark cumulative return same period
    alpha = Column(Float, nullable=True)                           # shadow return - benchmark return
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    shadow_portfolio = relationship("ShadowPortfolio", back_populates="daily_snapshots")

    __table_args__ = (UniqueConstraint("shadow_portfolio_id", "snapshot_date", name="uq_shadow_snapshot_date"),)


class AttributionMetric(Base):
    """Brinson-Hood-Beebower alpha attribution — selection vs allocation effects + human-vs-AI comparison."""
    __tablename__ = "attribution_metrics"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    shadow_portfolio_id = Column(Integer, ForeignKey("shadow_portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True, index=True)
    recommendation_snapshot_id = Column(Integer, ForeignKey("recommendation_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    evaluation_period_start = Column(String, nullable=False)       # "YYYY-MM-DD"
    evaluation_period_end = Column(String, nullable=False)         # "YYYY-MM-DD"
    evaluation_window_days = Column(Integer, nullable=True, default=30)
    # BHB alpha decomposition
    portfolio_return = Column(Float, nullable=True)                # shadow portfolio total return
    benchmark_return = Column(Float, nullable=True)                # benchmark total return same period
    selection_alpha = Column(Float, nullable=True)                 # alpha from stock selection vs sector peers
    allocation_alpha = Column(Float, nullable=True)                # alpha from sector/weight tilts
    interaction_effect = Column(Float, nullable=True)              # cross-term (selection × allocation)
    total_alpha = Column(Float, nullable=True)                     # selection + allocation + interaction
    attribution_breakdown_json = Column(Text, nullable=True)       # per-sector BHB components JSON
    # Human-vs-AI comparison fields (Phase 3B.7B)
    actual_return_pct = Column(Float, nullable=True)               # real portfolio return over evaluation window
    static_shadow_return_pct = Column(Float, nullable=True)        # STATIC_FROZEN shadow return same window
    ai_model_return_pct = Column(Float, nullable=True)             # ACTIVE_MODEL shadow return same window
    avoided_drawdown_pct = Column(Float, nullable=True)            # static_drawdown − actual_drawdown (+ = AI had more DD)
    regret_score = Column(Float, nullable=True)                    # ai_model_return − actual_return (+ = AI better)
    ai_outperformed = Column(Boolean, nullable=True)               # regret_score > 0
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="attribution_metrics")
    shadow_portfolio = relationship("ShadowPortfolio", back_populates="attribution_metrics")


class ConfidenceCalibrationRecord(Base):
    """Feedback loop: maps past consensus/policy scores to realized outcomes for re-injection."""
    __tablename__ = "confidence_calibration_records"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    optimizer_history_id = Column(Integer, ForeignKey("optimizer_history.id", ondelete="SET NULL"), nullable=True, index=True)
    recommendation_snapshot_id = Column(Integer, ForeignKey("recommendation_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    lookback_days = Column(Integer, nullable=False, default=30)    # evaluation window
    # Calibration scores: did the AI confidence predict real outcomes?
    consensus_strength_calibration = Column(Float, nullable=True)  # predicted vs realized direction accuracy
    policy_alignment_calibration = Column(Float, nullable=True)    # policy score vs realized compliance
    regime_confidence_calibration = Column(Float, nullable=True)   # regime confidence vs realized regime
    signal_accuracy_json = Column(Text, nullable=True)             # per-symbol {predicted, actual, correct}
    calibration_score = Column(Float, nullable=True)               # 0-100 overall calibration quality
    feedback_context_json = Column(Text, nullable=True)            # structured block to inject into AI prompts
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workspace = relationship("Workspace", back_populates="calibration_records")


class UserUsage(Base):
    __tablename__ = "user_usage"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    operation = Column(String, nullable=False, index=True)  # analyze | optimize | other
    layer = Column(String, nullable=True, index=True)       # layer1 | layer2 | layer3 | null
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    input_cost_usd = Column(Float, nullable=False, default=0.0)
    output_cost_usd = Column(Float, nullable=False, default=0.0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_default_workspace(db) -> Workspace:
    """Return the default workspace, creating it if it does not exist."""
    ws = db.query(Workspace).order_by(Workspace.id).first()
    if ws is None:
        ws = Workspace(name="Default")
        db.add(ws)
        db.commit()
        db.refresh(ws)
    return ws


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def migrate_legacy_data() -> None:
    """Bootstrap data + SQLite-only schema patches.
    On PostgreSQL, schema migrations are managed by Alembic — only data bootstrap runs here."""
    from sqlalchemy import text, inspect as sa_inspect

    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()

    db = SessionLocal()
    try:
        # Ensure default workspace exists first (required by all FK columns below)
        ws = get_default_workspace(db)
        ws_id = ws.id

        # Ensure at least one portfolio ("Main") exists
        if db.query(Portfolio).count() == 0:
            main = Portfolio(name="Main", workspace_id=ws_id)
            db.add(main)
            db.commit()
            db.refresh(main)
        else:
            main = db.query(Portfolio).order_by(Portfolio.id).first()

        # SQLite-only: apply incremental ALTER TABLE patches.
        # PostgreSQL uses Alembic migrations (`alembic upgrade head`) instead.
        if _is_sqlite:
            # ── workspace_id column on every user-owned table ──────────────────
            _ws_tables = (
                "portfolios", "portfolio_items", "watchlist",
                "analysis_cache", "analysis_history", "optimizer_history", "settings",
                "transactions", "portfolio_snapshots", "signal_history",
            )
            for t in _ws_tables:
                if t in tables:
                    cols = {c["name"] for c in inspector.get_columns(t)}
                    if "workspace_id" not in cols:
                        with engine.begin() as conn:
                            conn.execute(text(
                                f"ALTER TABLE {t} ADD COLUMN workspace_id INTEGER NOT NULL DEFAULT 1"
                            ))

            # ── pre-existing column patches ────────────────────────────────────
            if "portfolios" in tables:
                with engine.begin() as conn:
                    p_cols = {c["name"] for c in inspector.get_columns("portfolios")}
                    if "cash_balance" not in p_cols:
                        conn.execute(text("ALTER TABLE portfolios ADD COLUMN cash_balance REAL NOT NULL DEFAULT 0"))
                    if "strategy_persona" not in p_cols:
                        conn.execute(text("ALTER TABLE portfolios ADD COLUMN strategy_persona TEXT DEFAULT 'BALANCED'"))
                    if "goal_target_value" not in p_cols:
                        conn.execute(text("ALTER TABLE portfolios ADD COLUMN goal_target_value REAL"))
                    # Phase 4C.3 Goal Discovery Wizard columns
                    for col in ("goal_type", "goal_priority", "goal_target_date", "risk_personality"):
                        if col not in p_cols:
                            conn.execute(text(f"ALTER TABLE portfolios ADD COLUMN {col} TEXT"))

            if "portfolio_items" in tables:
                with engine.begin() as conn:
                    pi_cols = {c["name"] for c in inspector.get_columns("portfolio_items")}
                    if "allow_swap" not in pi_cols:
                        conn.execute(text("ALTER TABLE portfolio_items ADD COLUMN allow_swap INTEGER NOT NULL DEFAULT 1"))
                    if "sector" not in pi_cols:
                        conn.execute(text("ALTER TABLE portfolio_items ADD COLUMN sector TEXT"))

            if "watchlist" in tables:
                with engine.begin() as conn:
                    wl_cols = {c["name"] for c in inspector.get_columns("watchlist")}
                    if "sector" not in wl_cols:
                        conn.execute(text("ALTER TABLE watchlist ADD COLUMN sector TEXT"))

            if "analysis_cache" in tables:
                with engine.begin() as conn:
                    ac_cols = {c["name"] for c in inspector.get_columns("analysis_cache")}
                    for col, typedef in [("ta_score", "INTEGER"), ("fa_score", "INTEGER"),
                                         ("ai_provider", "TEXT"), ("ai_model", "TEXT"),
                                         ("sources_used", "TEXT"), ("executive_summary", "TEXT"),
                                         ("ai_summary", "TEXT")]:
                        if col not in ac_cols:
                            conn.execute(text(f"ALTER TABLE analysis_cache ADD COLUMN {col} {typedef}"))

            if "analysis_history" in tables:
                with engine.begin() as conn:
                    ah_cols = {c["name"] for c in inspector.get_columns("analysis_history")}
                    for col in ("sources_used", "scores", "executive_summary", "ai_summary"):
                        if col not in ah_cols:
                            conn.execute(text(f"ALTER TABLE analysis_history ADD COLUMN {col} TEXT"))
                    for col in ("latency_ms", "total_latency_ms"):
                        if col not in ah_cols:
                            conn.execute(text(f"ALTER TABLE analysis_history ADD COLUMN {col} INTEGER"))

            if "optimizer_history" in tables:
                with engine.begin() as conn:
                    oh_cols = {c["name"] for c in inspector.get_columns("optimizer_history")}
                    for col in ("ai_provider", "ai_model"):
                        if col not in oh_cols:
                            conn.execute(text(f"ALTER TABLE optimizer_history ADD COLUMN {col} TEXT"))
                    for col in ("layer1_latency_ms", "layer2_latency_ms", "layer3_latency_ms", "total_latency_ms"):
                        if col not in oh_cols:
                            conn.execute(text(f"ALTER TABLE optimizer_history ADD COLUMN {col} INTEGER"))
                    for col in ("optimizer_status", "no_action_reason", "no_action_summary", "blocked_opportunities_json"):
                        if col not in oh_cols:
                            conn.execute(text(f"ALTER TABLE optimizer_history ADD COLUMN {col} TEXT"))
                    if "rebalance_opportunity_score" not in oh_cols:
                        conn.execute(text("ALTER TABLE optimizer_history ADD COLUMN rebalance_opportunity_score INTEGER"))

            if "user_usage" in tables:
                with engine.begin() as conn:
                    uu_cols = {c["name"] for c in inspector.get_columns("user_usage")}
                    for col, typedef, default in [
                        ("input_cost_usd", "REAL", "0"),
                        ("output_cost_usd", "REAL", "0"),
                        ("total_cost_usd", "REAL", "0"),
                        ("total_tokens", "INTEGER", "0"),
                        ("operation", "TEXT", "'other'"),
                    ]:
                        if col not in uu_cols:
                            conn.execute(text(f"ALTER TABLE user_usage ADD COLUMN {col} {typedef} NOT NULL DEFAULT {default}"))
                    if "latency_ms" not in uu_cols:
                        conn.execute(text("ALTER TABLE user_usage ADD COLUMN latency_ms INTEGER"))

            if "signal_history" in tables:
                with engine.begin() as conn:
                    sh_cols = {c["name"] for c in inspector.get_columns("signal_history")}
                    if "price_at_signal" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN price_at_signal REAL"))
                    if "prev_signal" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN prev_signal TEXT"))
                    if "session_id" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN session_id TEXT"))
                    if "action" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN action TEXT"))
                    if "score_at_signal" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN score_at_signal REAL"))
                    if "signal_type" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN signal_type TEXT"))
                    if "reasoning_snippet" not in sh_cols:
                        conn.execute(text("ALTER TABLE signal_history ADD COLUMN reasoning_snippet TEXT"))

            if "portfolio_snapshots" in tables:
                with engine.begin() as conn:
                    ps_cols = {c["name"] for c in inspector.get_columns("portfolio_snapshots")}
                    if "realized_pnl" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN realized_pnl REAL"))
                    if "daily_return_pct" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN daily_return_pct REAL"))
                    if "holdings_json" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN holdings_json TEXT"))
                    if "net_external_cash_flow" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN net_external_cash_flow REAL"))
                    if "investment_return_pct" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN investment_return_pct REAL"))
                    if "investment_return_amount" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN investment_return_amount REAL"))
                    if "imported_asset_value" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN imported_asset_value REAL"))
                    if "manual_adjustment_value" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN manual_adjustment_value REAL"))
                    if "period_realized_pnl" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN period_realized_pnl REAL"))
                    if "period_dividend_income" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN period_dividend_income REAL"))
                    if "period_fees_paid" not in ps_cols:
                        conn.execute(text("ALTER TABLE portfolio_snapshots ADD COLUMN period_fees_paid REAL"))

            if "transactions" in tables:
                with engine.begin() as conn:
                    tx_cols = {c["name"] for c in inspector.get_columns("transactions")}
                    if "taxes" not in tx_cols:
                        conn.execute(text("ALTER TABLE transactions ADD COLUMN taxes REAL DEFAULT 0"))
                    if "currency" not in tx_cols:
                        conn.execute(text("ALTER TABLE transactions ADD COLUMN currency TEXT DEFAULT 'THB'"))
                    if "exchange_rate" not in tx_cols:
                        conn.execute(text("ALTER TABLE transactions ADD COLUMN exchange_rate REAL DEFAULT 1.0"))

            # market_data_cache: production-grade yfinance response cache
            if "market_data_cache" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS market_data_cache (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            cache_type TEXT NOT NULL,
                            payload_json TEXT NOT NULL,
                            fetched_at DATETIME NOT NULL,
                            expires_at DATETIME NOT NULL,
                            hit_count INTEGER NOT NULL DEFAULT 0,
                            UNIQUE (symbol, cache_type)
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mdc_symbol ON market_data_cache (symbol)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mdc_expires ON market_data_cache (expires_at)"))

            # regime_snapshots: daily market regime detection history
            if "regime_snapshots" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS regime_snapshots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            snapshot_date TEXT NOT NULL,
                            regime TEXT NOT NULL,
                            confidence REAL NOT NULL,
                            trend_score REAL,
                            volatility_score REAL,
                            drawdown_score REAL,
                            momentum_score REAL,
                            vol_z_score REAL,
                            ema_alignment REAL,
                            regime_duration_days INTEGER,
                            previous_regime TEXT,
                            transition_stability TEXT,
                            signals_json TEXT,
                            created_at DATETIME,
                            UNIQUE (snapshot_date)
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_regime_snapshots_date ON regime_snapshots (snapshot_date)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_regime_snapshots_regime ON regime_snapshots (regime)"))

            # ── Phase 3B.7 Decision Memory tables ─────────────────────────────
            if "recommendation_snapshots" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS recommendation_snapshots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workspace_id INTEGER NOT NULL DEFAULT 1,
                            optimizer_history_id INTEGER NOT NULL,
                            portfolio_id INTEGER NOT NULL,
                            persona TEXT,
                            total_portfolio_value REAL,
                            regime_snapshot_json TEXT,
                            constraint_envelope_json TEXT,
                            active_policy_json TEXT,
                            layer1_output_json TEXT,
                            layer2_output_json TEXT,
                            layer3_output_json TEXT,
                            consensus_json TEXT,
                            portfolio_dna_json TEXT,
                            style_drift_json TEXT,
                            scores_map_json TEXT,
                            projected_allocations_json TEXT,
                            created_at DATETIME,
                            UNIQUE (optimizer_history_id)
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rec_snap_ws ON recommendation_snapshots (workspace_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rec_snap_portfolio ON recommendation_snapshots (portfolio_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rec_snap_oh ON recommendation_snapshots (optimizer_history_id)"))

            if "user_execution_decisions" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS user_execution_decisions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workspace_id INTEGER NOT NULL DEFAULT 1,
                            recommendation_snapshot_id INTEGER NOT NULL,
                            optimizer_history_id INTEGER,
                            portfolio_id INTEGER NOT NULL,
                            decision TEXT NOT NULL,
                            approved_allocations_json TEXT,
                            rejected_symbols_json TEXT,
                            override_notes TEXT,
                            executed_at DATETIME NOT NULL,
                            created_at DATETIME
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ued_ws ON user_execution_decisions (workspace_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ued_snapshot ON user_execution_decisions (recommendation_snapshot_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ued_decision ON user_execution_decisions (decision)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ued_portfolio ON user_execution_decisions (portfolio_id)"))

            if "shadow_portfolios" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS shadow_portfolios (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workspace_id INTEGER NOT NULL DEFAULT 1,
                            portfolio_id INTEGER NOT NULL,
                            shadow_type TEXT NOT NULL,
                            name TEXT NOT NULL,
                            inception_date TEXT NOT NULL,
                            inception_value REAL,
                            recommendation_snapshot_id INTEGER,
                            execution_decision_id INTEGER,
                            inception_holdings_json TEXT,
                            paper_cash_balance REAL NOT NULL DEFAULT 0,
                            is_active INTEGER NOT NULL DEFAULT 1,
                            last_valued_at DATETIME,
                            current_value REAL,
                            inception_return_pct REAL,
                            created_at DATETIME
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sp_ws ON shadow_portfolios (workspace_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sp_portfolio ON shadow_portfolios (portfolio_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sp_type ON shadow_portfolios (shadow_type)"))

            if "shadow_portfolio_snapshots" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS shadow_portfolio_snapshots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            shadow_portfolio_id INTEGER NOT NULL,
                            snapshot_date TEXT NOT NULL,
                            total_value REAL NOT NULL,
                            return_pct_since_inception REAL,
                            daily_return_pct REAL,
                            holdings_json TEXT,
                            benchmark_symbol TEXT,
                            benchmark_return_pct REAL,
                            alpha REAL,
                            created_at DATETIME,
                            UNIQUE (shadow_portfolio_id, snapshot_date)
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sps_shadow ON shadow_portfolio_snapshots (shadow_portfolio_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sps_date ON shadow_portfolio_snapshots (snapshot_date)"))

            if "attribution_metrics" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS attribution_metrics (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workspace_id INTEGER NOT NULL DEFAULT 1,
                            shadow_portfolio_id INTEGER NOT NULL,
                            portfolio_id INTEGER,
                            recommendation_snapshot_id INTEGER,
                            evaluation_period_start TEXT NOT NULL,
                            evaluation_period_end TEXT NOT NULL,
                            evaluation_window_days INTEGER DEFAULT 30,
                            portfolio_return REAL,
                            benchmark_return REAL,
                            selection_alpha REAL,
                            allocation_alpha REAL,
                            interaction_effect REAL,
                            total_alpha REAL,
                            attribution_breakdown_json TEXT,
                            actual_return_pct REAL,
                            static_shadow_return_pct REAL,
                            ai_model_return_pct REAL,
                            avoided_drawdown_pct REAL,
                            regret_score REAL,
                            ai_outperformed INTEGER,
                            computed_at DATETIME
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_am_ws ON attribution_metrics (workspace_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_am_shadow ON attribution_metrics (shadow_portfolio_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_am_portfolio ON attribution_metrics (portfolio_id)"))
            else:
                # Add new columns to existing attribution_metrics table
                with engine.begin() as conn:
                    am_cols = {c["name"] for c in inspector.get_columns("attribution_metrics")}
                    for col, typedef in [
                        ("portfolio_id", "INTEGER"),
                        ("recommendation_snapshot_id", "INTEGER"),
                        ("evaluation_window_days", "INTEGER"),
                        ("actual_return_pct", "REAL"),
                        ("static_shadow_return_pct", "REAL"),
                        ("ai_model_return_pct", "REAL"),
                        ("avoided_drawdown_pct", "REAL"),
                        ("regret_score", "REAL"),
                        ("ai_outperformed", "INTEGER"),
                    ]:
                        if col not in am_cols:
                            conn.execute(text(f"ALTER TABLE attribution_metrics ADD COLUMN {col} {typedef}"))

            if "confidence_calibration_records" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS confidence_calibration_records (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            workspace_id INTEGER NOT NULL DEFAULT 1,
                            optimizer_history_id INTEGER,
                            recommendation_snapshot_id INTEGER,
                            lookback_days INTEGER NOT NULL DEFAULT 30,
                            consensus_strength_calibration REAL,
                            policy_alignment_calibration REAL,
                            regime_confidence_calibration REAL,
                            signal_accuracy_json TEXT,
                            calibration_score REAL,
                            feedback_context_json TEXT,
                            computed_at DATETIME
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccr_ws ON confidence_calibration_records (workspace_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ccr_oh ON confidence_calibration_records (optimizer_history_id)"))

            # benchmark_prices: create if missing (SQLite has no CREATE TABLE IF NOT EXISTS in ALTER path)
            if "benchmark_prices" not in tables:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS benchmark_prices (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT NOT NULL,
                            price_date TEXT NOT NULL,
                            close_price REAL NOT NULL,
                            created_at DATETIME,
                            updated_at DATETIME,
                            data_source TEXT,
                            sync_status TEXT,
                            UNIQUE (symbol, price_date)
                        )
                    """))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_benchmark_prices_symbol ON benchmark_prices (symbol)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_benchmark_prices_price_date ON benchmark_prices (price_date)"))
            else:
                # Phase S.3: add freshness columns to existing table
                with engine.begin() as conn:
                    bp_cols = {c["name"] for c in inspector.get_columns("benchmark_prices")}
                    for col, typedef in [
                        ("updated_at", "DATETIME"),
                        ("data_source", "TEXT"),
                        ("sync_status", "TEXT"),
                    ]:
                        if col not in bp_cols:
                            conn.execute(text(f"ALTER TABLE benchmark_prices ADD COLUMN {col} {typedef}"))

        # Data migration: copy from old flat 'portfolio' table if it still exists (both DB types)
        if "portfolio" in tables:
            existing = {item.symbol for item in db.query(PortfolioItem).filter_by(portfolio_id=main.id).all()}
            try:
                rows = db.execute(text("SELECT symbol, shares, avg_cost FROM portfolio")).fetchall()
                for row in rows:
                    if row.symbol not in existing:
                        db.add(PortfolioItem(
                            workspace_id=ws_id,
                            portfolio_id=main.id,
                            symbol=row.symbol,
                            shares=row.shares,
                            avg_cost=row.avg_cost,
                        ))
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()
