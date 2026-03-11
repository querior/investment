from app.db.macro_pillar import MacroPillar

def test_pillar_temporal_smoothness(db_session):
  rows = (
      db_session.query(MacroPillar)
      .filter(MacroPillar.pillar == "Growth")
      .order_by(MacroPillar.date)
      .all()
  )

  for prev, curr in zip(rows, rows[1:]):
      assert abs(curr.score - prev.score) < 4
