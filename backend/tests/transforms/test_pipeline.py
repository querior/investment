from app.services.transforms.macro_pipeline import process_indicator
from app.db.macro_processed import MacroProcessed

# def test_process_indicator(db_session):
#   process_indicator("TEST")

#   rows = db_session.query(MacroProcessed).all()
#   assert len(rows) > 0