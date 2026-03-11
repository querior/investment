from app.db.macro_pillar import MacroPillar

def test_pillar_score_range(db_session):
    rows = db_session.query(MacroPillar).all()

    for r in rows:
        assert -3.5 <= r.score <= 3.5