"""Seed della configurazione base del sistema.

Popola le entity di configurazione con i valori attualmente hardcoded.
Idempotente: skippa i record già esistenti (confronto su chiave naturale).

Run inside backend container:
    python -m app.scripts.seed_config
"""
from typing import cast
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.macro_indicator import MacroIndicator, IndicatorSource, IndicatorFrequency
from app.db.market_symbol import MarketSymbol, MarketSource, AssetType
from app.db.processed_indicator import ProcessedIndicator, TransformType, ResampleMethod
from app.db.pillar import Pillar
from app.db.pillar_component import PillarComponent
from app.db.composite_score import CompositeScore
from app.db.composite_score_weight import CompositeScoreWeight
from app.db.regime_threshold import RegimeThreshold
from app.db.asset_class import AssetClass
from app.db.sensitivity_coefficient import SensitivityCoefficient
from app.db.allocation_parameter import AllocationParameter


# ---------------------------------------------------------------------------
# Dati sorgente (corrispondono ai config.py esistenti)
# ---------------------------------------------------------------------------

_INDICATORS = [
    ("CUMFNS",   "Capacity Utilization: Manufacturing",                        IndicatorFrequency.MONTHLY),
    ("GDPC1",    "Real Gross Domestic Product",                                IndicatorFrequency.QUARTERLY),
    ("W875RX1",  "Real personal income excluding current transfer receipts",   IndicatorFrequency.MONTHLY),
    ("INDPRO",   "Industrial Production Index",                                IndicatorFrequency.MONTHLY),
    ("CPIAUCSL", "Consumer Price Index (All Urban)",                           IndicatorFrequency.MONTHLY),
    ("PPIFIS",   "Producer Price Index",                                       IndicatorFrequency.MONTHLY),
    ("PPIACO",   "Producer Price Index by Commodity: All Commodities",         IndicatorFrequency.MONTHLY),
    ("EXPINF5YR","5-Year Expected Inflation",                                  IndicatorFrequency.MONTHLY),
    ("T5YIE",    "5-Year Breakeven Inflation Rate",                            IndicatorFrequency.DAILY),
    ("FEDFUNDS", "Federal Funds Effective Rate",                               IndicatorFrequency.MONTHLY),
    ("T10Y2Y",   "10-Year Treasury Minus 2-Year Treasury",                     IndicatorFrequency.DAILY),
    ("VIXCLS",   "CBOE Volatility Index (VIX)",                                IndicatorFrequency.DAILY),
    ("BAA10Y",   "Moody's Baa Corporate Bond Spread",                          IndicatorFrequency.DAILY),
    ("NFCI",     "Chicago Fed National Financial Conditions",                  IndicatorFrequency.WEEKLY),
]

_MARKET_SYMBOLS = [
    ("SPY", "S&P 500 ETF",                                  MarketSource.YAHOO, AssetType.ETF),
    ("IEF", "iShares 7-10 Year Treasury Bond ETF",          MarketSource.YAHOO, AssetType.ETF),
    ("DBC", "Invesco DB Commodity Index Tracking Fund",     MarketSource.YAHOO, AssetType.ETF),
    ("BIL", "SPDR Bloomberg 1-3 Month T-Bill ETF",          MarketSource.YAHOO, AssetType.ETF),
]

# (ticker_sorgente, output_name, transform, resample)
# Indicatori non-MONTHLY (DAILY/WEEKLY) vengono ricampionati a MONTHLY_MEAN → suffisso _M
_PROCESSED_MAP = [
    # Growth — tutti MONTHLY, nessun resample
    ("CUMFNS",   "CUMFNS",          TransformType.LEVEL, None),
    ("INDPRO",   "INDPRO_YOY",      TransformType.YOY,   None),
    ("W875RX1",  "W875RX1_YOY",     TransformType.YOY,   None),
    # Inflation — tutti MONTHLY, nessun resample
    ("CPIAUCSL", "CPI_YOY",         TransformType.YOY,   None),
    ("PPIACO",   "PPIACO_YOY",      TransformType.YOY,   None),
    ("EXPINF5YR","EXPINF5YR",       TransformType.LEVEL, None),
    # Policy — FEDFUNDS MONTHLY, T10Y2Y DAILY → resample
    ("FEDFUNDS", "FEDFUNDS",        TransformType.LEVEL, None),
    ("FEDFUNDS", "FEDFUNDS_DELTA",  TransformType.DELTA, None),
    ("T10Y2Y",   "T10Y2Y_M",        TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
    # Risk — tutti DAILY/WEEKLY → resample
    ("BAA10Y",   "BAA10Y_M",        TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
    ("VIXCLS",   "VIXCLS_M",        TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
    ("NFCI",     "NFCI_M",          TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
]

# (nome_pillar, descrizione, display_order, [output_names])
_PILLARS = [
    ("Growth",    "Forza del ciclo economico reale",          1, ["CUMFNS", "W875RX1_YOY", "INDPRO_YOY"]),
    ("Inflation", "Pressione inflattiva realizzata e attesa", 2, ["CPI_YOY", "PPIACO_YOY", "EXPINF5YR"]),
    ("Policy",    "Stance della banca centrale (Fed)",         3, ["FEDFUNDS", "T10Y2Y_M", "FEDFUNDS_DELTA"]),
    ("Risk",      "Stress finanziario e risk aversion",        4, ["BAA10Y_M", "VIXCLS_M", "NFCI_M"]),
]

_MACRO_SCORE_WEIGHTS = {
    "Growth":    0.3,
    "Inflation": -0.3,
    "Policy":    -0.2,
    "Risk":      -0.2,
}

# (threshold_min, nome_regime, display_order)
# threshold_min=None → nessun lower bound (regime più basso)
_REGIME_THRESHOLDS = [
    (0.5,  "Espansione",    1),
    (0.0,  "Ripresa",       2),
    (-0.5, "Rallentamento", 3),
    (None, "Recessione",    4),
]

# (nome_asset, neutral_weight, max_weight, proxy_symbol)
_ASSET_CLASSES = [
    ("Equity",      0.50, 0.70, "SPY"),
    ("Bond",        0.30, 0.55, "IEF"),
    ("Commodities", 0.10, 0.30, "DBC"),
    ("Cash",        0.10, 0.30, "BIL"),
]

# (pillar, asset, coefficient)
_SENSITIVITY = [
    ("Growth",    "Equity",       1.0),
    ("Growth",    "Bond",        -0.5),
    ("Growth",    "Commodities",  0.5),
    ("Growth",    "Cash",        -0.5),
    ("Inflation", "Equity",      -0.5),
    ("Inflation", "Bond",        -1.0),
    ("Inflation", "Commodities",  1.0),
    ("Inflation", "Cash",         0.0),
    ("Policy",    "Equity",      -0.5),
    ("Policy",    "Bond",         1.0),
    ("Policy",    "Commodities", -0.5),
    ("Policy",    "Cash",         0.0),
    ("Risk",      "Equity",      -1.0),
    ("Risk",      "Bond",         0.5),
    ("Risk",      "Commodities", -0.5),
    ("Risk",      "Cash",         1.0),
]

_ALLOCATION_PARAMETERS = [
    ("scale_factor_k", 0.05, "Fattore di scala per il tilt sull'allocazione (5%)"),
    ("max_abs_delta",  0.10, "Cap assoluto per la deviazione dal peso neutro (±10%)"),
]


# ---------------------------------------------------------------------------
# Funzioni di seed
# ---------------------------------------------------------------------------

def seed_indicators(db: Session) -> dict[str, int]:
    """Ritorna mappa ticker → id."""
    mapping = {}
    for ticker, description, frequency in _INDICATORS:
        existing = db.query(MacroIndicator).filter_by(ticker=ticker).first()
        if existing:
            mapping[ticker] = existing.id
            continue
        obj = MacroIndicator(
            ticker=ticker,
            source=IndicatorSource.FRED,
            description=description,
            frequency=frequency,
        )
        db.add(obj)
        db.flush()
        mapping[ticker] = obj.id
        print(f"  [indicator] {ticker}")
    return mapping


def seed_market_symbols(db: Session) -> dict[str, int]:
    """Ritorna mappa symbol → id."""
    mapping = {}
    for symbol, description, source, asset_type in _MARKET_SYMBOLS:
        existing = db.query(MarketSymbol).filter_by(symbol=symbol).first()
        if existing:
            mapping[symbol] = existing.id
            continue
        obj = MarketSymbol(
            symbol=symbol,
            description=description,
            source=source,
            asset_type=asset_type,
        )
        db.add(obj)
        db.flush()
        mapping[symbol] = obj.id
        print(f"  [market_symbol] {symbol}")
    return mapping


def seed_processed_indicators(db: Session, indicator_map: dict[str, int]) -> dict[str, int]:
    """Ritorna mappa output_name → id."""
    mapping = {}
    for ticker, output_name, transform, resample in _PROCESSED_MAP:
        existing = db.query(ProcessedIndicator).filter_by(output_name=output_name).first()
        if existing:
            mapping[output_name] = existing.id
            continue
        obj = ProcessedIndicator(
            output_name=output_name,
            source_indicator_id=indicator_map[ticker],
            transform=transform,
            resample=resample,
        )
        db.add(obj)
        db.flush()
        mapping[output_name] = obj.id
        resample_label = f" + resample({resample.value})" if resample else ""
        print(f"  [processed_indicator] {output_name} ({transform.value}{resample_label})")
    return mapping


def seed_pillars(db: Session, processed_map: dict[str, int]) -> dict[str, int]:
    """Ritorna mappa nome_pillar → id."""
    pillar_map = {}
    for name, description, display_order, indicators in _PILLARS:
        existing = db.query(Pillar).filter_by(name=name).first()
        if existing:
            pillar_map[name] = existing.id
        else:
            obj = Pillar(name=name, description=description, display_order=display_order)
            db.add(obj)
            db.flush()
            pillar_map[name] = obj.id
            print(f"  [pillar] {name}")

        for order, output_name in enumerate(indicators):
            proc_id = processed_map[output_name]
            existing_comp = db.query(PillarComponent).filter_by(
                pillar_id=pillar_map[name],
                processed_indicator_id=proc_id,
            ).first()
            if existing_comp:
                continue
            db.add(PillarComponent(
                pillar_id=pillar_map[name],
                processed_indicator_id=proc_id,
                weight=1.0,
                display_order=order,
            ))
            print(f"  [pillar_component] {name} ← {output_name}")

    return pillar_map


def seed_composite_score(db: Session, pillar_map: dict[str, int]) -> int:
    """Ritorna id del MacroScore."""
    existing = db.query(CompositeScore).filter_by(name="MacroScore").first()
    if existing:
        score_id = cast(int, existing.id)
    else:
        obj = CompositeScore(
            name="MacroScore",
            description="MacroScore composito (Growth, Inflation, Policy, Risk)",
            display_order=1,
        )
        db.add(obj)
        db.flush()
        score_id = cast(int, obj.id)
        print("  [composite_score] MacroScore")

    for pillar_name, weight in _MACRO_SCORE_WEIGHTS.items():
        existing_w = db.query(CompositeScoreWeight).filter_by(
            composite_score_id=score_id,
            pillar_id=pillar_map[pillar_name],
        ).first()
        if existing_w:
            continue
        db.add(CompositeScoreWeight(
            composite_score_id=score_id,
            pillar_id=pillar_map[pillar_name],
            weight=weight,
        ))
        print(f"  [composite_score_weight] MacroScore ← {pillar_name} ({weight:+})")

    for threshold_min, name, display_order in _REGIME_THRESHOLDS:
        existing_r = db.query(RegimeThreshold).filter_by(
            composite_score_id=score_id,
            name=name,
        ).first()
        if existing_r:
            continue
        db.add(RegimeThreshold(
            composite_score_id=score_id,
            name=name,
            threshold_min=threshold_min,
            display_order=display_order,
        ))
        print(f"  [regime_threshold] {name} (min={threshold_min})")

    return score_id


def seed_asset_classes(db: Session, symbol_map: dict[str, int]) -> dict[str, int]:
    """Ritorna mappa nome_asset → id."""
    mapping = {}
    for order, (name, neutral_weight, max_weight, proxy_symbol) in enumerate(_ASSET_CLASSES):
        existing = db.query(AssetClass).filter_by(name=name).first()
        if existing:
            mapping[name] = existing.id
            continue
        obj = AssetClass(
            name=name,
            neutral_weight=neutral_weight,
            max_weight=max_weight,
            proxy_id=symbol_map[proxy_symbol],
            display_order=order,
        )
        db.add(obj)
        db.flush()
        mapping[name] = obj.id
        print(f"  [asset_class] {name} (neutral={neutral_weight}, proxy={proxy_symbol})")
    return mapping


def seed_sensitivity(db: Session, pillar_map: dict[str, int], asset_map: dict[str, int]):
    for pillar_name, asset_name, coefficient in _SENSITIVITY:
        existing = db.query(SensitivityCoefficient).filter_by(
            pillar_id=pillar_map[pillar_name],
            asset_class_id=asset_map[asset_name],
        ).first()
        if existing:
            continue
        db.add(SensitivityCoefficient(
            pillar_id=pillar_map[pillar_name],
            asset_class_id=asset_map[asset_name],
            coefficient=coefficient,
        ))
        print(f"  [sensitivity] {pillar_name} × {asset_name} = {coefficient:+}")


def seed_allocation_parameters(db: Session):
    for key, value, description in _ALLOCATION_PARAMETERS:
        existing = db.query(AllocationParameter).filter_by(key=key).first()
        if existing:
            continue
        db.add(AllocationParameter(key=key, value=value, description=description))
        print(f"  [allocation_parameter] {key} = {value}")


# ---------------------------------------------------------------------------
# Seed condizionale (usato allo startup)
# ---------------------------------------------------------------------------

def seed_if_needed(db: Session) -> bool:
    """
    Esegue il seed solo se la configurazione non è ancora presente.
    Usa il count di macro_indicators come sentinel.
    Ritorna True se il seed è stato eseguito, False se già presente.
    """
    import logging
    logger = logging.getLogger(__name__)

    if db.query(MacroIndicator).count() > 0:
        logger.info("seed_config: configurazione già presente, skip.")
        return False

    logger.info("seed_config: prima esecuzione, avvio seed configurazione...")
    try:
        indicator_map = seed_indicators(db)
        symbol_map = seed_market_symbols(db)
        processed_map = seed_processed_indicators(db, indicator_map)
        pillar_map = seed_pillars(db, processed_map)
        seed_composite_score(db, pillar_map)
        asset_map = seed_asset_classes(db, symbol_map)
        seed_sensitivity(db, pillar_map, asset_map)
        seed_allocation_parameters(db)
        db.commit()
        logger.info("seed_config: completato.")
        return True
    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    db: Session = SessionLocal()
    try:
        print("=== seed indicators ===")
        indicator_map = seed_indicators(db)

        print("=== seed market symbols ===")
        symbol_map = seed_market_symbols(db)

        print("=== seed processed indicators ===")
        processed_map = seed_processed_indicators(db, indicator_map)

        print("=== seed pillars ===")
        pillar_map = seed_pillars(db, processed_map)

        print("=== seed composite score ===")
        seed_composite_score(db, pillar_map)

        print("=== seed asset classes ===")
        asset_map = seed_asset_classes(db, symbol_map)

        print("=== seed sensitivity matrix ===")
        seed_sensitivity(db, pillar_map, asset_map)

        print("=== seed allocation parameters ===")
        seed_allocation_parameters(db)

        db.commit()
        print("\nDone.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
