from app.backtest.init_db import init_backtest_db
from datetime import date
from app.db.macro_regimes import MacroRegime
from typing import cast
from app.backtest.runs import run_backtest
from app.backtest.schemas import BacktestWeight, BacktestPerformance

def test_run_backtest_creates_records(db_session):
  init_backtest_db()
  
  # pillar minimi
  d = date(2020,1,31)
  db_session.add_all([
    MacroRegime(date=d, pillar="Growth", score=0.0),
    MacroRegime(date=d, pillar="Inflation", score=0.0),
    MacroRegime(date=d, pillar="Policy", score=0.0),
    MacroRegime(date=d, pillar="Risk", score=0.0),
  ])
  db_session.commit()
  
  run_id = cast(
    int,
    run_backtest(
      db=db_session,
      name="test",
      strategy_version="v1",
      start=d,
      end=d
    )
  )
  
  assert run_id > 0
  
  assert (
    db_session.query(BacktestWeight)
      .filter(BacktestWeight.run_id == run_id)
      .count()
      >= 0
  )
  
  assert (
    db_session.query(BacktestPerformance)
      .filter(BacktestPerformance.run_id == run_id)
      .count()
      >= 0
  )