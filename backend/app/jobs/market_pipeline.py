from app.db.session import SessionLocal
from app.services.ingest.market import ingest_all_market_delta

def run_market_pipeline():
  db = SessionLocal()
  try:
    ingest_all_market_delta(db)
  finally:
    db.close()