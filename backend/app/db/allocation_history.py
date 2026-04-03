from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, Integer, String, Float, ForeignKey
from app.db.session import Base
import datetime


class AllocationHistory(Base):
    __tablename__ = "allocation_history"

    id        : Mapped[int]           = mapped_column(Integer, primary_key=True)
    date      : Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    asset     : Mapped[str]           = mapped_column(String, nullable=False)
    run_id    : Mapped[int | None]    = mapped_column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    target    : Mapped[float]         = mapped_column(Float, nullable=False)
    effective : Mapped[float]         = mapped_column(Float, nullable=False)