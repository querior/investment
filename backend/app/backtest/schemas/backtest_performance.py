from sqlalchemy import Column, Integer, ForeignKey, Date, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class BacktestPerformance(Base):
    __tablename__ ="backtest_performance"

    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"),primary_key=True,)
    date: Mapped[Date] = mapped_column(Date, primary_key=True)

    nav: Mapped[Float] = mapped_column(Float, nullable=False)
    period_return: Mapped[Float] = mapped_column(Float, nullable=False)