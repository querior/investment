from datetime import date
import pandas as pd
from sqlalchemy.orm import Session
from typing import cast
from app.db.macro_raw import MacroRaw
from app.db.market_price import MarketPrice
from app.services.ingest.market import ASSET_PROXIES

ASSET_SERIES = {
    "Equity": "SP500_REAL_RETURN",
    "Bond": "BAMLCC0A0CMTRIV",
    "Commodities": "PALLFNFINDEXQ",
    "Cash": "DTB3",
}

def load_asset_returns(
    db: Session,
    start: date,
    end: date,
) -> dict[date, dict[str, float]]:
  out: dict[date, dict[str, float]] = {}

  for asset, cfg in ASSET_PROXIES.items():
    symbol = cfg["symbol"]
    
    rows = (
      db.query(MarketPrice)
        .filter(MarketPrice.symbol == symbol)
        .filter(MarketPrice.date >= start)
        .filter(MarketPrice.date <= end)
        .order_by(MarketPrice.date)
        .all()
    )

    if not rows:
      continue

    df = (
      pd.DataFrame(
          [{"date": r.date, "close": r.close} for r in rows]
      )
      .set_index("date")
      .sort_index()
    )

    df["ret"] = df["close"].pct_change()
    
    for d, r in df["ret"].dropna().items():
      d = cast(date,d)
      out.setdefault(d, {})[asset] = float(r)

  return out