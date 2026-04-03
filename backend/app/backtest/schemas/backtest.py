from sqlalchemy import Enum, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.backtest.schemas.backtest_run import BacktestFrequency
from datetime import datetime

class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    instrument: Mapped[str | None] = mapped_column(String, nullable=True)
    strategy_version: Mapped[str] = mapped_column(String, nullable=False, default="v1")
    frequency: Mapped[BacktestFrequency] = mapped_column(
        Enum(BacktestFrequency, native_enum=False),
        nullable=False,
        default=BacktestFrequency.EOM,
    )

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
