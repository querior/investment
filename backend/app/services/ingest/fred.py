from fredapi import Fred
from sqlalchemy.orm import Session
from typing import cast
from app.db.session import SessionLocal
from app.db.macro_raw import MacroRaw
from app.db.meta_ingestion import IngestionState
from datetime import date
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _upsert_series(db: Session, series_id: str, data) -> int:
    count = 0
    for idx, value in data.items():
        if value is None:
            continue
        db.merge(MacroRaw(
            date=idx.date() if hasattr(idx, "date") else idx,
            indicator=series_id,
            value=float(value),
            source="FRED",
        ))
        count += 1
    return count


def _get_last_date(db: Session, key: str) -> date | None:
    row = db.query(IngestionState).filter(IngestionState.key == key).one_or_none()
    return cast(date, row.last_date) if row else None


def _set_last_date(db: Session, key: str, d: date):
    row = db.query(IngestionState).filter(IngestionState.key == key).one_or_none()
    if row:
        row.last_date = d  # type: ignore
    else:
        db.add(IngestionState(key=key, last_date=d))


def ingest_fred_series(series_id: str, fred: Fred):
    """Full ingest — scarica l'intera serie storica."""
    data = fred.get_series(series_id)
    db = SessionLocal()
    try:
        _upsert_series(db, series_id, data)
        db.commit()
    finally:
        db.close()


def ingest_fred_series_delta(db: Session, series_id: str, fred: Fred) -> int:
    """Delta ingest — scarica solo i dati dall'ultima data salvata."""
    key = f"FRED:{series_id}"
    last_date = _get_last_date(db, key)
    data = fred.get_series(series_id, observation_start=last_date)
    if data.empty:
        return 0
    count = _upsert_series(db, series_id, data)
    if count > 0:
        last = max(pd.DatetimeIndex(data.index).date)
        _set_last_date(db, key, last)
    db.commit()
    return count


def ingest_fred_series_full(db: Session, series_id: str, fred: Fred) -> int:
    """Full ingest con tracking — scarica tutto e aggiorna IngestionState."""
    data = fred.get_series(series_id)
    logger.warning(f"received {len(data)}")
    if data.empty:
        return 0
    count = _upsert_series(db, series_id, data)
    if count > 0:
        key = f"FRED:{series_id}"
        last = max(pd.DatetimeIndex(data.index).date)
        _set_last_date(db, key, last)
    db.commit()
    return count