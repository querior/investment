import pandas as pd
from sqlalchemy.orm import Session
from app.db.macro_processed import MacroProcessed
from app.db.macro_raw import MacroRaw
from app.services.transforms.normalization import compute_z_score, clip
import logging

logger = logging.getLogger(__name__)

WINDOW = 60 # mesi

def process_indicator(
  db: Session,
  source_indicator: str,
  target_indicator: str,
  transform: str,
  window: int = WINDOW
):
  rows = (
    db.query(MacroRaw)
      .filter(MacroRaw.indicator == source_indicator)
      .order_by(MacroRaw.date)
      .all()
  )
  if not rows:
    return
  
  df = pd.DataFrame(
    [{ "date": r.date, "value": r.value } for r in rows]
  ).set_index("date").sort_index()
  
  # --- trasformazioni ---
  if transform == "yoy":
    df["value"] = df["value"].pct_change(12)*100
    
  if transform == "level":
    df["value"] = df["value"].diff()
    
  df = df.dropna()

  # --- z-score ---
  df["z_score"] = clip(compute_z_score(df["value"], window))
  df = df.dropna(subset=["z_score"])

  for date, row in df.iterrows():
    db.merge(
      MacroProcessed(
        date=date,
        indicator=target_indicator,
        value=float(row["value"]),
        z_score=float(row["z_score"])
      )
    )

  db.commit()