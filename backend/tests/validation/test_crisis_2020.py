from datetime import date
from app.db.macro_pillar import MacroPillar
from app.db.macro_processed import MacroProcessed
from app.services.pillars.service import compute_pillars

def test_2020_covid_shock(db_session, clean_db):
    db_session.add_all([
        # Growth collassa
        MacroProcessed(date=date(2020, 3, 31), indicator="CUMFNS", value=68, z_score=-2.2),
        MacroProcessed(date=date(2020, 3, 31), indicator="INDPRO_YOY", value=-15, z_score=-3.0),
        MacroProcessed(date=date(2020, 3, 31), indicator="GDPC1_YOY", value=-5, z_score=-1.5),

        # Risk esplode
        MacroProcessed(date=date(2020, 3, 31), indicator="BAA10Y", value=7.0, z_score=2.5),
        MacroProcessed(date=date(2020, 3, 31), indicator="VIXCLS", value=80, z_score=3.2),
        MacroProcessed(date=date(2020, 3, 31), indicator="NFCI", value=1.8, z_score=2.8),

        # Policy ultra espansiva
        MacroProcessed(date=date(2020, 3, 31), indicator="FEDFUNDS", value=0.25, z_score=-2.0),
        MacroProcessed(date=date(2020, 3, 31), indicator="T10Y2Y", value=0.2, z_score=-1.2),
        MacroProcessed(date=date(2020, 3, 31), indicator="FEDFUNDS_DELTA", value=-1.5, z_score=-3.0),
    ])
    db_session.commit()

    compute_pillars(db_session)

    policy = db_session.query(MacroPillar).filter_by(
        date=date(2020, 3, 31), pillar="Policy"
    ).one()

    assert policy.score < 0
