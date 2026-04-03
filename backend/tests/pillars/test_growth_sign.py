from datetime import date
from app.db.macro_processed import MacroProcessed
from app.services.pillars.service import compute_pillars
from app.db.macro_regimes import MacroRegime


def test_growth_negative_in_recession(db_session, clean_db):
  db_session.add_all([
    MacroProcessed(date=date(2020, 3, 31), indicator="CUMFNS", value=70, z_score=-1.5, z_score_ema=-1.5),
    MacroProcessed(date=date(2020, 3, 31), indicator="INDPRO_YOY", value=-10, z_score=-2.0, z_score_ema=-2.0),
    MacroProcessed(date=date(2020, 3, 31), indicator="GDPC1_YOY", value=-5, z_score=-1.2, z_score_ema=-1.2),
  ])
  db_session.commit()
  
  compute_pillars(db_session)
  
  growth = (
    db_session.query(MacroRegime)
    .filter_by(date=date(2020, 3, 31), pillar="Growth")
    .one()
  )
  
  assert growth.score < 0