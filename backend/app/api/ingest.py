from fastapi import APIRouter
from fredapi import Fred
from app.services.ingest.fred import ingest_fred_series

router = APIRouter(tags=["ingest"])

@router.post("/ingest/macro")
def ingest_macro():
    fred = Fred()
    for ticker in ["NAPM", "GDPC1", "INDPRO"]:
        ingest_fred_series(ticker, fred)
    return {"status": "ok"}
