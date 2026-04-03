import enum
from sqlalchemy import Boolean, Column, Integer, String, Date, DateTime, Float, Enum, ForeignKey, func
from app.db.session import Base


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

    id = Column(Integer, primary_key=True)
    backtest_id = Column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    frequency = Column(Enum(BacktestFrequency, native_enum=False), nullable=False, default=BacktestFrequency.EOM)
    config_snapshot = Column(String, nullable=True)  # JSON: matrice sensitività + neutral + params
    status = Column(Enum(BacktestStatus, native_enum=False), nullable=False, default=BacktestStatus.READY)
    stop_requested = Column(Boolean, nullable=False, default=False)
    notes = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # metriche aggregate (aggiornate ad ogni ciclo)
    cagr = Column(Float)
    volatility = Column(Float)
    sharpe = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    n_trades = Column(Integer)
