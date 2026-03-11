from app.services.transforms.macro_pipeline import process_indicator
from app.db.macro_processed import MacroProcessed
from app.db.macro_raw import MacroRaw
from datetime import date


def test_process_indicator(db_session, clean_db):
  # prepara RAW
  db_session.add_all([
      MacroRaw(date=date(2020, 1, 31), indicator="TEST", value=1.0, source="TEST"),
      MacroRaw(date=date(2020, 2, 29), indicator="TEST", value=1.1, source="TEST"),
      MacroRaw(date=date(2020, 3, 31), indicator="TEST", value=1.2, source="TEST"),
      MacroRaw(date=date(2020, 4, 30), indicator="TEST", value=1.3, source="TEST"),
      MacroRaw(date=date(2020, 5, 31), indicator="TEST", value=1.4, source="TEST"),
  ])
  db_session.commit()
  assert db_session.query(MacroRaw).count() == 5
  
  process_indicator("TEST", window=3)

  rows = db_session.query(MacroProcessed).all()
  assert len(rows) > 0