from app.jobs.macro_pipeline import run_macro_pipeline
from app.db.macro_regimes import MacroRegime

def test_macro_pipeline_runs(db_session):
    run_macro_pipeline()
    assert db_session.query(MacroRegime).count() >= 0