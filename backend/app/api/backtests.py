from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date
from sqlalchemy.orm import Session
from typing import cast
from app.db.session import SessionLocal
from app.backtest.init_db import init_backtest_db
from app.backtest.runs import run_backtest
from app.backtest.schemas.backtest_performance import BacktestPerformance
from app.backtest.schemas.backtest_run import BacktestRun

router = APIRouter(tags=["backtest"])

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
    
class RunBacktestRequest(BaseModel):
  start: date
  end: date
  name:str ="Macro Allocation"
  strategy_version:str ="v1"
  
@router.post("/backtest/run")
def run(req: RunBacktestRequest, db: Session = Depends(get_db)):
  init_backtest_db()
  run_id = run_backtest(db=db, name=req.name, strategy_version=req.strategy_version, start=req.start, end=req.end)
  return {"run_id": run_id}

@router.get("/backtests/{run_id}/nav")
def nav(run_id: int, db: Session = Depends(get_db)):
  rows = (
    db.query(BacktestPerformance)
      .filter(BacktestPerformance.run_id == run_id)
      .order_by(BacktestPerformance.date)
      .all()
  )
  
  return [
    {
      "date": r.date,
      "nav": cast(float, r.nav),
      "monthly_return": cast(float, r.monthly_return),
    }
    for r in rows
  ]
  
@router.get("/backtests/{run_id}/metrics")
def metrics(run_id: int, db: Session = Depends(get_db)):
  run = db.query(BacktestRun).filter(BacktestRun.id == run_id).one()
  return {
		"run_id": run_id,
		"cagr": run.cagr,
		"volatility": run.volatility,
		"sharpe": run.sharpe,
		"max_drawdown": run.max_drawdown,
  }