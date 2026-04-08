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
from app.services.config_repo import get_neutral_allocation, get_allocation_parameter
from app.db.backtest_parameter import BacktestParameter
from app.db.allocation_adjustment import AllocationAdjustment
from app.backtest.schemas.backtest_performance import BacktestPerformance
from app.backtest.schemas.backtest_portfolio_performance import BacktestPortfolioPerformance
from app.backtest.schemas.backtest_run import BacktestFrequency, BacktestRun, BacktestStatus, BacktestInstrument
from app.backtest.schemas.backtest_weight import BacktestWeight
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter
from app.db.allocation_history import AllocationHistory
import logging

logger = logging.getLogger(__name__)

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
        "instrument": bt.instrument,
        "created_at": bt.created_at,
        "updated_at": bt.updated_at,
    }


def _serialize_run(run: BacktestRun, db: Session) -> dict:
    params = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run.id).all()
    return {
        "id": run.id,
        "backtest_id": run.backtest_id,
        "name": run.name,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "frequency": run.frequency,
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
        "parameters": {p.key: p.value for p in params},
    }


# ---------------------------------------------------------------------------
# Allocation config (current state)
# ---------------------------------------------------------------------------

class UpdateParameterRequest(BaseModel):
    value: float


@router.patch("/allocation-config/parameters/{key}")
def update_allocation_parameter(key: str, req: UpdateParameterRequest, db: Session = Depends(get_db)):
    row = db.query(BacktestParameter).filter(BacktestParameter.key == key).first()
    if not row:
        raise HTTPException(status_code=404, detail="Parameter not found")
    row.value = req.value  # type: ignore[assignment]
    db.commit()
    return {"key": key, "value": req.value}


@router.get("/backtests/{backtest_id}/config")
def get_backtest_config(backtest_id: int, db: Session = Depends(get_db)):
    bt = _get_backtest_or_404(backtest_id, db)
    
    logger.warning(f"frequency: {bt.frequency} - instrument: {bt.instrument}")
    
    if bt.frequency == BacktestFrequency.EOM.value:
        adjustments = db.query(AllocationAdjustment).order_by(
            AllocationAdjustment.pillar, AllocationAdjustment.regime, AllocationAdjustment.asset
        ).all()
        return {
            "neutral": get_neutral_allocation(db),
            "coherence_factor": get_allocation_parameter(db, "coherence.factor", backtest_id, 0.5),
            "allocation_alpha": get_allocation_parameter(db, "allocation.alpha", backtest_id, 0.3),
            "adjustments": [
                {"pillar": a.pillar, "regime": a.regime, "asset": a.asset, "delta": a.delta}
                for a in adjustments
            ],
        }
    if (bt.frequency == BacktestFrequency.EOD.value or  bt.frequency == BacktestFrequency.EOW.value) and bt.instrument == 'options':
        optionsParameters = db.query(BacktestParameter).filter(BacktestParameter.backtest_id == backtest_id).all()
        return optionsParameters
        
    return {}


# ---------------------------------------------------------------------------
# Backtests (container)
# ---------------------------------------------------------------------------

class CreateBacktestRequest(BaseModel):
    name: str
    description: str | None = None
    strategy_version: str = "v1"
    frequency: str = "EOM"
    instrument: str | None = None


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
        instrument= req.instrument,
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
    name: str | None = None
    start: date
    end: date
    notes: str | None = None
    initial_allocation: str = "neutral"


class UpdateRunRequest(BaseModel):
    name: str | None = None
    start: date | None = None
    end: date | None = None
    notes: str | None = None
    parameters: dict[str, str] | None = None


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
    serialized = [_serialize_run(r, db) for r in runs]
    return serialized


def _upsert_run_parameter(db: Session, run_id: int, key: str, value: str) -> None:
    row = db.query(BacktestRunParameter).filter(
        BacktestRunParameter.run_id == run_id,
        BacktestRunParameter.key == key,
    ).first()
    if row:
        row.value = value  
    else:
        db.add(BacktestRunParameter(run_id=run_id, key=key, value=value))


@router.post("/backtests/{backtest_id}/create-run", status_code=201)
def create_run(backtest_id: int, req: CreateRunRequest, db: Session = Depends(get_db)):
    bt = _get_backtest_or_404(backtest_id, db)
    data = {
        "backtest_id": backtest_id,
        "name": req.name,
        "start_date": req.start,
        "end_date": req.end,
        "frequency": bt.frequency,
        "notes": req.notes,
        "status": BacktestStatus.READY,
    }
        
    run = BacktestRun(**data)
    db.add(run)
    db.flush()  # get run.id before commit
    run_id = cast(int, run.id)
    logger.warning(f"create run for frequency: {bt.frequency} - instrument: {bt.instrument}")
    if bt.frequency == BacktestFrequency.EOM:
        # Copy global defaults into per-run parameters
        coherence_factor = get_allocation_parameter(db, "coherence.factor", backtest_id, 0.5)
        allocation_alpha = get_allocation_parameter(db, "allocation.alpha", backtest_id, 0.3)
        _upsert_run_parameter(db, run_id, "coherence.factor", str(coherence_factor))
        _upsert_run_parameter(db, run_id, "allocation.alpha", str(allocation_alpha))
        _upsert_run_parameter(db, run_id, "initial_allocation", req.initial_allocation)
        
    if (bt.frequency == BacktestFrequency.EOD or bt.frequency == BacktestFrequency.EOW) and bt.instrument == BacktestInstrument.OPTIONS.value:
        # Copy global defaults into per-run parameters
        _upsert_run_parameter(db, run_id, "symbol", "IWM")
        _upsert_run_parameter(db, run_id, "max_risk", "5")
        _upsert_run_parameter(db, run_id, "initial_capital", "10000")
        _upsert_run_parameter(db, run_id, "entry_every_n_days", "30")
        
    db.commit()
    db.refresh(run)
        
    return {"id": run_id}


@router.post("/backtests/{backtest_id}/runs/{run_id}/clone", status_code=201)
def clone_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    source = _get_run_or_404(backtest_id, run_id, db)
    source_name = cast(str, source.name) if source.name is not None else ""
    new_run = BacktestRun(
        backtest_id=backtest_id,
        name=(source_name + " copy").strip() if source_name else "copy",
        start_date=source.start_date,
        end_date=source.end_date,
        frequency=source.frequency,
        notes=source.notes,
        status=BacktestStatus.READY,
    )
    db.add(new_run)
    db.flush()
    new_run_id = cast(int, new_run.id)
    # Copy parameters from source run
    source_params = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run_id).all()
    for p in source_params:
        db.add(BacktestRunParameter(run_id=new_run_id, key=p.key, value=p.value))
    db.commit()
    db.refresh(new_run)
    return _serialize_run(new_run, db)


@router.get("/backtests/{backtest_id}/runs/{run_id}")
def get_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    return _serialize_run(run, db)


@router.patch("/backtests/{backtest_id}/runs/{run_id}")
def update_run(backtest_id: int, run_id: int, req: UpdateRunRequest, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if req.name is not None:
        run.name = req.name  # type: ignore[assignment]
    if req.start is not None:
        run.start_date = req.start  # type: ignore[assignment]
    if req.end is not None:
        run.end_date = req.end  # type: ignore[assignment]
    if req.notes is not None:
        run.notes = req.notes  # type: ignore[assignment]
    if req.parameters:
        for key, value in req.parameters.items():
            _upsert_run_parameter(db, cast(int, run.id), key, value)
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
    bt = _get_backtest_or_404(backtest_id, db)
    if bt.frequency != BacktestFrequency.EOM and bt.frequency != BacktestFrequency.EOD:
        run.status = BacktestStatus.ERROR 
        run.error_message = f"***Backtest execution not yet implemented for frequency {bt.frequency}"  # type: ignore[assignment]
        db.commit()
        return {"id": run_id, "status": BacktestStatus.ERROR}

    if run.status == BacktestStatus.RUNNING:  
        raise HTTPException(status_code=409, detail="Run already in progress")
    if run.end_date > date_type.today():  # type: ignore[operator]
        raise HTTPException(status_code=400, detail="end_date cannot be in the future")
    # clear error
    run.error_message = ""
    db.commit()
    Thread(target=run_in_background, args=(cast(int, run.id),), daemon=True).start()
    return {"id": run_id, "status": BacktestStatus.RUNNING}


@router.post("/backtests/{backtest_id}/runs/{run_id}/stop")
def stop_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if run.status != BacktestStatus.RUNNING:  
        raise HTTPException(status_code=409, detail="Run is not currently running")
    run.stop_requested = True 
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
            "period_return": cast(float, r.period_return),
        }
        for r in rows
    ]


@router.post("/backtests/{backtest_id}/runs/{run_id}/invalidate")
def invalidate_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if run.status == BacktestStatus.RUNNING:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=409, detail="Cannot invalidate a running run")
    db.query(BacktestWeight).filter(BacktestWeight.run_id == run_id).delete()
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run_id).delete()
    db.query(AllocationHistory).filter(AllocationHistory.run_id == run_id).delete()
    
    for field in ("cagr", "volatility", "sharpe", "max_drawdown", "win_rate", "profit_factor", "n_trades", "config_snapshot", "error_message"):
        setattr(run, field, None)
    setattr(run, "status", BacktestStatus.READY)
    db.commit()
    return {"id": run_id, "status": BacktestStatus.READY}


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


@router.get("/backtests/{backtest_id}/runs/{run_id}/performances")
def run_portfolio_performances(backtest_id: int, run_id: int, page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    _get_run_or_404(backtest_id, run_id, db)
    total = (
        db.query(BacktestPortfolioPerformance)
        .filter(BacktestPortfolioPerformance.run_id == run_id)
        .count()
    )
    rows = (
        db.query(BacktestPortfolioPerformance)
        .filter(BacktestPortfolioPerformance.run_id == run_id)
        .order_by(BacktestPortfolioPerformance.snapshot_date)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "snapshot_date": r.snapshot_date,
                "cash": r.cash,
                "positions_value": r.positions_value,
                "total_equity": r.total_equity,
                "realized_pnl": r.realized_pnl,
                "unrealized_pnl": r.unrealized_pnl,
                "total_pnl": r.total_pnl,
                "total_delta": r.total_delta,
                "total_gamma": r.total_gamma,
                "total_theta": r.total_theta,
                "total_vega": r.total_vega,
                "open_positions_count": r.open_positions_count,
                "closed_positions_count": r.closed_positions_count,
                "new_positions_count": r.new_positions_count,
                "underlying_price": r.underlying_price,
                "iv": r.iv,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }
