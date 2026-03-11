from app.db.session import engine, Base

# importa ESPLICITAMENTE solo i modelli backtest
from app.backtest.schemas.backtest_run import BacktestRun
from app.backtest.schemas.backtest_weight import BacktestWeight
from app.backtest.schemas.backtest_performance import BacktestPerformance


def init_backtest_db():
    Base.metadata.create_all(
        bind=engine,
        tables=[
            BacktestRun.__table__,
            BacktestWeight.__table__,
            BacktestPerformance.__table__,
        ],
    )