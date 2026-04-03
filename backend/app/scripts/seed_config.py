"""Seed della configurazione base del sistema.

Popola le entity di configurazione con i valori attualmente hardcoded.
Idempotente: skippa i record già esistenti (confronto su chiave naturale).

Run inside backend container:
    python -m app.scripts.seed_config
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.macro_indicator import MacroIndicator, IndicatorSource, IndicatorFrequency
from app.db.market_symbol import MarketSymbol, MarketSource, AssetType
from app.db.processed_indicator import ProcessedIndicator, TransformType, ResampleMethod
from app.db.pillar import Pillar
from app.db.pillar_component import PillarComponent
from app.db.asset_class import AssetClass
from app.db.backtest_parameter import BacktestParameter
from app.db.allocation_adjustment import AllocationAdjustment


# ---------------------------------------------------------------------------
# Dati sorgente
# ---------------------------------------------------------------------------

_INDICATORS = [
    ("CUMFNS",    "Capacity Utilization: Manufacturing",                       IndicatorFrequency.MONTHLY),
    ("GDPC1",     "Real Gross Domestic Product",                               IndicatorFrequency.QUARTERLY),
    ("W875RX1",   "Real personal income excluding current transfer receipts",  IndicatorFrequency.MONTHLY),
    ("INDPRO",    "Industrial Production Index",                               IndicatorFrequency.MONTHLY),
    ("CPIAUCSL",  "Consumer Price Index (All Urban)",                          IndicatorFrequency.MONTHLY),
    ("PPIFIS",    "Producer Price Index",                                      IndicatorFrequency.MONTHLY),
    ("PPIACO",    "Producer Price Index by Commodity: All Commodities",        IndicatorFrequency.MONTHLY),
    ("EXPINF5YR", "5-Year Expected Inflation",                                 IndicatorFrequency.MONTHLY),
    ("T5YIE",     "5-Year Breakeven Inflation Rate",                           IndicatorFrequency.DAILY),
    ("FEDFUNDS",  "Federal Funds Effective Rate",                              IndicatorFrequency.MONTHLY),
    ("T10Y2Y",    "10-Year Treasury Minus 2-Year Treasury",                    IndicatorFrequency.DAILY),
    ("VIXCLS",    "CBOE Volatility Index (VIX)",                               IndicatorFrequency.DAILY),
    ("BAA10Y",    "Moody's Baa Corporate Bond Spread",                         IndicatorFrequency.DAILY),
    ("NFCI",      "Chicago Fed National Financial Conditions",                 IndicatorFrequency.WEEKLY),
]

_MARKET_SYMBOLS = [
    ("SPY", "S&P 500 ETF",                              MarketSource.YAHOO, AssetType.ETF),
    ("IEF", "iShares 7-10 Year Treasury Bond ETF",      MarketSource.YAHOO, AssetType.ETF),
    ("DBC", "Invesco DB Commodity Index Tracking Fund", MarketSource.YAHOO, AssetType.ETF),
    ("BIL", "SPDR Bloomberg 1-3 Month T-Bill ETF",      MarketSource.YAHOO, AssetType.ETF),
]

# (ticker_sorgente, output_name, transform, resample)
_PROCESSED_MAP = [
    # Growth — tutti MONTHLY, nessun resample
    ("CUMFNS",    "CUMFNS",         TransformType.LEVEL, None),
    ("INDPRO",    "INDPRO_YOY",     TransformType.YOY,   None),
    ("W875RX1",   "W875RX1_YOY",    TransformType.YOY,   None),
    # Inflation — tutti MONTHLY, nessun resample
    ("CPIAUCSL",  "CPI_YOY",        TransformType.YOY,   None),
    ("PPIACO",    "PPIACO_YOY",     TransformType.YOY,   None),
    ("EXPINF5YR", "EXPINF5YR",      TransformType.LEVEL, None),
    # Policy — FEDFUNDS MONTHLY, T10Y2Y DAILY → resample
    ("FEDFUNDS",  "FEDFUNDS",       TransformType.LEVEL, None),
    ("FEDFUNDS",  "FEDFUNDS_DELTA", TransformType.DELTA, None),
    ("T10Y2Y",    "T10Y2Y_M",       TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
    # Risk — tutti DAILY/WEEKLY → resample
    ("BAA10Y",    "BAA10Y_M",       TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
    ("VIXCLS",    "VIXCLS_M",       TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
    ("NFCI",      "NFCI_M",         TransformType.LEVEL, ResampleMethod.MONTHLY_MEAN),
]

# (nome_pillar, descrizione, display_order, [output_names])
_PILLARS = [
    ("Growth",    "Forza del ciclo economico reale",          1, ["CUMFNS", "W875RX1_YOY", "INDPRO_YOY"]),
    ("Inflation", "Pressione inflattiva realizzata e attesa", 2, ["CPI_YOY", "PPIACO_YOY", "EXPINF5YR"]),
    ("Policy",    "Stance della banca centrale (Fed)",        3, ["FEDFUNDS", "T10Y2Y_M", "FEDFUNDS_DELTA"]),
    ("Risk",      "Stress finanziario e risk aversion",       4, ["BAA10Y_M", "VIXCLS_M", "NFCI_M"]),
]

# (nome_asset, neutral_weight, max_weight, proxy_symbol)
_ASSET_CLASSES = [
    ("Equity",      0.50, 0.70, "SPY"),
    ("Bond",        0.30, 0.55, "IEF"),
    ("Commodities", 0.10, 0.30, "DBC"),
    ("Cash",        0.10, 0.30, "BIL"),
]

# (pillar, regime, asset, delta)
# delta in percentuale (0.08 = +8%). Ogni riga (pillar, regime) deve sommare a zero.
# Regime neutral → delta = 0 convenzionalmente (non inserito).
# Valori indicativi da layer-long.md — da calibrare empiricamente.
_ALLOCATION_ADJUSTMENTS = [
    ("Growth",    "expansion",   "Equity",      0.08),
    ("Growth",    "expansion",   "Bond",        -0.05),
    ("Growth",    "expansion",   "Commodities",  0.03),
    ("Growth",    "expansion",   "Cash",        -0.06),
    ("Growth",    "contraction", "Equity",      -0.08),
    ("Growth",    "contraction", "Bond",         0.05),
    ("Growth",    "contraction", "Commodities", -0.03),
    ("Growth",    "contraction", "Cash",         0.06),
    ("Inflation", "expansion",   "Equity",      -0.05),
    ("Inflation", "expansion",   "Bond",        -0.08),
    ("Inflation", "expansion",   "Commodities",  0.10),
    ("Inflation", "expansion",   "Cash",         0.03),
    ("Inflation", "contraction", "Equity",       0.03),
    ("Inflation", "contraction", "Bond",         0.05),
    ("Inflation", "contraction", "Commodities", -0.08),
    ("Inflation", "contraction", "Cash",         0.00),
    ("Policy",    "expansion",   "Equity",       0.06),
    ("Policy",    "expansion",   "Bond",         0.05),
    ("Policy",    "expansion",   "Commodities",  0.00),
    ("Policy",    "expansion",   "Cash",        -0.11),
    ("Policy",    "contraction", "Equity",      -0.06),
    ("Policy",    "contraction", "Bond",        -0.05),
    ("Policy",    "contraction", "Commodities",  0.00),
    ("Policy",    "contraction", "Cash",         0.11),
    ("Risk",      "expansion",   "Equity",       0.05),
    ("Risk",      "expansion",   "Bond",        -0.03),
    ("Risk",      "expansion",   "Commodities",  0.02),
    ("Risk",      "expansion",   "Cash",        -0.04),
    ("Risk",      "contraction", "Equity",      -0.08),
    ("Risk",      "contraction", "Bond",         0.05),
    ("Risk",      "contraction", "Commodities", -0.02),
    ("Risk",      "contraction", "Cash",         0.05),
]

_ALLOCATION_PARAMETERS = [
    ("smoothing.alpha",   0.4, "Alpha EWM sullo z-score per indicatore"),
    ("allocation.alpha",  0.3, "Alpha smoothing allocazione mensile (EWM verso target)"),
    ("coherence.factor",  0.5, "Riduzione intensità aggiustamenti quando pillar in neutral"),
]


# ---------------------------------------------------------------------------
# Funzioni di seed
# ---------------------------------------------------------------------------

def seed_indicators(db: Session) -> dict[str, int]:
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


def seed_asset_classes(db: Session, symbol_map: dict[str, int]) -> dict[str, int]:
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


def seed_allocation_adjustments(db: Session):
    for pillar, regime, asset, delta in _ALLOCATION_ADJUSTMENTS:
        existing = db.query(AllocationAdjustment).filter_by(
            pillar=pillar, regime=regime, asset=asset
        ).first()
        if existing:
            continue
        db.add(AllocationAdjustment(pillar=pillar, regime=regime, asset=asset, delta=delta))
        print(f"  [allocation_adjustment] {pillar} × {regime} × {asset} = {delta:+.0%}")


def seed_allocation_parameters(db: Session):
    for key, value, description in _ALLOCATION_PARAMETERS:
        existing = db.query(BacktestParameter).filter_by(key=key).first()
        if existing:
            continue
        db.add(BacktestParameter(key=key, value=value, description=description))
        print(f"  [allocation_parameter] {key} = {value}")


# ---------------------------------------------------------------------------
# Seed condizionale (usato allo startup)
# ---------------------------------------------------------------------------

def seed_if_needed(db: Session) -> bool:
    """
    Esegue il seed solo se la configurazione non è ancora presente.
    Usa il count di macro_indicators come sentinel.
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
        seed_pillars(db, processed_map)
        seed_asset_classes(db, symbol_map)
        seed_allocation_adjustments(db)
        # seed_allocation_parameters(db)
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
        seed_pillars(db, processed_map)

        print("=== seed asset classes ===")
        seed_asset_classes(db, symbol_map)

        print("=== seed allocation adjustments ===")
        seed_allocation_adjustments(db)

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
