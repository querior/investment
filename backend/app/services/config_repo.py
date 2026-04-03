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
from app.db.asset_class import AssetClass
from app.db.backtest_parameter import BacktestParameter


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


def get_pillars(db: Session) -> dict[str, list[tuple[str, bool]]]:
    """
    Dict {pillar_name: [(output_name, invert), ...]} per tutti i pillar attivi,
    ordinati per display_order.
    """
    pillars = (
        db.query(Pillar)
        .filter(Pillar.is_active.is_(True))
        .order_by(Pillar.display_order)
        .all()
    )
    result: dict[str, list[tuple[str, bool]]] = {}
    for pillar in pillars:
        components = (
            db.query(PillarComponent, ProcessedIndicator)
            .join(ProcessedIndicator, PillarComponent.processed_indicator_id == ProcessedIndicator.id)
            .filter(PillarComponent.pillar_id == pillar.id)
            .filter(ProcessedIndicator.is_active.is_(True))
            .order_by(PillarComponent.display_order)
            .all()
        )
        result[pillar.name] = [
            (proc.output_name, proc.invert)
            for _, proc in components
        ]
    return result


def get_neutral_allocation(db: Session) -> dict[str, float]:
    """Dict {asset_name: neutral_weight}."""
    rows = db.query(AssetClass).order_by(AssetClass.display_order).all()
    return {r.name: r.neutral_weight for r in rows}


def get_asset_classes(db: Session) -> list[AssetClass]:
    """Lista di AssetClass ordinata per display_order."""
    return db.query(AssetClass).order_by(AssetClass.display_order).all()


def get_allocation_parameter(db: Session, key: str, backtest_id: int, default: float) -> float:
    """Legge un parametro scalare dell'allocation engine."""
    row = db.query(BacktestParameter).filter(
        BacktestParameter.key == key,
        BacktestParameter.backtest_id == backtest_id,
    ).one_or_none()
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
    "YOY":   "(xₜ / xₜ₋₁₂ − 1) × 100  →  z = (x − μ₆₀) / σ₆₀, clip ±2",
    "LEVEL": "xₜ − xₜ₋₁  →  z = (x − μ₆₀) / σ₆₀, clip ±2",
    "DELTA": "xₜ − xₜ₋₁  →  z = (x − μ₆₀) / σ₆₀, clip ±2",
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


def get_asset_proxy_map(db: Session) -> dict[str, str]:
    """Dict {asset_name: symbol} dai proxy delle asset class."""
    rows = (
        db.query(AssetClass, MarketSymbol)
        .join(MarketSymbol, AssetClass.proxy_id == MarketSymbol.id)
        .order_by(AssetClass.display_order)
        .all()
    )
    return {asset.name: sym.symbol for asset, sym in rows}
