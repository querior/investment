from app.services.processed.service import process_indicator
from app.services.config_repo import get_processed_map
import logging

logger = logging.getLogger(__name__)

def process_all_indicators(db):
  processed_map = get_processed_map(db)
  logger.info("Process all indicators: %d entries", len(processed_map))
  for src, tgt, tf, resample, window, clip_limit in processed_map:
    process_indicator(db, src, tgt, tf, resample=resample, window=window, clip_limit=clip_limit)