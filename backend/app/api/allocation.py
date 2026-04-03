from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.db.macro_regimes import MacroRegime
from app.services.allocation.engine import compute_target_allocation

router = APIRouter(tags=["allocation"])

@router.get("/allocation")
def get_allocation(date: str, db: Session = Depends(get_db)):
    rows = (
        db.query(MacroRegime)
        .filter(MacroRegime.date == date)
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"Nessun dato di regime per {date}")

    regimes = {r.pillar: r.regime for r in rows}
    target = compute_target_allocation(db, regimes)

    return {
        "date": date,
        "regimes": regimes,
        "target_allocation": target,
    }
