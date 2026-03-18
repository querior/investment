from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal
import os
from fredapi import Fred
from app.db.deps import get_db
from app.services.ingest.bootstrap_macro import ingest_all_macro
from app.services.ingest.fred import ingest_fred_series_delta, ingest_fred_series_full
from app.services.ingest.market import ingest_market_delta, ingest_market_full
from app.services.processed.service import process_indicator
from app.services.processed.config import PROCESSED_MAP
from app.services.pillars.config import PILLARS
from app.services.pillars.service import compute_pillars

router = APIRouter(tags=["ingest"])

# Indicatori FRED ingestionabili direttamente (serie raw, non derivate)
FRED_RAW_INDICATORS = {
    "CUMFNS", "GDPC1", "W875RX1", "INDPRO", "CPIAUCSL", "PPIFIS", "PPIACO",
    "T5YIE", "FEDFUNDS", "T10Y2Y", "VIXCLS", "BAA10Y", "NFCI", "EXPINF5YR",
}

MARKET_SYMBOLS = {"SPY", "IEF", "DBC", "BIL"}

PILLAR_NAMES = set(PILLARS.keys())

# mappa target_indicator → (src, tgt, transform) per lookup rapido
_TARGET_TO_PROCESS = {tgt: (src, tgt, tf) for src, tgt, tf in PROCESSED_MAP}


def _compute_pillar(db: Session, pillar: str) -> int:
    """Ricalcola process_indicator per tutti gli indicatori del pillar, poi compute_pillars."""
    for indicator in PILLARS[pillar]:
        if indicator in _TARGET_TO_PROCESS:
            src, tgt, tf = _TARGET_TO_PROCESS[indicator]
            process_indicator(db, src, tgt, tf)
    compute_pillars(db)
    from sqlalchemy import func
    from app.db.macro_pillar import MacroPillar
    count = db.query(func.count(MacroPillar.date)).filter(MacroPillar.pillar == pillar).scalar()
    return count or 0


class IngestSeriesRequest(BaseModel):
    symbol: str
    mode: Literal["delta", "full"]


@router.post("/ingest/macro")
def ingest_macro_all():
    ingest_all_macro()


@router.post("/ingest/series")
def ingest_series(
    body: IngestSeriesRequest,
    db: Session = Depends(get_db),
):
    symbol = body.symbol

    # MacroScore — ricalcola tutta la pipeline
    if symbol == "MacroScore":
        n_indicators = len(PROCESSED_MAP)
        for src, tgt, tf in PROCESSED_MAP:
            process_indicator(db, src, tgt, tf)
        compute_pillars(db)
        return {
            "symbol": symbol,
            "mode": "computed",
            "inserted": None,
            "detail": f"Pipeline completa: {n_indicators} indicatori processati, pillar scores ricalcolati",
        }

    # Pillar — ricalcola gli indicatori del pillar specifico
    if symbol in PILLAR_NAMES:
        n_indicators = len(PILLARS[symbol])
        inserted = _compute_pillar(db, symbol)
        return {
            "symbol": symbol,
            "mode": "computed",
            "inserted": inserted,
            "detail": f"Pillar {symbol}: {n_indicators} indicatori processati, {inserted} score calcolati",
        }

    # Macro processed — ricalcola process_indicator per il target specifico
    if symbol in _TARGET_TO_PROCESS:
        src, tgt, tf = _TARGET_TO_PROCESS[symbol]
        process_indicator(db, src, tgt, tf)
        from sqlalchemy import func
        from app.db.macro_processed import MacroProcessed
        count = db.query(func.count(MacroProcessed.date)).filter(MacroProcessed.indicator == tgt).scalar() or 0
        return {
            "symbol": symbol,
            "mode": "computed",
            "inserted": count,
            "detail": f"{tgt}: ricalcolato da {src} (transform={tf}), {count} punti totali",
        }

    symbol_upper = symbol.upper()

    # Market (yfinance)
    if symbol_upper in MARKET_SYMBOLS:
        if body.mode == "delta":
            inserted = ingest_market_delta(db, symbol_upper)
            detail = (
                f"{symbol_upper}: {inserted} nuovi record scaricati da Yahoo Finance"
                if inserted > 0
                else f"{symbol_upper}: già aggiornato, nessun nuovo record"
            )
        else:
            inserted = ingest_market_full(db, symbol_upper)
            detail = f"{symbol_upper}: {inserted} record scaricati da Yahoo Finance (serie completa)"
        return {"symbol": symbol_upper, "mode": body.mode, "inserted": inserted, "detail": detail}

    # FRED raw
    if symbol_upper in FRED_RAW_INDICATORS:
        fred = Fred(api_key=os.getenv("FRED_API_KEY"))
        if body.mode == "delta":
            inserted = ingest_fred_series_delta(db, symbol_upper, fred)
            detail = (
                f"{symbol_upper}: {inserted} nuovi record scaricati da FRED"
                if inserted > 0
                else f"{symbol_upper}: già aggiornato, nessun nuovo record"
            )
        else:
            inserted = ingest_fred_series_full(db, symbol_upper, fred)
            detail = f"{symbol_upper}: {inserted} record scaricati da FRED (serie completa)"
        return {"symbol": symbol_upper, "mode": body.mode, "inserted": inserted, "detail": detail}

    raise HTTPException(
        status_code=422,
        detail=f"'{symbol}' non è supportato per l'ingestion diretta.",
    )