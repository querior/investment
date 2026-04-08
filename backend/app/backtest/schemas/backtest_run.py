import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, Integer, String, Date, DateTime, Float, Enum, ForeignKey, func
from typing import TYPE_CHECKING
from app.db.session import Base

if TYPE_CHECKING:
    from app.backtest.schemas.backtest_portfolio_performance import BacktestPortfolioPerformance
    from app.backtest.schemas.backtest_position import BacktestPosition


class BacktestInstrument(str, enum.Enum):
    OPTIONS = "options"  
    FUTURES = "futures"
    
class BacktestFrequency(str, enum.Enum):
    EOM = "EOM"  # End of Month
    EOW = "EOW"  # End of Week
    EOD = "EOD"  # End of Day


class BacktestStatus(str, enum.Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[int] = mapped_column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)

    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)
    frequency: Mapped[BacktestFrequency] = mapped_column(Enum(BacktestFrequency, native_enum=False), nullable=False, default=BacktestFrequency.EOM)
    config_snapshot: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[BacktestStatus] = mapped_column(Enum(BacktestStatus, native_enum=False), nullable=False, default=BacktestStatus.READY)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    cagr: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    positions: Mapped[list["BacktestPosition"]] = relationship(
        "BacktestPosition",
        back_populates="run",
        cascade="all, delete-orphan",
    )

    portfolio_performances: Mapped[list["BacktestPortfolioPerformance"]] = relationship(
        "BacktestPortfolioPerformance",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="BacktestPortfolioPerformance.snapshot_date",
    )
