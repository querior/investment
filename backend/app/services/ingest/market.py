from sqlalchemy.orm import Session
from datetime import date
from typing import cast
import yfinance as yf

from app.db.meta_ingestion import IngestionState
from app.db.market_price import MarketPrice

ASSET_PROXIES = {
	"Equity": {"symbol":"SPY","source":"YAHOO"},
	"Bond": {"symbol":"IEF","source":"YAHOO"},
	"Commodities": {"symbol":"DBC","source":"YAHOO"},
	"Cash": {"symbol":"BIL","source":"YAHOO"},
}

def _get_last_date(db: Session, key: str) -> date | None:
  row = db.query(IngestionState).filter(IngestionState.key == key).one_or_none()
  return cast(date, row.last_date) if row else None

def _set_last_date(db: Session, key: str, d: date):
  row = db.query(IngestionState).filter(IngestionState.key == key).one_or_none()
  
  if row:
    row.last_date = d # type: ignore
  else:
    db.add(IngestionState(key=key, last_date=d))
    
def ingest_market_delta(db: Session, symbol: str, source: str = "YAHOO") -> int:
  key = f"MK:{symbol}"
  last_date = _get_last_date(db, key)

  ticker = yf.Ticker(symbol)
  data = ticker.history(start=last_date, auto_adjust=True)
  if data.empty:
    return 0

  count = 0
  for idx, row in data.iterrows():
    d = idx.date()
    if last_date and d <= last_date:
      continue

    db.merge(
      MarketPrice(
        symbol=symbol,
        date=d,
        open=float(row["Open"]),
        high=float(row["High"]),
        low=float(row["Low"]),
        close=float(row["Close"]),
        volume=float(row["Volume"]),
        source=source,
      )
    )
    count += 1

  if count > 0:
    _set_last_date(db, key, max(data.index.date))

  db.commit()
  return count
  
  
def ingest_all_market_delta(db: Session):
  for cfg in ASSET_PROXIES.values():
    ingest_market_delta(db, cfg["symbol"], cfg["source"])