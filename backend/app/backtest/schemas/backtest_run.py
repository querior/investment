from sqlalchemy import Column, Integer, String, Date, DateTime, Float, func
from app.db.session import Base


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)
    strategy_version = Column(String, nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # metriche aggregate (post-run)
    cagr = Column(Float)
    volatility = Column(Float)
    sharpe = Column(Float)
    max_drawdown = Column(Float)