import pandas as pd
from sqlalchemy.orm import Session
from app.db.macro_processed import MacroProcessed
from app.db.macro_raw import MacroRaw
from app.db.processed_indicator import TransformType, ResampleMethod
from app.services.transforms.normalization import compute_z_score, clip
import logging

logger = logging.getLogger(__name__)

def process_indicator(
  db: Session,
  source_indicator: str,
  target_indicator: str,
  transform: str,
  resample: str | None = None,
  window: int = 36,
  clip_limit: float = 2.0,
  smooth_window: int = 3,
  ema_alpha: float = 0.4,
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
    [{"date": r.date, "value": r.value} for r in rows]
  )
  df["date"] = pd.to_datetime(df["date"])
  df = df.set_index("date").sort_index()

  # --- resample a frequenza mensile (se necessario) ---
  if resample == ResampleMethod.MONTHLY_MEAN:
    df = df.resample("MS").mean()

  # --- trasformazioni ---
  if transform == TransformType.YOY:
    df["value"] = df["value"].pct_change(12)*100

  if transform == TransformType.LEVEL:
    df["value"] = df["value"].diff()

  if transform == TransformType.DELTA:
    df["value"] = df["value"].diff(1)

  df = df.dropna()

  # --- smoothing pre z-score ---
  df["value_smooth"] = df["value"].rolling(smooth_window, min_periods=1).mean()

  # --- z-score + clip ---
  df["z_score"] = clip(compute_z_score(df["value_smooth"], window), limit=clip_limit)
  df = df.dropna(subset=["z_score"])

  # --- EMA sullo z-score ---
  df["z_score_ema"] = df["z_score"].ewm(alpha=ema_alpha, adjust=False).mean()

  for date, row in df.iterrows():
    db.merge(
      MacroProcessed(
        date=date,
        indicator=target_indicator,
        value=float(row["value"]),
        z_score=float(row["z_score"]),
        z_score_ema=float(row["z_score_ema"]),
      )
    )

  db.commit()
