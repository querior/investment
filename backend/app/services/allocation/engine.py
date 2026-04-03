from sqlalchemy.orm import Session
from app.db.asset_class import AssetClass
from app.db.allocation_adjustment import AllocationAdjustment
from app.db.allocation_history import AllocationHistory
from app.db.backtest_parameter import BacktestParameter
from app.db.macro_regimes import MacroRegime
import datetime


def _get_param(db: Session, key: str, backtest_id: int) -> float:
    rec = db.query(BacktestParameter).filter(
        BacktestParameter.key == key,
        BacktestParameter.backtest_id == backtest_id,
    ).first()
    if rec is None:
        raise ValueError(f"BacktestParameter '{key}' non trovato per backtest_id {backtest_id}")
    return rec.value

def _apply_constraints(
    target: dict[str, float],
    constraints: dict[str, dict[str, float]],
) -> dict[str, float]:
    return {
        asset: max(constraints[asset]["min"], min(constraints[asset]["max"], value))
        for asset, value in target.items()
    }


def _rescale(allocation: dict[str, float]) -> dict[str, float]:
    total = sum(allocation.values())
    if total == 0:
        return {asset: 1.0 / len(allocation) for asset in allocation}
    return {asset: value / total for asset, value in allocation.items()}


def compute_target_allocation(
    db: Session,
    regimes: dict[str, str],
    backtest_id: int,
    coherence_factor: float | None = None,
) -> dict[str, float]:

    # --- carica asset class ---
    asset_classes = db.query(AssetClass).order_by(AssetClass.display_order).all()
    assets        = [a.name for a in asset_classes]
    base          = {a.name: a.neutral_weight for a in asset_classes}
    constraints   = {
        a.name: {"min": a.min_weight, "max": a.max_weight}
        for a in asset_classes
    }

    # --- carica parametri (override per-run se fornito) ---
    if coherence_factor is None:
        coherence_factor = _get_param(db, "coherence.factor", backtest_id)

    # --- carica delta dalla matrice ---
    adjustments = db.query(AllocationAdjustment).all()
    delta_map: dict[tuple[str, str, str], float] = {
        (r.pillar, r.regime, r.asset): r.delta
        for r in adjustments
    }

    # --- coefficiente di coerenza ---
    n_neutral = sum(1 for r in regimes.values() if r == "neutral")
    coherence = 1.0 - (n_neutral / len(regimes)) * coherence_factor

    # --- somma dei delta ---
    total_delta = {asset: 0.0 for asset in assets}
    for pillar, regime in regimes.items():
        for asset in assets:
            total_delta[asset] += delta_map.get((pillar, regime, asset), 0.0)

    # --- applica coerenza e calcola target ---
    target = {
        asset: base[asset] + total_delta[asset] * coherence
        for asset in assets
    }

    # --- applica vincoli e riscala ---
    target = _apply_constraints(target, constraints)
    target = _rescale(target)

    return target

def compute_effective_allocation(
    db: Session,
    date: datetime.date,
    target: dict[str, float],
    backtest_id: int,
    run_id: int | None = None,
    allocation_alpha: float | None = None,
) -> dict[str, float]:

    alpha = allocation_alpha if allocation_alpha is not None else _get_param(db, "allocation.alpha", backtest_id)

    # carica allocazione effettiva del mese precedente (scoped per run_id)
    prev_date = (date.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)

    prev_records = (
        db.query(AllocationHistory)
        .filter(
            AllocationHistory.date == prev_date,
            AllocationHistory.run_id == run_id,
        )
        .all()
    )

    if not prev_records:
        return target

    prev = {r.asset: r.effective for r in prev_records}

    effective = {
        asset: prev[asset] + alpha * (target[asset] - prev[asset])
        if asset in prev else target[asset]
        for asset in target
    }

    return effective


def save_allocation(
    db: Session,
    date: datetime.date,
    target: dict[str, float],
    effective: dict[str, float],
    run_id: int | None = None,
) -> None:

    for asset in target:
        existing = (
            db.query(AllocationHistory)
            .filter(
                AllocationHistory.date == date,
                AllocationHistory.asset == asset,
                AllocationHistory.run_id == run_id,
            )
            .first()
        )
        if existing:
            existing.target = target[asset]      # type: ignore[assignment]
            existing.effective = effective[asset]  # type: ignore[assignment]
        else:
            db.add(AllocationHistory(
                date=date,
                asset=asset,
                run_id=run_id,
                target=target[asset],
                effective=effective[asset],
            ))

    db.commit()