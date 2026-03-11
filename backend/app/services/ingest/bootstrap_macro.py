from fredapi import Fred
from app.services.ingest.fred import ingest_fred_series
import os
import logging

logger = logging.getLogger(__name__)

INDICATORS = [
	"CUMFNS","GDPC1","INDPRO",
	"CPIAUCSL","T5YIE",
	"FEDFUNDS","T10Y2Y",
	"VIXCLS","BAA10Y",
]

def ingest_all_macro():
  logger.info("*** ingest raw date from FRED")
  fred = Fred(api_key=os.getenv("FRED_API_KEY"))
  for ticker in INDICATORS:
    ingest_fred_series(ticker, fred)