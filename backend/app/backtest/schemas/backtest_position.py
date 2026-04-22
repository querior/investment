from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
if TYPE_CHECKING:
    from .backtest_run import BacktestRun
    from .backtest_position_snapshot import BacktestPositionSnapshot
    from .option_strategy import OptionStrategy

class BacktestPosition(Base):
    __tablename__ = "backtest_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position_type: Mapped[Optional[str]] = mapped_column(
        ForeignKey("option_strategies.type", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    opened_at: Mapped[date] = mapped_column(Date, nullable=False)
    closed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    entry_underlying: Mapped[float] = mapped_column(Float, nullable=False)
    entry_iv: Mapped[float] = mapped_column(Float, nullable=False)
    entry_macro_regime: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    initial_value: Mapped[float] = mapped_column(Float, nullable=False)
    close_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    entry_conditions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    exit_conditions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    entry_fair_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_ev_gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_ev_net: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_prob_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_transaction_costs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    run: Mapped["BacktestRun"] = relationship(
        "BacktestRun",
        back_populates="positions",
    )

    strategy: Mapped[Optional["OptionStrategy"]] = relationship(
        "OptionStrategy",
        foreign_keys="[BacktestPosition.position_type]",
    )

    snapshots: Mapped[list["BacktestPositionSnapshot"]] = relationship(
        "BacktestPositionSnapshot",
        back_populates="position",
        cascade="all, delete-orphan",
        order_by="BacktestPositionSnapshot.snapshot_date",
    )