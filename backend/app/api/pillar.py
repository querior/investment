from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.pillars.service import compute_pillars
from app.db.macro_pillar import MacroPillar

router = APIRouter(tags=["pillar"])

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

@router.get("/pillars")
def get_pillars(
  start: date | None = None,
  end: date | None = None,
  db: Session = Depends(get_db)
):
  # calcolo lazy (idempotente)
  compute_pillars(db, start, end)
  
  q = db.query(MacroPillar)
  if start:
    q = q.filter(MacroPillar.date >= start)
    
  if end:
    q = q.filter(MacroPillar.date <= end)
    
  rows = q.order_by(MacroPillar.date, MacroPillar.pillar).all()
  
  return [
    {
      "date": r.date,
      "pillar": r.pillar,
      "score": r.score
    }
    for r in rows
  ]