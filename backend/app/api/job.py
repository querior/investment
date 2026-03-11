from fastapi import APIRouter
from app.jobs.macro_pipeline import run_macro_pipeline

router = APIRouter(tags=["jobs"])

@router.post("/jobs/macro")
def run_macro_job():
  run_macro_pipeline()
  return {"status": "ok"}