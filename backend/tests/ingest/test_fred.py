from app.services.ingest.fred import ingest_fred_series
from app.db.macro_raw import MacroRaw

# def test_ingest_fred(mock_fred, db_session):
#     ingest_fred_series("TEST", mock_fred)

#     rows = db_session.query(MacroRaw).all()
#     assert len(rows) > 0
