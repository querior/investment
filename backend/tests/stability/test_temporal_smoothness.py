from app.db.macro_regimes import MacroRegime

def test_pillar_temporal_smoothness(db_session):
  rows = (
      db_session.query(MacroRegime)
      .filter(MacroRegime.pillar == "Growth")
      .order_by(MacroRegime.date)
      .all()
  )

  for prev, curr in zip(rows, rows[1:]):
      assert abs(curr.score - prev.score) < 4
