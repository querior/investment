from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal
import os
from fredapi import Fred
from app.db.deps import get_db
from app.db.macro_processed import MacroProcessed
from app.db.macro_regimes import MacroRegime
from app.services.ingest.bootstrap_macro import ingest_all_macro
from app.services.ingest.fred import ingest_fred_series_delta, ingest_fred_series_full
from app.services.ingest.market import ingest_market_delta, ingest_market_full
from app.services.processed.service import process_indicator
from app.services.pillars.service import compute_pillars
from app.services.config_repo import get_fred_tickers, get_market_symbols, get_processed_map, get_pillars


router = APIRouter(tags=["ingest"])

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

    processed_map = get_processed_map(db)
    pillars = get_pillars(db)
    target_to_process = {tgt: (src, tgt, tf, resample, window, clip) for src, tgt, tf, resample, window, clip in processed_map}
    market_symbols = {sym for sym, _ in get_market_symbols(db)}
    fred_tickers = get_fred_tickers(db)

    # Pillar — ricalcola gli indicatori del pillar specifico
    if symbol in pillars:
        compute_pillars(db, pillar=symbol)
        count = db.query(func.count(MacroRegime.date)).filter(MacroRegime.pillar == symbol).scalar() or 0
        return {
            "symbol": symbol,
            "mode": "computed",
            "inserted": count,
            "detail": f"Pillar {symbol}: {count} regime records calcolati",
        }

    # Macro processed — ricalcola process_indicator per il target specifico
    if symbol in target_to_process:
        src, tgt, tf, resample, window, clip = target_to_process[symbol]
        process_indicator(db, src, tgt, tf, resample=resample, window=window, clip_limit=clip)
        count = db.query(func.count(MacroProcessed.date)).filter(MacroProcessed.indicator == tgt).scalar() or 0
        return {
            "symbol": symbol,
            "mode": "computed",
            "inserted": count,
            "detail": f"{tgt}: ricalcolato da {src} (transform={tf}), {count} punti totali",
        }

    symbol_upper = symbol.upper()

    # Market (yfinance)
    if symbol_upper in market_symbols:
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
    if symbol_upper in fred_tickers:
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