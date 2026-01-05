from fastapi import APIRouter
from app.services.transforms.macro_pipeline import process_indicator

router = APIRouter(tags=["process"])

@router.post("/process/macro")
def process_macro():
  for indicator in ["NAPM","GDPC1","INDPRO"]:
    process_indicator(indicator)

  return {"status":"processed"}