from sqlalchemy.orm import Session
from app.db.macro_processed import MacroProcessed
from app.db.macro_pillar import MacroPillar
from app.services.config_repo import get_pillars
import logging

logger = logging.getLogger(__name__)

def compute_pillars(
    db: Session,
    start_date=None,
    end_date=None,
):
  logger.info("*** compute pillars ***")
  pillars = get_pillars(db)

  q = db.query(MacroProcessed.date).distinct()
  if start_date:
    q = q.filter(MacroProcessed.date >= start_date)
  if end_date:
    q = q.filter(MacroProcessed.date <= end_date)

  dates = [d[0] for d in q.order_by(MacroProcessed.date).all()]

  for date in dates:
    for pillar, indicators in pillars.items():
      rows = (
          db.query(MacroProcessed.z_score)
	          .filter(MacroProcessed.date == date)
	          .filter(MacroProcessed.indicator.in_(indicators))
	          .all()
      )

      if len(rows) != len(indicators):
        continue # pillar incompleto → skip

      score = sum(r[0] for r in rows) /len(rows)

      db.merge(
          MacroPillar(
              date=date,
              pillar=pillar,
              score=float(score),
          )
      )

  db.commit()