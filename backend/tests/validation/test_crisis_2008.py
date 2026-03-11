from datetime import date
from app.db.macro_pillar import MacroPillar
from app.db.macro_processed import MacroProcessed
from app.services.pillars.service import compute_pillars

def test_2008_crisis_pattern(db_session, clean_db):
  # Simuliamo pattern tipico 2008
  db_session.add_all([
      # Growth molto negativo
      MacroProcessed(date=date(2008, 10, 31), indicator="CUMFNS", value=70, z_score=-2.0),
      MacroProcessed(date=date(2008, 10, 31), indicator="INDPRO_YOY", value=-12, z_score=-2.5),
      MacroProcessed(date=date(2008, 10, 31), indicator="GDPC1_YOY", value=-4, z_score=-1.8),

      # Risk molto positivo
      MacroProcessed(date=date(2008, 10, 31), indicator="BAA10Y", value=6.5, z_score=2.2),
      MacroProcessed(date=date(2008, 10, 31), indicator="VIXCLS", value=60, z_score=3.0),
      MacroProcessed(date=date(2008, 10, 31), indicator="NFCI", value=1.5, z_score=2.5),
  ])
  db_session.commit()

  compute_pillars(db_session)

  growth = db_session.query(MacroPillar).filter_by(
      date=date(2008, 10, 31), pillar="Growth"
  ).one()

  risk = db_session.query(MacroPillar).filter_by(
      date=date(2008, 10, 31), pillar="Risk"
  ).one()

  assert growth.score < 0
  assert risk.score > 0
