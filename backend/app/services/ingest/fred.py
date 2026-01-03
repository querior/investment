from fredapi import Fred
from app.db.session import SessionLocal
from app.db.models import MacroRaw
from datetime import date

def ingest_fred_series(series_id: str, fred: Fred):
    data = fred.get_series(series_id)

    db = SessionLocal()
    try:
        for idx, value in data.items():
            if value is None:
                continue

            row = MacroRaw(
                date=idx.date() if hasattr(idx, "date") else idx,
                indicator=series_id,
                value=float(value),
                source="FRED",
            )
            db.merge(row)  # UPSERT
        db.commit()
    finally:
        db.close()