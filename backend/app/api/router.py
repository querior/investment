from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.ingest import router as ingest_router
from app.api.process import router as process_router
from app.api.pillar import router as pillar_router
from app.api.job import router as job_router
from app.api.backtests import router as backtest_router
from app.core.settings import settings
from app.api.data import router as data_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix=settings.api_prefix)

api_router.include_router(data_router, prefix=settings.api_prefix)
api_router.include_router(ingest_router, prefix=settings.api_prefix)
api_router.include_router(process_router, prefix=settings.api_prefix)
api_router.include_router(pillar_router, prefix=settings.api_prefix)

api_router.include_router(job_router, prefix=settings.api_prefix)

api_router.include_router(backtest_router, prefix=settings.api_prefix)