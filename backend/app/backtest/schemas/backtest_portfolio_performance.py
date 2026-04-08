from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.backtest.schemas.backtest_run import BacktestRun


class BacktestPortfolioPerformance(Base):
    __tablename__ = "backtest_portfolio_performances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    cash: Mapped[float] = mapped_column(Float, nullable=False)
    positions_value: Mapped[float] = mapped_column(Float, nullable=False)
    total_equity: Mapped[float] = mapped_column(Float, nullable=False)

    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    total_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_gamma: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_theta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_vega: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    open_positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closed_positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    underlying_price: Mapped[float] = mapped_column(Float, nullable=False)
    iv: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    run: Mapped["BacktestRun"] = relationship(
        "BacktestRun",
        back_populates="portfolio_performances",
    )