from typing import Dict
from sqlalchemy.orm import Session


def f(x: float) -> float:
    """Funzione di risposta del pillar. Saturazione lineare."""
    if x > 2.0:
        return 1.0
    if x < -2.0:
        return -1.0
    return x / 2.0


def compute_allocation_deltas(db: Session, pillars: Dict[str, float]) -> Dict[str, float]:
    from app.services.config_repo import get_sensitivity, get_asset_classes, get_allocation_parameter

    sensitivity = get_sensitivity(db)
    assets = [a.name for a in get_asset_classes(db)]
    K = get_allocation_parameter(db, "scale_factor_k", 0.05)
    MAX_ABS = get_allocation_parameter(db, "max_abs_delta", 0.10)

    raw_tilt = {asset: 0.0 for asset in assets}
    for pillar, score in pillars.items():
        if pillar not in sensitivity:
            continue
        signal = f(score)
        for asset in assets:
            coeff = sensitivity[pillar].get(asset, 0.0)
            raw_tilt[asset] += signal * coeff

    for asset in assets:
        raw_tilt[asset] *= K

    mean_tilt = sum(raw_tilt.values()) / len(raw_tilt)
    deltas = {asset: raw_tilt[asset] - mean_tilt for asset in assets}

    for asset in assets:
        if deltas[asset] > MAX_ABS:
            deltas[asset] = MAX_ABS
        if deltas[asset] < -MAX_ABS:
            deltas[asset] = -MAX_ABS

    return {
        asset: 0.0 if abs(val) < 1e-12 else float(val)
        for asset, val in deltas.items()
    }


def compute_allocation(db: Session, pillars: dict) -> dict:
    from app.services.config_repo import get_neutral_allocation

    neutral = get_neutral_allocation(db)
    deltas = compute_allocation_deltas(db, pillars)

    allocation = {
        asset: neutral[asset] + deltas.get(asset, 0.0)
        for asset in neutral
    }

    total = sum(allocation.values())
    return {asset: weight / total for asset, weight in allocation.items()}
