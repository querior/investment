from app.db.macro_regimes import MacroRegime

def test_pillar_score_range(db_session):
    rows = db_session.query(MacroRegime).all()

    for r in rows:
        assert -3.5 <= r.score <= 3.5