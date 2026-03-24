from sqlalchemy import Column, Integer, ForeignKey, Date, Float
from app.db.session import Base

class BacktestPerformance(Base):
    __tablename__ ="backtest_performance"

    run_id = Column(
        Integer,
        ForeignKey("backtest_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    date = Column(Date, primary_key=True)

    nav = Column(Float, nullable=False)
    monthly_return = Column(Float, nullable=False)