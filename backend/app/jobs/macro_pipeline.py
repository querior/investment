from app.db.session import SessionLocal
from app.services.ingest.bootstrap_macro import ingest_all_macro
from app.services.processed.orchestrator import process_all_indicators
from app.services.pillars.service import compute_pillars

def run_macro_pipeline():
  db = SessionLocal()
  try:
    ingest_all_macro()
    process_all_indicators(db)
    compute_pillars(db)
  finally:
    db.close()
    
    
