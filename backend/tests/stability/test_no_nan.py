from app.db.macro_regimes import MacroRegime
import math

def test_no_nan_in_pillars(db_session):
    rows = db_session.query(MacroRegime).all()

    for r in rows:
        assert r.score is not None
        assert not math.isnan(r.score)