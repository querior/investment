from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
  
from app.backtest.schemas.backtest_position import BacktestPosition
from app.backtest.schemas.backtest_run import BacktestRun


class BacktestPositionSnapshot(Base):
    __tablename__ = "backtest_position_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    underlying_price: Mapped[float] = mapped_column(Float, nullable=False)
    iv: Mapped[float] = mapped_column(Float, nullable=False)

    position_price: Mapped[float] = mapped_column(Float, nullable=False)
    position_pnl: Mapped[float] = mapped_column(Float, nullable=False)

    position_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_gamma: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_theta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_vega: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    min_dte: Mapped[float] = mapped_column(Float, nullable=False)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped["BacktestRun"] = relationship("BacktestRun")
    position: Mapped["BacktestPosition"] = relationship(
        "BacktestPosition",
        back_populates="snapshots",
    )