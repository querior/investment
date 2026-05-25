from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime
from app.db.session import Base


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id                      : Mapped[int]   = mapped_column(Integer, primary_key=True)
    run_id                  : Mapped[int]   = mapped_column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"))
    date                    : Mapped[str]   = mapped_column(String)

    # Market regime (L1)
    zone                    : Mapped[str]   = mapped_column(String, nullable=True)
    trend                   : Mapped[str]   = mapped_column(String, nullable=True)
    iv_rank                 : Mapped[float] = mapped_column(Float, nullable=True)
    adx                     : Mapped[float] = mapped_column(Float, nullable=True)

    # Entry scoring (L2)
    entry_score             : Mapped[float] = mapped_column(Float, nullable=True)

    # Strategy selection (L2)
    strategy_name           : Mapped[str]   = mapped_column(String)
    size_multiplier         : Mapped[float] = mapped_column(Float, default=0.0)
    should_trade            : Mapped[bool]  = mapped_column(default=False)

    # Pricing (L3)
    spot                    : Mapped[float] = mapped_column(Float, nullable=True)
    iv                      : Mapped[float] = mapped_column(Float, nullable=True)
    dte_days                : Mapped[int]   = mapped_column(Integer, nullable=True)
    delta                   : Mapped[float] = mapped_column(Float, nullable=True)
    gamma                   : Mapped[float] = mapped_column(Float, nullable=True)
    vega                    : Mapped[float] = mapped_column(Float, nullable=True)
    theta                   : Mapped[float] = mapped_column(Float, nullable=True)
    bid_ask_spread          : Mapped[float] = mapped_column(Float, nullable=True)
    bid_ask_pct             : Mapped[float] = mapped_column(Float, nullable=True)
    edge                    : Mapped[float] = mapped_column(Float, nullable=True)
    breakeven_distance      : Mapped[float] = mapped_column(Float, nullable=True)

    # Pricing source — see ADR 004
    edge_source             : Mapped[str]   = mapped_column(String, nullable=True)

    # Decision Engine (L4-L5)
    decision_action         : Mapped[str]   = mapped_column(String)
    decision_score          : Mapped[float] = mapped_column(Float, default=0.0)
    decision_reasoning      : Mapped[str]   = mapped_column(Text, nullable=True)

    # Opportunity evaluation sub-scores (L4) — see opportunity_evaluator.py
    pricing_edge_score      : Mapped[float] = mapped_column(Float, nullable=True)
    risk_reward_score       : Mapped[float] = mapped_column(Float, nullable=True)
    breakeven_score         : Mapped[float] = mapped_column(Float, nullable=True)
    execution_cost_score    : Mapped[float] = mapped_column(Float, nullable=True)
    capital_efficiency_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at              : Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
