from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import date
from datetime import date as date_type
from sqlalchemy.orm import Session
from threading import Thread
from typing import cast
from app.db.session import SessionLocal
from app.backtest.runs import run_in_background
from app.backtest.schemas.backtest import Backtest
from app.services.config_repo import get_sensitivity, get_neutral_allocation, get_allocation_parameter, get_macro_score_weights
from app.backtest.schemas.backtest_performance import BacktestPerformance
from app.backtest.schemas.backtest_run import BacktestRun, BacktestStatus
from app.backtest.schemas.backtest_weight import BacktestWeight

router = APIRouter(tags=["backtest"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_backtest(bt: Backtest) -> dict:
    return {
        "id": bt.id,
        "name": bt.name,
        "description": bt.description,
        "strategy_version": bt.strategy_version,
        "frequency": bt.frequency,
        "primary_index": bt.primary_index,
        "created_at": bt.created_at,
        "updated_at": bt.updated_at,
    }


def _serialize_run(run: BacktestRun) -> dict:
    return {
        "id": run.id,
        "backtest_id": run.backtest_id,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "frequency": run.frequency,
        "primary_index": run.primary_index,
        "config_snapshot": run.config_snapshot,
        "status": run.status,
        "notes": run.notes,
        "error_message": run.error_message,
        "cagr": run.cagr,
        "sharpe": run.sharpe,
        "volatility": run.volatility,
        "max_drawdown": run.max_drawdown,
        "win_rate": run.win_rate,
        "profit_factor": run.profit_factor,
        "n_trades": run.n_trades,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


# ---------------------------------------------------------------------------
# Allocation config (current state)
# ---------------------------------------------------------------------------

@router.get("/allocation-config")
def get_allocation_config(db: Session = Depends(get_db)):
    return {
        "sensitivity": get_sensitivity(db),
        "neutral": get_neutral_allocation(db),
        "scale_k": get_allocation_parameter(db, "scale_factor_k", 0.05),
        "max_abs_delta": get_allocation_parameter(db, "max_abs_delta", 0.10),
        "macro_score_weights": get_macro_score_weights(db),
    }


# ---------------------------------------------------------------------------
# Backtests (container)
# ---------------------------------------------------------------------------

class CreateBacktestRequest(BaseModel):
    name: str
    description: str | None = None
    strategy_version: str = "v1"
    frequency: str = "EOM"
    primary_index: str = "MacroScore"


class UpdateBacktestRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("/backtests")
def list_backtests(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    total = db.query(Backtest).count()
    items = (
        db.query(Backtest)
        .order_by(Backtest.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {"items": [_serialize_backtest(b) for b in items], "total": total, "page": page, "limit": limit}


@router.post("/backtests", status_code=201)
def create_backtest(req: CreateBacktestRequest, db: Session = Depends(get_db)):
    bt = Backtest(
        name=req.name,
        description=req.description,
        strategy_version=req.strategy_version,
        frequency=req.frequency,
        primary_index=req.primary_index,
    )
    db.add(bt)
    db.commit()
    db.refresh(bt)
    return {"id": cast(int, bt.id)}


@router.get("/backtests/{backtest_id}")
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    bt = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return _serialize_backtest(bt)


@router.patch("/backtests/{backtest_id}")
def update_backtest(backtest_id: int, req: UpdateBacktestRequest, db: Session = Depends(get_db)):
    bt = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    if req.name is not None:
        bt.name = req.name  # type: ignore[assignment]
    if req.description is not None:
        bt.description = req.description  # type: ignore[assignment]
    db.commit()
    return {"id": backtest_id}


@router.delete("/backtests/{backtest_id}", status_code=204)
def delete_backtest(backtest_id: int, db: Session = Depends(get_db)):
    bt = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    db.delete(bt)
    db.commit()


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class CreateRunRequest(BaseModel):
    start: date
    end: date
    notes: str | None = None


class UpdateRunRequest(BaseModel):
    notes: str | None = None


def _get_backtest_or_404(backtest_id: int, db: Session) -> Backtest:
    bt = db.query(Backtest).filter(Backtest.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return bt


def _get_run_or_404(backtest_id: int, run_id: int, db: Session) -> BacktestRun:
    run = (
        db.query(BacktestRun)
        .filter(BacktestRun.backtest_id == backtest_id, BacktestRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/backtests/{backtest_id}/runs")
def list_runs(backtest_id: int, db: Session = Depends(get_db)):
    _get_backtest_or_404(backtest_id, db)
    runs = (
        db.query(BacktestRun)
        .filter(BacktestRun.backtest_id == backtest_id)
        .order_by(BacktestRun.created_at.desc())
        .all()
    )
    return [_serialize_run(r) for r in runs]


@router.post("/backtests/{backtest_id}/create-run", status_code=201)
def create_run(backtest_id: int, req: CreateRunRequest, db: Session = Depends(get_db)):
    bt = _get_backtest_or_404(backtest_id, db)
    run = BacktestRun(
        backtest_id=backtest_id,
        start_date=req.start,
        end_date=req.end,
        frequency=bt.frequency,
        primary_index=bt.primary_index,
        notes=req.notes,
        status=BacktestStatus.READY,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": cast(int, run.id)}


@router.get("/backtests/{backtest_id}/runs/{run_id}")
def get_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    return _serialize_run(run)


@router.patch("/backtests/{backtest_id}/runs/{run_id}")
def update_run(backtest_id: int, run_id: int, req: UpdateRunRequest, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if req.notes is not None:
        run.notes = req.notes  # type: ignore[assignment]
    db.commit()
    return {"id": run_id}


@router.delete("/backtests/{backtest_id}/runs/{run_id}", status_code=204)
def delete_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    db.delete(run)
    db.commit()


@router.post("/backtests/{backtest_id}/runs/{run_id}/execute", status_code=202)
def execute_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if run.status == BacktestStatus.RUNNING:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=409, detail="Run already in progress")
    if run.end_date > date_type.today():  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="end_date cannot be in the future")
    Thread(target=run_in_background, args=(cast(int, run.id),), daemon=True).start()
    return {"id": run_id, "status": BacktestStatus.RUNNING}


@router.post("/backtests/{backtest_id}/runs/{run_id}/stop")
def stop_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if run.status != BacktestStatus.RUNNING:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=409, detail="Run is not currently running")
    run.stop_requested = True  # type: ignore[assignment]
    db.commit()
    return {"id": run_id}


@router.get("/backtests/{backtest_id}/runs/{run_id}/weights")
def run_weights(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    _get_run_or_404(backtest_id, run_id, db)
    rows = (
        db.query(BacktestWeight)
        .filter(BacktestWeight.run_id == run_id)
        .order_by(BacktestWeight.date, BacktestWeight.asset)
        .all()
    )
    return [
        {
            "date": r.date,
            "asset": r.asset,
            "weight": cast(float, r.weight),
            "macro_score": r.macro_score,
            "pillar_scores": r.pillar_scores,
        }
        for r in rows
    ]


@router.get("/backtests/{backtest_id}/runs/{run_id}/nav")
def run_nav(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    _get_run_or_404(backtest_id, run_id, db)
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


@router.get("/backtests/{backtest_id}/runs/{run_id}/metrics")
def run_metrics(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    return {
        "run_id": run_id,
        "cagr": run.cagr,
        "volatility": run.volatility,
        "sharpe": run.sharpe,
        "max_drawdown": run.max_drawdown,
    }
