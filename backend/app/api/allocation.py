from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.macro_pillar import MacroPillar
from app.db.deps import get_db
from app.services.allocation.engine import compute_allocation_deltas

router = APIRouter(tags=["allocation"])

@router.get("/allocation")
def get_allocation(date: str, db: Session = Depends(get_db)):
  rows = (
    db.query(MacroPillar)
      .filter(MacroPillar.date == date)
      .all()
  )
  
  if not rows:
    return {"error": "No pillar data for date"}
  
  pillars = {r.pillar: r.score for r in rows} # type: ignore
  allocation_deltas = compute_allocation_deltas(pillars) # type: ignore
  
  return {
    "date": date,
    "pillars": pillars,
    "allocation_deltas": allocation_deltas
  }