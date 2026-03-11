from app.services.processed.config import PROCESSED_MAP
from app.services.processed.service import process_indicator
import logging

logger = logging.getLogger(__name__)

def process_all_indicators(db):
  logger.info(f"Process all indicator in {PROCESSED_MAP}")
  for src, tgt, tf in PROCESSED_MAP:
    process_indicator(db, src, tgt, tf)