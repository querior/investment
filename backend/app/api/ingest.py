from fastapi import APIRouter
from app.services.ingest.bootstrap_macro import ingest_all_macro

router = APIRouter(tags=["ingest"])

@router.post("/ingest/macro")
def ingest_macro_all():
    ingest_all_macro()