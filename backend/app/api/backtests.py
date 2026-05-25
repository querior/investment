from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import date, datetime
from datetime import date as date_type
from collections import defaultdict
from sqlalchemy import String, func
from sqlalchemy import cast as sa_cast
from app.backtest.metrics import compute_ev_accuracy
from sqlalchemy.orm import Session, selectinload
from threading import Thread
from typing import cast, Optional, List
from app.db.session import SessionLocal
from app.backtest.runs import run_in_background
from app.backtest.schemas.backtest import Backtest
from app.services.config_repo import get_neutral_allocation, get_allocation_parameter
from app.db.backtest_parameter import BacktestParameter
from app.db.allocation_adjustment import AllocationAdjustment
from app.backtest.schemas.backtest_performance import BacktestPerformance
from app.backtest.schemas.backtest_portfolio_performance import BacktestPortfolioPerformance
from app.backtest.schemas.backtest_position import BacktestPosition
from app.backtest.schemas.backtest_position_snapshot import BacktestPositionSnapshot
from app.backtest.schemas.backtest_run import BacktestFrequency, BacktestRun, BacktestStatus, BacktestInstrument
from app.backtest.schemas.backtest_weight import BacktestWeight
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter
from app.db.allocation_history import AllocationHistory
from app.db.decision_log import DecisionLog
from app.backtest.parameter_schema import validate_parameters, PARAMETER_SCHEMA
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
    params_dict = {p.key: {"value": p.value, "unit": p.unit} for p in params}

    # Ensure all parameters from schema are present
    # If missing, add them to DB with default values
    missing_keys = []
    for key, schema in PARAMETER_SCHEMA.items():
        if key not in params_dict:
            default_value = schema.get("default")
            if default_value is not None:
                # Add to dict for this response
                unit = schema.get("unit", "value")
                params_dict[key] = {"value": default_value, "unit": unit}
                # Also add to DB so future queries get it
                missing_keys.append((key, default_value, unit))

    # Bulk insert missing parameters
    if missing_keys:
        for key, value, unit in missing_keys:
            db.add(BacktestRunParameter(
                run_id=cast(int, run.id),
                key=key,
                value=str(value),
                unit=unit
            ))
        db.commit()

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
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "parameters": params_dict,
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

    # Build parameter schema for frontend
    param_schema = {
        key: {
            "type": schema.get("type"),
            "min": schema.get("min"),
            "max": schema.get("max"),
            "default": schema.get("default"),
            "unit": schema.get("unit"),
            "precision": schema.get("precision"),
        }
        for key, schema in PARAMETER_SCHEMA.items()
    }

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
            "parameterSchema": param_schema,
        }
    if (bt.frequency == BacktestFrequency.EOD.value or  bt.frequency == BacktestFrequency.EOW.value) and bt.instrument == 'options':
        optionsParameters = db.query(BacktestParameter).filter(BacktestParameter.backtest_id == backtest_id).all()
        return {
            "optionsParameters": optionsParameters,
            "parameterSchema": param_schema,
        }

    return {"parameterSchema": param_schema}


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


def _upsert_run_parameter(db: Session, run_id: int, key: str, value: str, unit: str = "value") -> None:
    row = db.query(BacktestRunParameter).filter(
        BacktestRunParameter.run_id == run_id,
        BacktestRunParameter.key == key,
    ).first()
    if row:
        row.value = value
        row.unit = unit
    else:
        db.add(BacktestRunParameter(run_id=run_id, key=key, value=value, unit=unit))


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
        # Populate ALL parameters from schema with their defaults
        for key, schema in PARAMETER_SCHEMA.items():
            default_value = schema.get("default")
            if default_value is not None:
                unit = schema.get("unit", "value")
                _upsert_run_parameter(db, run_id, key, str(default_value), unit=unit)
        
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
        errors = validate_parameters(req.parameters)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"errors": errors}
            )
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

    # Reset metrics, performance, and positions before execution
    run.cagr = None
    run.sharpe = None
    run.volatility = None
    run.max_drawdown = None
    run.win_rate = None
    run.profit_factor = None
    run.n_trades = None
    run.error_message = ""

    # Delete previous results
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run_id).delete()
    db.query(BacktestPortfolioPerformance).filter(BacktestPortfolioPerformance.run_id == run_id).delete()
    db.query(BacktestPosition).filter(BacktestPosition.run_id == run_id).delete()
    db.query(BacktestPositionSnapshot).filter(BacktestPositionSnapshot.run_id == run_id).delete()
    db.query(BacktestWeight).filter(BacktestWeight.run_id == run_id).delete()

    # Set status to RUNNING in database before starting background thread
    run.status = BacktestStatus.RUNNING
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


@router.post("/backtests/{backtest_id}/runs/{run_id}/invalidate")
def invalidate_run(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    if run.status == BacktestStatus.RUNNING:  # type: ignore[comparison-overlap]
        raise HTTPException(status_code=409, detail="Cannot invalidate a running run")
    db.query(BacktestWeight).filter(BacktestWeight.run_id == run_id).delete()
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run_id).delete()
    db.query(AllocationHistory).filter(AllocationHistory.run_id == run_id).delete()
    db.query(BacktestPositionSnapshot).filter(BacktestPositionSnapshot.run_id == run_id).delete()
    db.query(BacktestPosition).filter(BacktestPosition.run_id == run_id).delete()
    db.query(BacktestPortfolioPerformance).filter(BacktestPortfolioPerformance.run_id == run_id).delete()
    db.query(DecisionLog).filter(DecisionLog.run_id == run_id).delete()

    for field in ("cagr", "volatility", "sharpe", "max_drawdown", "win_rate", "profit_factor", "n_trades", "config_snapshot", "error_message"):
        setattr(run, field, None)
    setattr(run, "status", BacktestStatus.READY)
    db.commit()
    return {"id": run_id, "status": BacktestStatus.READY}


@router.get("/backtests/{backtest_id}/runs/{run_id}/status")
def run_status(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)
    return {
        "id": run_id,
        "status": run.status,
        "error_message": run.error_message,
        "updated_at": run.updated_at,
    }


@router.get("/backtests/{backtest_id}/runs/{run_id}/metrics")
def run_metrics(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    run = _get_run_or_404(backtest_id, run_id, db)

    # Extract entry and exit rules from parameters
    params = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run_id).all()

    entry_rules = {}
    exit_rules = {}

    for p in params:
        if p.key.startswith("entry."):
            entry_rules[p.key] = p.value
        elif p.key.startswith("exit."):
            exit_rules[p.key] = p.value

    # Summary of overall run metrics
    summary = {
        "cagr": run.cagr,
        "volatility": run.volatility,
        "sharpe": run.sharpe,
        "max_drawdown": run.max_drawdown,
        "win_rate": run.win_rate,
        "profit_factor": run.profit_factor,
        "n_trades": run.n_trades,
        "max_consecutive_losses": run.max_consecutive_losses,
    }

    # Performance breakdown by strategy
    positions = (
        db.query(BacktestPosition)
        .filter(BacktestPosition.run_id == run_id)
        .all()
    )

    strategies_data = {}
    for pos in positions:
        strategy = pos.position_type

        if strategy not in strategies_data:
            strategies_data[strategy] = {
                "count": 0,
                "winning": 0,
                "losing": 0,
                "total_pnl": 0.0,
                "days_in_trade": [],
                "snapshots_for_dd": [],
                "strategy_acronym": pos.strategy.acronym if pos.strategy else None,
                "strategy_name": pos.strategy.name if pos.strategy else strategy,
                "strategy_color": pos.strategy.color if pos.strategy else "default",
            }

        strategies_data[strategy]["count"] += 1

        if pos.realized_pnl and pos.realized_pnl > 0:
            strategies_data[strategy]["winning"] += 1
        elif pos.realized_pnl and pos.realized_pnl < 0:
            strategies_data[strategy]["losing"] += 1

        if pos.realized_pnl:
            strategies_data[strategy]["total_pnl"] += pos.realized_pnl

        if pos.closed_at:
            days = (pos.closed_at - pos.opened_at).days
            strategies_data[strategy]["days_in_trade"].append(days)

        snapshots = (
            db.query(BacktestPositionSnapshot)
            .filter(BacktestPositionSnapshot.position_id == pos.id)
            .order_by(BacktestPositionSnapshot.snapshot_date)
            .all()
        )
        if snapshots:
            strategies_data[strategy]["snapshots_for_dd"].extend(snapshots)

    performances = []
    for strategy, data in sorted(strategies_data.items()):
        avg_days = (
            sum(data["days_in_trade"]) / len(data["days_in_trade"])
            if data["days_in_trade"]
            else 0
        )
        avg_pnl = data["total_pnl"] / data["count"] if data["count"] > 0 else 0

        max_dd = None
        if data["snapshots_for_dd"]:
            max_pnl = max((s.position_pnl for s in data["snapshots_for_dd"] if s.position_pnl is not None), default=None)
            min_pnl = min((s.position_pnl for s in data["snapshots_for_dd"] if s.position_pnl is not None), default=None)
            if max_pnl is not None and min_pnl is not None and max_pnl > 0:
                max_dd = (max_pnl - min_pnl) / max_pnl if max_pnl != 0 else 0

        performances.append({
            "strategy": strategy,
            "strategy_acronym": data.get("strategy_acronym"),
            "strategy_name": data.get("strategy_name"),
            "strategy_color": data.get("strategy_color"),
            "count": data["count"],
            "winning": data["winning"],
            "losing": data["losing"],
            "win_rate": data["winning"] / data["count"] if data["count"] > 0 else 0,
            "avg_holding_days": round(avg_days, 2),
            "total_pnl": round(data["total_pnl"], 2),
            "avg_pnl": round(avg_pnl, 2),
            "max_drawdown": round(max_dd, 4) if max_dd is not None else None,
        })

    # Fetch NAV data
    nav_rows = (
        db.query(BacktestPerformance)
        .filter(BacktestPerformance.run_id == run_id)
        .order_by(BacktestPerformance.date)
        .all()
    )
    nav = [
        {
            "date": r.date,
            "nav": cast(float, r.nav),
            "period_return": cast(float, r.period_return),
        }
        for r in nav_rows
    ]

    # Fetch portfolio timeseries for charts (underlying, IV, P&L attribution)
    portfolio_rows = (
        db.query(BacktestPortfolioPerformance)
        .filter(BacktestPortfolioPerformance.run_id == run_id)
        .order_by(BacktestPortfolioPerformance.snapshot_date)
        .all()
    )
    portfolio_timeseries = [
        {
            "snapshot_date": r.snapshot_date,
            "total_equity": float(r.total_equity),
            "realized_pnl": float(r.realized_pnl),
            "unrealized_pnl": float(r.unrealized_pnl),
            "total_pnl": float(r.total_pnl),
            "underlying_price": float(r.underlying_price),
            "iv": float(r.iv),
        }
        for r in portfolio_rows
    ]

    return {
        "run_id": run_id,
        "start_date": run.start_date,
        "end_date": run.end_date,
        "summary": summary,
        "entry_rules": entry_rules,
        "exit_rules": exit_rules,
        "performances": performances,
        "nav": nav,
        "portfolio_timeseries": portfolio_timeseries,
    }


@router.get("/backtests/{backtest_id}/runs/{run_id}/ev-accuracy")
def run_ev_accuracy(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    _get_run_or_404(backtest_id, run_id, db)
    return compute_ev_accuracy(db, run_id)


@router.get("/backtests/{backtest_id}/runs/{run_id}/positions/filter-options")
def positions_filter_options(backtest_id: int, run_id: int, db: Session = Depends(get_db)):
    """Valori distinti di strategia e regime per i filtri della tabella posizioni."""
    _get_run_or_404(backtest_id, run_id, db)
    rows = (
        db.query(BacktestPosition.position_type, BacktestPosition.entry_macro_regime)
        .filter(BacktestPosition.run_id == run_id)
        .distinct()
        .all()
    )
    strategies = sorted({r.position_type for r in rows if r.position_type})
    regimes = sorted({r.entry_macro_regime for r in rows if r.entry_macro_regime})
    return {"strategies": strategies, "regimes": regimes}


@router.get("/backtests/{backtest_id}/runs/{run_id}/performance")
def run_performance(
    backtest_id: int,
    run_id: int,
    page: int = 1,
    limit: int = 20,
    strategy: Optional[str] = None,
    macro_regime: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _get_run_or_404(backtest_id, run_id, db)

    run_params = {
        p.key: p.value
        for p in db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run_id).all()
    }
    initial_capital = float(run_params.get("initial_capital", 10000))
    max_risk_pct = float(run_params.get("max_risk", 3)) / 100.0

    base_filter = [BacktestPosition.run_id == run_id]
    if strategy:
        base_filter.append(BacktestPosition.position_type == strategy)
    if macro_regime:
        base_filter.append(BacktestPosition.entry_macro_regime == macro_regime)

    total = db.query(BacktestPosition).filter(*base_filter).count()
    positions = (
        db.query(BacktestPosition)
        .filter(*base_filter)
        .options(selectinload(BacktestPosition.strategy))
        .order_by(BacktestPosition.opened_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for pos in positions:
        # Calculate performance_pct
        performance_pct = None
        if pos.initial_value and pos.initial_value != 0 and pos.realized_pnl is not None:
            performance_pct = pos.realized_pnl / abs(pos.initial_value)

        # Calculate days_in_trade
        if pos.closed_at:
            days_in_trade = (pos.closed_at - pos.opened_at).days
        else:
            # Position is open: use last snapshot date or today
            last_snapshot = (
                db.query(BacktestPositionSnapshot)
                .filter(BacktestPositionSnapshot.position_id == pos.id)
                .order_by(BacktestPositionSnapshot.snapshot_date.desc())
                .first()
            )
            snapshot_date = last_snapshot.snapshot_date if last_snapshot else date_type.today()
            days_in_trade = (snapshot_date - pos.opened_at).days

        # Calculate unrealized_pnl for open positions
        unrealized_pnl = None
        if pos.status == "OPEN":
            last_snapshot = (
                db.query(BacktestPositionSnapshot)
                .filter(BacktestPositionSnapshot.position_id == pos.id)
                .order_by(BacktestPositionSnapshot.snapshot_date.desc())
                .first()
            )
            if last_snapshot:
                unrealized_pnl = last_snapshot.position_pnl

        capital_at_risk_pct = None
        risk_limit_ok = None
        if pos.entry_max_loss is not None and initial_capital > 0:
            capital_at_risk_pct = pos.entry_max_loss / initial_capital
            risk_limit_ok = capital_at_risk_pct <= max_risk_pct

        items.append({
            "id": pos.id,
            "position_type": pos.position_type,
            "strategy_name": pos.strategy.name if pos.strategy else None,
            "strategy_acronym": pos.strategy.acronym if pos.strategy else None,
            "strategy_color": pos.strategy.color if pos.strategy else "default",
            "status": pos.status,
            "opened_at": pos.opened_at,
            "closed_at": pos.closed_at,
            "entry_underlying": pos.entry_underlying,
            "entry_iv": pos.entry_iv,
            "entry_macro_regime": pos.entry_macro_regime,
            "initial_value": pos.initial_value,
            "close_value": pos.close_value,
            "realized_pnl": pos.realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "performance_pct": performance_pct,
            "days_in_trade": days_in_trade,
            "entry_max_loss": pos.entry_max_loss,
            "entry_max_profit": pos.entry_max_profit,
            "entry_prob_profit": pos.entry_prob_profit,
            "entry_ev_net": pos.entry_ev_net,
            "capital_at_risk_pct": capital_at_risk_pct,
            "risk_limit_ok": risk_limit_ok,
        })

    # Calculate summary metrics (same as /metrics)
    run = _get_run_or_404(backtest_id, run_id, db)

    summary = {
        "cagr": run.cagr,
        "volatility": run.volatility,
        "sharpe": run.sharpe,
        "max_drawdown": run.max_drawdown,
        "win_rate": run.win_rate,
        "profit_factor": run.profit_factor,
        "n_trades": run.n_trades,
        "max_consecutive_losses": run.max_consecutive_losses,
    }

    # Get all positions for performance calculation
    all_positions = db.query(BacktestPosition).filter(BacktestPosition.run_id == run_id).all()

    strategies_data = {}
    for pos in all_positions:
        strategy = pos.position_type
        if strategy not in strategies_data:
            strategies_data[strategy] = {
                "count": 0,
                "winning": 0,
                "losing": 0,
                "total_pnl": 0.0,
                "days_in_trade": [],
                "snapshots_for_dd": [],
                "strategy_acronym": pos.strategy.acronym if pos.strategy else None,
                "strategy_name": pos.strategy.name if pos.strategy else strategy,
                "strategy_color": pos.strategy.color if pos.strategy else "default",
            }

        strategies_data[strategy]["count"] += 1

        if pos.realized_pnl and pos.realized_pnl > 0:
            strategies_data[strategy]["winning"] += 1
        elif pos.realized_pnl and pos.realized_pnl < 0:
            strategies_data[strategy]["losing"] += 1

        if pos.realized_pnl:
            strategies_data[strategy]["total_pnl"] += pos.realized_pnl

        if pos.closed_at:
            days = (pos.closed_at - pos.opened_at).days
            strategies_data[strategy]["days_in_trade"].append(days)

        snapshots = (
            db.query(BacktestPositionSnapshot)
            .filter(BacktestPositionSnapshot.position_id == pos.id)
            .order_by(BacktestPositionSnapshot.snapshot_date)
            .all()
        )
        if snapshots:
            strategies_data[strategy]["snapshots_for_dd"].extend(snapshots)

    performances = []
    for strategy, data in sorted(strategies_data.items()):
        avg_days = (
            sum(data["days_in_trade"]) / len(data["days_in_trade"])
            if data["days_in_trade"]
            else 0
        )
        avg_pnl = data["total_pnl"] / data["count"] if data["count"] > 0 else 0

        max_dd = None
        if data["snapshots_for_dd"]:
            max_pnl = max((s.position_pnl for s in data["snapshots_for_dd"] if s.position_pnl is not None), default=None)
            min_pnl = min((s.position_pnl for s in data["snapshots_for_dd"] if s.position_pnl is not None), default=None)
            if max_pnl is not None and min_pnl is not None and max_pnl > 0:
                max_dd = (max_pnl - min_pnl) / max_pnl if max_pnl != 0 else 0

        performances.append({
            "strategy": strategy,
            "strategy_acronym": data.get("strategy_acronym"),
            "strategy_name": data.get("strategy_name"),
            "strategy_color": data.get("strategy_color"),
            "count": data["count"],
            "winning": data["winning"],
            "losing": data["losing"],
            "win_rate": data["winning"] / data["count"] if data["count"] > 0 else 0,
            "avg_holding_days": round(avg_days, 2),
            "total_pnl": round(data["total_pnl"], 2),
            "avg_pnl": round(avg_pnl, 2),
            "max_drawdown": round(max_dd, 4) if max_dd is not None else None,
        })

    # Fetch NAV data
    nav_rows = (
        db.query(BacktestPerformance)
        .filter(BacktestPerformance.run_id == run_id)
        .order_by(BacktestPerformance.date)
        .all()
    )
    nav = [
        {
            "date": r.date,
            "nav": cast(float, r.nav),
            "period_return": cast(float, r.period_return),
        }
        for r in nav_rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "summary": summary,
        "performances": performances,
        "nav": nav,
    }


def _format_entry_criteria(entry_conditions: dict) -> list[str]:
    """Format entry conditions into human-readable criteria."""
    if not entry_conditions:
        return []

    criteria = []

    if entry_conditions.get("macro_regime"):
        criteria.append(f"Macro: {entry_conditions['macro_regime']}")

    if entry_conditions.get("trend"):
        criteria.append(f"Trend: {entry_conditions['trend']}")

    if entry_conditions.get("iv_rv_ratio"):
        criteria.append(f"IV/RV: {entry_conditions['iv_rv_ratio']:.2f}")

    if entry_conditions.get("rsi_14") is not None:
        criteria.append(f"RSI: {entry_conditions['rsi_14']:.2f}")

    if entry_conditions.get("macd") is not None:
        criteria.append(f"MACD: {entry_conditions['macd']:.4f}")

    if entry_conditions.get("iv"):
        criteria.append(f"IV: {entry_conditions['iv']:.2%}")

    if entry_conditions.get("underlying_price"):
        criteria.append(f"Price: {entry_conditions['underlying_price']:.2f}")

    return criteria


def _format_exit_criteria(exit_conditions: dict) -> list[str]:
    """Format exit conditions with actual data that triggered the exit."""
    if not exit_conditions:
        return []

    criteria = []

    # If exit_conditions has 'triggered_by' (new format), format with actual data
    if "triggered_by" in exit_conditions:
        reason = exit_conditions.get("reason", "Unknown exit reason")
        criteria.append(reason)

        # Add key data points from exit_conditions["data"]
        data = exit_conditions.get("data", {})
        if data.get("current_pnl") is not None:
            criteria.append(f"P&L: {data['current_pnl']:.2f} ({data.get('pnl_pct', 0):.1f}%)")

        if data.get("dte") is not None:
            criteria.append(f"DTE: {data['dte']:.0f} days")

        if data.get("macro_regime"):
            criteria.append(f"Macro Regime: {data['macro_regime']}")

        if data.get("rsi_14") is not None:
            criteria.append(f"RSI: {data['rsi_14']:.2f}")

        if data.get("macd") is not None:
            criteria.append(f"MACD: {data['macd']:.4f}")

        if data.get("iv_rv_ratio") is not None:
            criteria.append(f"IV/RV: {data['iv_rv_ratio']:.2f}")

        if data.get("position_delta") is not None:
            criteria.append(f"Delta: {data['position_delta']:.4f}")

        if data.get("position_theta") is not None:
            criteria.append(f"Theta: {data['position_theta']:.4f}")

    return criteria


@router.get("/backtests/{backtest_id}/runs/{run_id}/positions/{position_id}/history")
def position_history(backtest_id: int, run_id: int, position_id: int, db: Session = Depends(get_db)):
    _get_run_or_404(backtest_id, run_id, db)

    # Verify position exists and belongs to this run
    position = (
        db.query(BacktestPosition)
        .filter(BacktestPosition.id == position_id, BacktestPosition.run_id == run_id)
        .first()
    )
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    snapshots = (
        db.query(BacktestPositionSnapshot)
        .filter(
            BacktestPositionSnapshot.position_id == position_id,
            BacktestPositionSnapshot.run_id == run_id,
        )
        .order_by(BacktestPositionSnapshot.snapshot_date)
        .all()
    )

    # Format actual entry and exit criteria from position data
    entry_criteria = _format_entry_criteria(position.entry_conditions or {})
    exit_criteria = _format_exit_criteria(position.exit_conditions or {})

    return {
        "header": {
            "position_id": position.id,
            "position_type": position.position_type,
            "strategy_name": position.strategy.name if position.strategy else None,
            "status": position.status,
            "opened_at": position.opened_at,
            "closed_at": position.closed_at,
            "entry_underlying": position.entry_underlying,
            "entry_iv": position.entry_iv,
            "entry_macro_regime": position.entry_macro_regime,
            "initial_value": position.initial_value,
            "close_value": position.close_value,
            "realized_pnl": position.realized_pnl,
            "entry_criteria": entry_criteria,
            "exit_criteria": exit_criteria,
        },
        "snapshots": [
            {
                "snapshot_date": s.snapshot_date,
                "underlying_price": s.underlying_price,
                "iv": s.iv,
                "position_price": s.position_price,
                "position_pnl": s.position_pnl,
                "position_delta": s.position_delta,
                "position_gamma": s.position_gamma,
                "position_theta": s.position_theta,
                "position_vega": s.position_vega,
                "min_dte": s.min_dte,
                "is_open": s.is_open,
            }
            for s in snapshots
        ]
    }


# ---------------------------------------------------------------------------
# Decision Logs
# ---------------------------------------------------------------------------

class DecisionLogFilter(BaseModel):
    decision_actions: Optional[List[str]] = None
    strategy_names: Optional[List[str]] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    min_entry_score: Optional[float] = None
    max_entry_score: Optional[float] = None
    min_size_multiplier: Optional[float] = None
    max_size_multiplier: Optional[float] = None


class GetDecisionLogsRequest(BaseModel):
    skip: int = 0
    limit: int = 20
    filters: Optional[DecisionLogFilter] = None


@router.post("/backtests/{backtest_id}/runs/{run_id}/decision_logs")
def get_decision_logs(
    backtest_id: int,
    run_id: int,
    req: GetDecisionLogsRequest,
    db: Session = Depends(get_db),
):
    """Recupera i decision logs con paginazione e filtri."""
    _get_backtest_or_404(backtest_id, db)
    _get_run_or_404(backtest_id, run_id, db)

    query = db.query(DecisionLog).filter(DecisionLog.run_id == run_id)
    logger.warning(f"[DECISION_LOGS] run_id={run_id}, total_before_filter={query.count()}")
    logger.warning(f"[DECISION_LOGS] filters={req.filters}")

    if req.filters:
        if req.filters.decision_actions:
            query = query.filter(DecisionLog.decision_action.in_(req.filters.decision_actions))

        if req.filters.strategy_names:
            query = query.filter(DecisionLog.strategy_name.in_(req.filters.strategy_names))

        if req.filters.date_from:
            query = query.filter(DecisionLog.date >= req.filters.date_from)

        if req.filters.date_to:
            query = query.filter(DecisionLog.date <= req.filters.date_to)

        if req.filters.min_entry_score is not None:
            query = query.filter(DecisionLog.entry_score >= req.filters.min_entry_score)

        if req.filters.max_entry_score is not None:
            query = query.filter(DecisionLog.entry_score <= req.filters.max_entry_score)

        if req.filters.min_size_multiplier is not None:
            query = query.filter(DecisionLog.size_multiplier >= req.filters.min_size_multiplier)

        if req.filters.max_size_multiplier is not None:
            query = query.filter(DecisionLog.size_multiplier <= req.filters.max_size_multiplier)

    logger.warning(f"[DECISION_LOGS] total_after_filter={query.count()}")
    total = query.count()
    logs = query.order_by(DecisionLog.date.desc()).offset(req.skip).limit(req.limit).all()

    return {
        "run_id": run_id,
        "total": total,
        "skip": req.skip,
        "limit": req.limit,
        "logs": [
            {
                "id": log.id,
                "date": log.date,
                "zone": log.zone,
                "trend": log.trend,
                "iv_rank": log.iv_rank,
                "adx": log.adx,
                "entry_score": log.entry_score,
                "strategy_name": log.strategy_name,
                "size_multiplier": log.size_multiplier,
                "should_trade": log.should_trade,
                "spot": log.spot,
                "iv": log.iv,
                "dte_days": log.dte_days,
                "delta": log.delta,
                "gamma": log.gamma,
                "vega": log.vega,
                "theta": log.theta,
                "bid_ask_spread": log.bid_ask_spread,
                "bid_ask_pct": log.bid_ask_pct,
                "edge": log.edge,
                "breakeven_distance": log.breakeven_distance,
                "decision_action": log.decision_action,
                "decision_score": log.decision_score,
                "decision_reasoning": log.decision_reasoning,
                "pricing_edge_score": log.pricing_edge_score,
                "risk_reward_score": log.risk_reward_score,
                "breakeven_score": log.breakeven_score,
                "execution_cost_score": log.execution_cost_score,
                "capital_efficiency_score": log.capital_efficiency_score,
            }
            for log in logs
        ]
    }


@router.get("/backtests/{backtest_id}/runs/{run_id}/decision_matrix")
def get_decision_matrix(
    backtest_id: int,
    run_id: int,
    db: Session = Depends(get_db),
):
    """
    Aggregated decision matrix: zone × strategy × decision → counts + avg sub-scores.
    Used by the frontend regime matrix visualization.
    """
    _get_backtest_or_404(backtest_id, db)
    _get_run_or_404(backtest_id, run_id, db)

    rows = (
        db.query(
            DecisionLog.zone,
            DecisionLog.strategy_name,
            DecisionLog.decision_action,
            func.count().label("count"),
            func.avg(DecisionLog.decision_score).label("avg_score"),
            func.avg(DecisionLog.entry_score).label("avg_entry_score"),
            func.avg(DecisionLog.iv_rank).label("avg_iv_rank"),
            func.avg(DecisionLog.adx).label("avg_adx"),
            func.avg(DecisionLog.pricing_edge_score).label("avg_pricing_edge"),
            func.avg(DecisionLog.risk_reward_score).label("avg_risk_reward"),
            func.avg(DecisionLog.breakeven_score).label("avg_breakeven"),
            func.avg(DecisionLog.execution_cost_score).label("avg_execution_cost"),
            func.avg(DecisionLog.capital_efficiency_score).label("avg_capital_efficiency"),
        )
        .filter(DecisionLog.run_id == run_id)
        .group_by(DecisionLog.zone, DecisionLog.strategy_name, DecisionLog.decision_action)
        .order_by(DecisionLog.zone, DecisionLog.strategy_name, DecisionLog.decision_action)
        .all()
    )

    def _f(v) -> float | None:
        return round(float(v), 1) if v is not None else None

    # Per-zone performance stats: join positions → decision_log on (run_id, strategy, date)
    pos_rows = (
        db.query(
            DecisionLog.zone,
            BacktestPosition.realized_pnl,
            BacktestPosition.opened_at,
        )
        .join(
            BacktestPosition,
            (BacktestPosition.run_id == DecisionLog.run_id)
            & (BacktestPosition.position_type == DecisionLog.strategy_name)
            & (sa_cast(BacktestPosition.opened_at, String) == DecisionLog.date),
        )
        .filter(
            DecisionLog.run_id == run_id,
            DecisionLog.decision_action == "OPEN",
            BacktestPosition.status == "CLOSED",
            BacktestPosition.realized_pnl.isnot(None),
        )
        .order_by(DecisionLog.zone, BacktestPosition.opened_at)
        .all()
    )

    zone_pnls: dict[str, list[float]] = defaultdict(list)
    for pr in pos_rows:
        zone_pnls[pr.zone or "UNKNOWN"].append(float(pr.realized_pnl))

    def _zone_stats(pnls: list[float]) -> dict:
        if not pnls:
            return {}
        wins = sum(1 for p in pnls if p > 0)
        avg_pnl = sum(pnls) / len(pnls)
        cum, peak, max_dd = 0.0, 0.0, 0.0
        for p in pnls:
            cum += p
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
        return {
            "n_closed": len(pnls),
            "win_rate": round(wins / len(pnls) * 100, 1),
            "avg_pnl": round(avg_pnl, 2),
            "max_drawdown": round(max_dd, 2),
        }

    zone_stats = {zone: _zone_stats(pnls) for zone, pnls in zone_pnls.items()}

    return {
        "run_id": run_id,
        "rows": [
            {
                "zone": r.zone,
                "strategy_name": r.strategy_name,
                "decision_action": r.decision_action,
                "count": r.count,
                "avg_score": _f(r.avg_score),
                "avg_entry_score": _f(r.avg_entry_score),
                "avg_iv_rank": _f(r.avg_iv_rank),
                "avg_adx": _f(r.avg_adx),
                "avg_pricing_edge": _f(r.avg_pricing_edge),
                "avg_risk_reward": _f(r.avg_risk_reward),
                "avg_breakeven": _f(r.avg_breakeven),
                "avg_execution_cost": _f(r.avg_execution_cost),
                "avg_capital_efficiency": _f(r.avg_capital_efficiency),
            }
            for r in rows
        ],
        "zone_stats": zone_stats,
    }
