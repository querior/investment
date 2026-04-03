from sqlalchemy import Column, Enum, Integer, String, DateTime, func
from app.db.session import Base
from app.backtest.schemas.backtest_run import BacktestFrequency


class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    strategy_version = Column(String, nullable=False, default="v1")
    frequency = Column(Enum(BacktestFrequency, native_enum=False), nullable=False, default=BacktestFrequency.EOM)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
