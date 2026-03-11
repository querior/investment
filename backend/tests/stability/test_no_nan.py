from app.db.macro_pillar import MacroPillar
import math

def test_no_nan_in_pillars(db_session):
    rows = db_session.query(MacroPillar).all()

    for r in rows:
        assert r.score is not None
        assert not math.isnan(r.score)