from datetime import date
import pandas as pd
from sqlalchemy.orm import Session
from app.db.market_price import MarketPrice
from app.services.config_repo import get_asset_proxy_map


def load_asset_returns(
    db: Session,
    start: date,
    end: date,
    frequency: str = "EOM",
) -> dict[date, dict[str, float]]:
  out: dict[date, dict[str, float]] = {}
  asset_proxy_map = get_asset_proxy_map(db)

  for asset, symbol in asset_proxy_map.items():
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
    df.index = pd.to_datetime(df.index)

    if frequency == "EOM":
      # Resample to end-of-month: take last available price each month
      df = df.resample("ME").last().dropna()

    df["ret"] = df["close"].pct_change()

    for ts, r in df["ret"].dropna().items():
      d: date = pd.Timestamp(ts).date()  # type: ignore[arg-type]
      out.setdefault(d, {})[asset] = float(r)

  return out