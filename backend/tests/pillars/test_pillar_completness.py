from app.db.macro_processed import MacroProcessed
from app.db.macro_pillar import MacroPillar
from datetime import date
from app.services.pillars.service import compute_pillars

def test_pillar_requires_all_indicators(db_session, clean_db):
  db_session.add(MacroProcessed(
    date=date(2020,1,31),
    indicator="CUMFNS",
    value=75,
    z_score=0.5,
  ))
  db_session.commit()
  
  compute_pillars(db_session)
  rows = (db_session.query(MacroPillar).all())
  
  assert len(rows) == 0