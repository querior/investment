import logging
import time
from app.db.session import SessionLocal
from app.services.ingest.bootstrap_macro import ingest_all_macro
from app.services.processed.orchestrator import process_all_indicators
from app.services.pillars.service import compute_pillars

logger = logging.getLogger(__name__)

def run_macro_pipeline():
  time.sleep(3)  # attende che il server sia completamente avviato
  db = SessionLocal()
  try:
    ingest_all_macro()
    process_all_indicators(db)
    compute_pillars(db)
  except Exception as e:
    logger.error("macro pipeline error: %s", e)
  finally:
    db.close()
    
    
