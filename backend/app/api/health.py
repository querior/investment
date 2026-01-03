from fastapi import APIRouter
from app.core.settings import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
def health():
  return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)