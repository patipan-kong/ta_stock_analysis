"""Copy portfolio id=4 (TA) → id=5 (TA-test) with all related rows."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import (
    SessionLocal, Portfolio, PortfolioItem, Transaction,
    PortfolioSnapshot, OptimizerHistory, RecommendationSnapshot,
    UserExecutionDecision, ShadowPortfolio, SignalHistory,
)
from sqlalchemy import text

SRC_ID = 4
DST_ID = 5
DST_NAME = "TA-test"


def main():
    db = SessionLocal()
    try:
        src = db.query(Portfolio).filter(Portfolio.id == SRC_ID).first()
        assert src, f"Portfolio {SRC_ID} not found"
        print(f"Source: id={src.id} name={src.name} persona={src.strategy_persona} cash={src.cash_balance}")

        # ── Portfolio row ──────────────────────────────────────────────────────
        dst = db.query(Portfolio).filter(Portfolio.id == DST_ID).first()
        if dst:
            print(f"Portfolio {DST_ID} already exists ({dst.name!r}), updating metadata")
            dst.name = DST_NAME
            dst.strategy_persona = src.strategy_persona
            dst.cash_balance = src.cash_balance
            db.commit()
        else:
            db.execute(text(
                "INSERT INTO portfolios (id, workspace_id, name, cash_balance, strategy_persona, created_at) "
                f"VALUES (:dst_id, :ws_id, :name, :cash, :persona, NOW())"
            ), {"dst_id": DST_ID, "ws_id": src.workspace_id, "name": DST_NAME,
                "cash": src.cash_balance, "persona": src.strategy_persona})
            db.commit()
            # Reset sequence so future auto-inserts don't collide
            db.execute(text(
                "SELECT setval(pg_get_serial_sequence('portfolios','id'), (SELECT MAX(id) FROM portfolios))"
            ))
            db.commit()
            print(f"Created portfolio {DST_ID}")

        # ── PortfolioItems ─────────────────────────────────────────────────────
        db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == DST_ID).delete()
        db.commit()
        items = db.query(PortfolioItem).filter(PortfolioItem.portfolio_id == SRC_ID).all()
        for i in items:
            db.add(PortfolioItem(
                workspace_id=i.workspace_id, portfolio_id=DST_ID,
                symbol=i.symbol, shares=i.shares, avg_cost=i.avg_cost,
                allow_swap=i.allow_swap, sector=i.sector, created_at=i.created_at,
            ))
        db.commit()
        print(f"Copied {len(items)} portfolio_items")

        # ── Transactions ───────────────────────────────────────────────────────
        db.query(Transaction).filter(Transaction.portfolio_id == DST_ID).delete()
        db.commit()
        txs = db.query(Transaction).filter(Transaction.portfolio_id == SRC_ID).all()
        for t in txs:
            db.add(Transaction(
                workspace_id=t.workspace_id, portfolio_id=DST_ID,
                symbol=t.symbol, transaction_type=t.transaction_type,
                shares=t.shares, price_per_share=t.price_per_share,
                total_amount=t.total_amount, fees=t.fees, taxes=t.taxes,
                currency=t.currency, exchange_rate=t.exchange_rate,
                transaction_date=t.transaction_date, notes=t.notes,
                sector=t.sector, created_at=t.created_at,
            ))
        db.commit()
        print(f"Copied {len(txs)} transactions")

        # ── PortfolioSnapshots ─────────────────────────────────────────────────
        db.query(PortfolioSnapshot).filter(PortfolioSnapshot.portfolio_id == DST_ID).delete()
        db.commit()
        snaps = db.query(PortfolioSnapshot).filter(PortfolioSnapshot.portfolio_id == SRC_ID).all()
        for s in snaps:
            db.add(PortfolioSnapshot(
                workspace_id=s.workspace_id, portfolio_id=DST_ID,
                snapshot_date=s.snapshot_date, total_value=s.total_value,
                cash_balance=s.cash_balance, total_invested=s.total_invested,
                unrealized_pnl=s.unrealized_pnl, unrealized_pnl_pct=s.unrealized_pnl_pct,
                realized_pnl=s.realized_pnl, daily_return_pct=s.daily_return_pct,
                sector_breakdown_json=s.sector_breakdown_json,
                holdings_json=s.holdings_json, holdings_count=s.holdings_count,
                created_at=s.created_at,
            ))
        db.commit()
        print(f"Copied {len(snaps)} portfolio_snapshots")

        # ── OptimizerHistory ──────────────────────────────────────────────────
        # Must delete RecommendationSnapshots first (FK → optimizer_history)
        db.query(RecommendationSnapshot).filter(RecommendationSnapshot.portfolio_id == DST_ID).delete()
        db.commit()
        db.query(OptimizerHistory).filter(OptimizerHistory.portfolio_id == DST_ID).delete()
        db.commit()

        oh_rows = db.query(OptimizerHistory).filter(OptimizerHistory.portfolio_id == SRC_ID).all()
        old_to_new_oh: dict[int, int] = {}
        for oh in oh_rows:
            new_oh = OptimizerHistory(
                workspace_id=oh.workspace_id, portfolio_id=DST_ID,
                portfolio_name=DST_NAME, analyzed_at=oh.analyzed_at,
                swap_count=oh.swap_count, result_json=oh.result_json,
                ai_provider=oh.ai_provider, ai_model=oh.ai_model,
                layer1_latency_ms=oh.layer1_latency_ms,
                layer2_latency_ms=oh.layer2_latency_ms,
                layer3_latency_ms=oh.layer3_latency_ms,
                total_latency_ms=oh.total_latency_ms,
                optimizer_status=oh.optimizer_status,
                rebalance_opportunity_score=oh.rebalance_opportunity_score,
                no_action_reason=oh.no_action_reason,
                no_action_summary=oh.no_action_summary,
                blocked_opportunities_json=oh.blocked_opportunities_json,
            )
            db.add(new_oh)
            db.flush()
            old_to_new_oh[oh.id] = new_oh.id
        db.commit()
        print(f"Copied {len(oh_rows)} optimizer_history rows")
        print(f"  ID map: {old_to_new_oh}")

        # ── RecommendationSnapshots ────────────────────────────────────────────
        rs_rows = db.query(RecommendationSnapshot).filter(
            RecommendationSnapshot.portfolio_id == SRC_ID
        ).all()
        copied_rs = 0
        for rs in rs_rows:
            new_oh_id = old_to_new_oh.get(rs.optimizer_history_id)
            if not new_oh_id:
                print(f"  Skip RS {rs.id}: no mapped OH for oh_id={rs.optimizer_history_id}")
                continue
            db.add(RecommendationSnapshot(
                workspace_id=rs.workspace_id, optimizer_history_id=new_oh_id,
                portfolio_id=DST_ID, persona=rs.persona,
                total_portfolio_value=rs.total_portfolio_value,
                regime_snapshot_json=rs.regime_snapshot_json,
                constraint_envelope_json=rs.constraint_envelope_json,
                active_policy_json=rs.active_policy_json,
                layer1_output_json=rs.layer1_output_json,
                layer2_output_json=rs.layer2_output_json,
                layer3_output_json=rs.layer3_output_json,
                consensus_json=rs.consensus_json,
                portfolio_dna_json=rs.portfolio_dna_json,
                style_drift_json=rs.style_drift_json,
                scores_map_json=rs.scores_map_json,
                projected_allocations_json=rs.projected_allocations_json,
                created_at=rs.created_at,
            ))
            copied_rs += 1
        db.commit()
        print(f"Copied {copied_rs} recommendation_snapshots")

        # ── UserExecutionDecisions ────────────────────────────────────────────
        ud_rows = db.query(UserExecutionDecision).filter(
            UserExecutionDecision.portfolio_id == SRC_ID
        ).all()
        if ud_rows:
            db.query(UserExecutionDecision).filter(
                UserExecutionDecision.portfolio_id == DST_ID
            ).delete()
            db.commit()
            for ud in ud_rows:
                db.add(UserExecutionDecision(
                    workspace_id=ud.workspace_id, portfolio_id=DST_ID,
                    recommendation_snapshot_id=ud.recommendation_snapshot_id,
                    optimizer_history_id=ud.optimizer_history_id,
                    decision=ud.decision,
                    approved_allocations_json=ud.approved_allocations_json,
                    rejected_symbols_json=ud.rejected_symbols_json,
                    override_notes=ud.override_notes,
                    override_type=ud.override_type,
                    original_symbol=ud.original_symbol,
                    replacement_symbol=ud.replacement_symbol,
                    reason_category=ud.reason_category,
                    executed_at=ud.executed_at, created_at=ud.created_at,
                ))
            db.commit()
            print(f"Copied {len(ud_rows)} user_execution_decisions")
        else:
            print("No user_execution_decisions to copy")

        # ── ShadowPortfolios ──────────────────────────────────────────────────
        sp_rows = db.query(ShadowPortfolio).filter(
            ShadowPortfolio.portfolio_id == SRC_ID
        ).all()
        if sp_rows:
            db.query(ShadowPortfolio).filter(ShadowPortfolio.portfolio_id == DST_ID).delete()
            db.commit()
            for sp in sp_rows:
                db.add(ShadowPortfolio(
                    workspace_id=sp.workspace_id, portfolio_id=DST_ID,
                    shadow_type=sp.shadow_type, name=sp.name,
                    inception_date=sp.inception_date, inception_value=sp.inception_value,
                    recommendation_snapshot_id=sp.recommendation_snapshot_id,
                    execution_decision_id=sp.execution_decision_id,
                    inception_holdings_json=sp.inception_holdings_json,
                    paper_cash_balance=sp.paper_cash_balance,
                    is_active=sp.is_active, last_valued_at=sp.last_valued_at,
                    current_value=sp.current_value,
                    inception_return_pct=sp.inception_return_pct,
                    created_at=sp.created_at,
                ))
            db.commit()
            print(f"Copied {len(sp_rows)} shadow_portfolios")
        else:
            print("No shadow_portfolios to copy")

        # ── SignalHistory (via session_id = str(optimizer_history.id)) ─────────
        old_session_ids = [str(k) for k in old_to_new_oh.keys()]
        if old_session_ids:
            new_session_ids = [str(v) for v in old_to_new_oh.values()]
            for sid in new_session_ids:
                db.query(SignalHistory).filter(SignalHistory.session_id == sid).delete()
            db.commit()
            sh_rows = db.query(SignalHistory).filter(
                SignalHistory.session_id.in_(old_session_ids)
            ).all()
            for sh in sh_rows:
                new_sid = str(old_to_new_oh[int(sh.session_id)])
                db.add(SignalHistory(
                    workspace_id=sh.workspace_id, session_id=new_sid,
                    symbol=sh.symbol, sector=sh.sector, action=sh.action,
                    signal=sh.signal, prev_signal=sh.prev_signal,
                    signal_type=sh.signal_type, confidence=sh.confidence,
                    ta_score=sh.ta_score, fa_score=sh.fa_score,
                    score_at_signal=sh.score_at_signal,
                    ai_provider=sh.ai_provider, ai_model=sh.ai_model,
                    price_at_signal=sh.price_at_signal,
                    reasoning_snippet=sh.reasoning_snippet,
                    recorded_at=sh.recorded_at,
                ))
            db.commit()
            print(f"Copied {len(sh_rows)} signal_history rows")
        else:
            print("No signal_history rows to copy")

        print("\n=== DONE ===")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
