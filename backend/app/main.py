from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
from app.core.settings import settings
from app.api.router import api_router
from app.db.init_db import init_db
from app.backtest.init_db import init_backtest_db
import logging
from app.jobs.macro_pipeline import run_macro_pipeline
from app.jobs.market_pipeline import run_market_pipeline
from app.jobs.scheduler import start_scheduler

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.warning("**** Start ingestion job ****")
    
    start_scheduler()
    
    Thread(
        target=run_macro_pipeline,
        daemon=True,
    ).start()
    
    Thread(
        target=run_market_pipeline,
        daemon=True
    ).start()

    yield
    

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    init_db()
    init_backtest_db()
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS, 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    
    
    app.include_router(api_router)
    return app

app = create_app()
