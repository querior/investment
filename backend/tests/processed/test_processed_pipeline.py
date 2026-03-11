from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from datetime import date
from app.services.processed.service import process_indicator


def test_macro_prosessed_is_populate(db_session,macro_raw_monthly_indpro):  
  process_indicator(db_session, "INDPRO", "INDPRO_YOY", "yoy", 3)

  rows = (
    db_session.query(MacroProcessed)
              .filter(MacroProcessed.indicator == "INDPRO_YOY")
              .all()
  )

  assert len(rows) > 0