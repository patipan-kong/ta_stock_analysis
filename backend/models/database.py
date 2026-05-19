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

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("PortfolioItem", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    shares = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    allow_swap = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="items")

    __table_args__ = (UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),)


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentCache(Base):
    """Caches raw agent results (TA / FA / News) with per-agent TTLs."""
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
    symbol = Column(String, unique=True, index=True, nullable=False)
    signal = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    reasoning = Column(Text, nullable=False)
    risks = Column(Text, nullable=False)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ta_score = Column(Integer, nullable=True)
    fa_score = Column(Integer, nullable=True)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    sources_used = Column(Text, nullable=True)


class OptimizerHistory(Base):
    __tablename__ = "optimizer_history"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_name = Column(String, nullable=False)
    analyzed_at = Column(DateTime, nullable=False)
    swap_count = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=False)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    signal = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    reasoning = Column(Text, nullable=False)
    risks = Column(Text, nullable=False)
    ta_score = Column(Integer, nullable=True)
    fa_score = Column(Integer, nullable=True)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    sources_used = Column(Text, nullable=True)
    scores = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)


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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def migrate_legacy_data() -> None:
    """One-time migration: copy old 'portfolio' table rows into new multi-portfolio schema."""
    from sqlalchemy import text, inspect as sa_inspect

    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()

    db = SessionLocal()
    try:
        # Ensure at least one portfolio ("Main") exists
        if db.query(Portfolio).count() == 0:
            main = Portfolio(name="Main")
            db.add(main)
            db.commit()
            db.refresh(main)
        else:
            main = db.query(Portfolio).order_by(Portfolio.id).first()

        # Add allow_swap column to portfolio_items if not exists
        if "portfolio_items" in tables:
            with engine.begin() as conn:
                pi_cols = {c["name"] for c in inspector.get_columns("portfolio_items")}
                if "allow_swap" not in pi_cols:
                    conn.execute(text("ALTER TABLE portfolio_items ADD COLUMN allow_swap INTEGER NOT NULL DEFAULT 1"))

        # Add columns to analysis_cache if they don't exist yet
        if "analysis_cache" in tables:
            with engine.begin() as conn:
                ac_cols = {c["name"] for c in inspector.get_columns("analysis_cache")}
                for col, typedef in [("ta_score", "INTEGER"), ("fa_score", "INTEGER"),
                                     ("ai_provider", "TEXT"), ("ai_model", "TEXT"),
                                     ("sources_used", "TEXT")]:
                    if col not in ac_cols:
                        conn.execute(text(f"ALTER TABLE analysis_cache ADD COLUMN {col} {typedef}"))

        # Add sources_used and scores to analysis_history if missing
        if "analysis_history" in tables:
            with engine.begin() as conn:
                ah_cols = {c["name"] for c in inspector.get_columns("analysis_history")}
                for col in ("sources_used", "scores"):
                    if col not in ah_cols:
                        conn.execute(text(f"ALTER TABLE analysis_history ADD COLUMN {col} TEXT"))

        # Add ai columns to optimizer_history if they don't exist yet
        if "optimizer_history" in tables:
            with engine.begin() as conn:
                oh_cols = {c["name"] for c in inspector.get_columns("optimizer_history")}
                for col in ("ai_provider", "ai_model"):
                    if col not in oh_cols:
                        conn.execute(text(f"ALTER TABLE optimizer_history ADD COLUMN {col} TEXT"))

        # Add usage cost columns if legacy user_usage table exists with missing fields
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

        # Migrate rows from old flat 'portfolio' table if it still exists
        if "portfolio" in tables:
            existing = {item.symbol for item in db.query(PortfolioItem).filter_by(portfolio_id=main.id).all()}
            try:
                rows = db.execute(text("SELECT symbol, shares, avg_cost FROM portfolio")).fetchall()
                for row in rows:
                    if row.symbol not in existing:
                        db.add(PortfolioItem(
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
