from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.db.session import SessionLocal
from app.db.macro_regimes import MacroRegime

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
    q = db.query(MacroRegime)
    if start:
        q = q.filter(MacroRegime.date >= start)
    if end:
        q = q.filter(MacroRegime.date <= end)

    rows = q.order_by(MacroRegime.date, MacroRegime.pillar).all()

    return [
        {
            "date": r.date,
            "pillar": r.pillar,
            "score": r.score,
            "score_ema": r.score_ema,
            "regime": r.regime,
            "counter": r.counter,
            "pending": r.pending,
        }
        for r in rows
    ]
