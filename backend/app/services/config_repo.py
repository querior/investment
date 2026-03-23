"""
Lettura della configurazione dal database.
Unico punto di accesso per dati che erano hardcoded nei config.py statici.
"""
from sqlalchemy.orm import Session
from app.db.macro_indicator import MacroIndicator, IndicatorSource, IndicatorFrequency
from app.db.market_symbol import MarketSymbol
from app.db.processed_indicator import ProcessedIndicator
from app.db.pillar import Pillar
from app.db.pillar_component import PillarComponent
from app.db.composite_score import CompositeScore
from app.db.composite_score_weight import CompositeScoreWeight
from app.db.regime_threshold import RegimeThreshold
from app.db.asset_class import AssetClass
from app.db.sensitivity_coefficient import SensitivityCoefficient
from app.db.allocation_parameter import AllocationParameter


def get_fred_tickers(db: Session) -> set[str]:
    """Tutti i ticker FRED attivi."""
    rows = db.query(MacroIndicator.ticker).filter(MacroIndicator.is_active.is_(True)).all()
    return {r[0] for r in rows}


def get_market_symbols(db: Session) -> list[tuple[str, str]]:
    """Lista di (symbol, source) per tutti i market symbol attivi."""
    rows = db.query(MarketSymbol).filter(MarketSymbol.is_active.is_(True)).all()
    return [(r.symbol, r.source.value) for r in rows]


def get_processed_map(db: Session) -> list[tuple[str, str, str, str | None, int, float]]:
    """
    Lista di (source_ticker, output_name, transform, resample, z_score_window, z_score_clip)
    per tutti i processed indicator attivi.
    """
    rows = (
        db.query(ProcessedIndicator, MacroIndicator)
        .join(MacroIndicator, ProcessedIndicator.source_indicator_id == MacroIndicator.id)
        .filter(ProcessedIndicator.is_active.is_(True))
        .all()
    )
    return [
        (
            ind.ticker,
            proc.output_name,
            proc.transform.value,
            proc.resample.value if proc.resample else None,
            proc.z_score_window,
            proc.z_score_clip,
        )
        for proc, ind in rows
    ]


def get_pillars(db: Session) -> dict[str, list[str]]:
    """
    Dict {pillar_name: [output_names]} per tutti i pillar attivi,
    ordinati per display_order.
    """
    pillars = (
        db.query(Pillar)
        .filter(Pillar.is_active.is_(True))
        .order_by(Pillar.display_order)
        .all()
    )
    result: dict[str, list[str]] = {}
    for pillar in pillars:
        components = (
            db.query(PillarComponent, ProcessedIndicator)
            .join(ProcessedIndicator, PillarComponent.processed_indicator_id == ProcessedIndicator.id)
            .filter(PillarComponent.pillar_id == pillar.id)
            .filter(ProcessedIndicator.is_active.is_(True))
            .order_by(PillarComponent.display_order)
            .all()
        )
        result[pillar.name] = [proc.output_name for _, proc in components]
    return result


def get_macro_score_weights(db: Session, score_name: str = "MacroScore") -> dict[str, float]:
    """Dict {pillar_name: weight} per lo score indicato."""
    score = db.query(CompositeScore).filter(CompositeScore.name == score_name).one_or_none()
    if not score:
        return {}
    rows = (
        db.query(CompositeScoreWeight, Pillar)
        .join(Pillar, CompositeScoreWeight.pillar_id == Pillar.id)
        .filter(CompositeScoreWeight.composite_score_id == score.id)
        .all()
    )
    return {pillar.name: w.weight for w, pillar in rows}


def get_regime_thresholds(db: Session, score_name: str = "MacroScore") -> list[tuple[float | None, str]]:
    """
    Lista di (threshold_min, nome_regime) ordinata per display_order.
    threshold_min=None indica il regime senza lower bound (il più basso).
    """
    score = db.query(CompositeScore).filter(CompositeScore.name == score_name).one_or_none()
    if not score:
        return []
    rows = (
        db.query(RegimeThreshold)
        .filter(RegimeThreshold.composite_score_id == score.id)
        .order_by(RegimeThreshold.display_order)
        .all()
    )
    return [(r.threshold_min, r.name) for r in rows]


def get_neutral_allocation(db: Session) -> dict[str, float]:
    """Dict {asset_name: neutral_weight}."""
    rows = db.query(AssetClass).order_by(AssetClass.display_order).all()
    return {r.name: r.neutral_weight for r in rows}


def get_asset_classes(db: Session) -> list[AssetClass]:
    """Lista di AssetClass ordinata per display_order."""
    return db.query(AssetClass).order_by(AssetClass.display_order).all()


def get_sensitivity(db: Session) -> dict[str, dict[str, float]]:
    """Dict {pillar_name: {asset_name: coefficient}}."""
    rows = (
        db.query(SensitivityCoefficient, Pillar, AssetClass)
        .join(Pillar, SensitivityCoefficient.pillar_id == Pillar.id)
        .join(AssetClass, SensitivityCoefficient.asset_class_id == AssetClass.id)
        .all()
    )
    result: dict[str, dict[str, float]] = {}
    for coeff, pillar, asset in rows:
        result.setdefault(pillar.name, {})[asset.name] = coeff.coefficient
    return result


def get_allocation_parameter(db: Session, key: str, default: float) -> float:
    """Legge un parametro scalare dell'allocation engine."""
    row = db.query(AllocationParameter).filter(AllocationParameter.key == key).one_or_none()
    return row.value if row else default


# ---------------------------------------------------------------------------
# Meta helpers (descrizioni, formule, frequenze — per catalog e series API)
# ---------------------------------------------------------------------------

_TRANSFORM_LABEL: dict[str, str] = {
    "YOY":   "YoY % change",
    "LEVEL": "level",
    "DELTA": "monthly delta",
}

_TRANSFORM_FORMULA: dict[str, str] = {
    "YOY":   "(xₜ / xₜ₋₁₂ − 1) × 100  →  z = (x − μ₆₀) / σ₆₀, clip ±3",
    "LEVEL": "xₜ − xₜ₋₁  →  z = (x − μ₆₀) / σ₆₀, clip ±3",
    "DELTA": "xₜ − xₜ₋₁  →  z = (x − μ₆₀) / σ₆₀, clip ±3",
}


def get_indicator_meta(db: Session) -> dict[str, dict]:
    """Dict {ticker: {description, frequency, source}} per tutti gli indicator attivi."""
    rows = db.query(MacroIndicator).filter(MacroIndicator.is_active.is_(True)).all()
    return {
        r.ticker: {
            "description": r.description,
            "frequency": r.frequency.value,
            "source": r.source.value,
        }
        for r in rows
    }


def get_market_symbol_meta(db: Session) -> dict[str, dict]:
    """Dict {symbol: {description, source, frequency}} per tutti i market symbol attivi."""
    rows = db.query(MarketSymbol).filter(MarketSymbol.is_active.is_(True)).all()
    return {
        r.symbol: {
            "description": r.description,
            "source": r.source.value,
            "frequency": "DAILY",
        }
        for r in rows
    }


def get_processed_meta(db: Session) -> dict[str, dict]:
    """
    Dict {output_name: {description, formula, frequency, source_ticker, transform}}
    per tutti i processed indicator attivi.
    """
    rows = (
        db.query(ProcessedIndicator, MacroIndicator)
        .join(MacroIndicator, ProcessedIndicator.source_indicator_id == MacroIndicator.id)
        .filter(ProcessedIndicator.is_active.is_(True))
        .all()
    )
    result: dict[str, dict] = {}
    for proc, ind in rows:
        tf = proc.transform.value
        result[proc.output_name] = {
            "description": f"{ind.description} — {_TRANSFORM_LABEL.get(tf, tf)}",
            "formula": _TRANSFORM_FORMULA.get(tf, ""),
            "source_ticker": ind.ticker,
            "transform": tf,
            "frequency": ind.frequency.value,
        }
    return result


def get_pillar_meta(db: Session) -> dict[str, dict]:
    """Dict {pillar_name: {description, formula, frequency}} per tutti i pillar attivi."""
    pillars_map = get_pillars(db)
    pillar_rows = (
        db.query(Pillar)
        .filter(Pillar.is_active.is_(True))
        .order_by(Pillar.display_order)
        .all()
    )
    result: dict[str, dict] = {}
    for pillar in pillar_rows:
        indicators = pillars_map.get(pillar.name, [])
        result[pillar.name] = {
            "description": pillar.description,
            "formula": "mean(" + ", ".join(f"z({ind})" for ind in indicators) + ")",
            "frequency": "MONTHLY",
        }
    return result


def get_composite_score_meta(db: Session, score_name: str = "MacroScore") -> dict:
    """Meta (description, formula, frequency) per un composite score."""
    score = db.query(CompositeScore).filter(CompositeScore.name == score_name).one_or_none()
    if not score:
        return {}
    weights = get_macro_score_weights(db, score_name)
    parts = []
    for pillar, w in weights.items():
        sign = "+" if w >= 0 else "−"
        parts.append(f"{sign} {abs(w)}·{pillar}")
    formula = " ".join(parts).lstrip("+ ").strip()
    return {
        "description": score.description,
        "formula": formula,
        "frequency": "MONTHLY",
    }


def get_asset_proxy_map(db: Session) -> dict[str, str]:
    """Dict {asset_name: symbol} dai proxy delle asset class."""
    rows = (
        db.query(AssetClass, MarketSymbol)
        .join(MarketSymbol, AssetClass.proxy_id == MarketSymbol.id)
        .order_by(AssetClass.display_order)
        .all()
    )
    return {asset.name: sym.symbol for asset, sym in rows}
