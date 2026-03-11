from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.processed.orchestrator import process_all_indicators

router = APIRouter(tags=["processed"])

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
    

@router.post("/processed")
def build_processed(db: Session = Depends(get_db)):
	process_all_indicators(db)
	return {"status":"ok"}