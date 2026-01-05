import pandas as pd
from app.db.session import SessionLocal
from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from app.services.transforms.normalization import compute_z_score, clip

WINDOW =60 # 5 anni mensili

def process_indicator(indicator: str):
  db = SessionLocal()
  try:
    rows = (
      db.query(MacroRaw)
      .filter(MacroRaw.indicator == indicator)
      .order_by(MacroRaw.date)
      .all()
    )

    if not rows:
      return

    df = pd.DataFrame(
      [{"date": r.date,"value": r.value}for r in rows]
    ).set_index("date")

    z = compute_z_score(df["value"], WINDOW)
    z = clip(z)

    for date, row in df.iterrows():
      if pd.isna(z.loc[date]):
        continue

      rec = MacroProcessed(
          date=date,
          indicator=indicator,
          value=row["value"],
          z_score=float(z.loc[date]),
          source="FRED",
      )
      db.merge(rec)

    db.commit()
  finally:
    db.close()