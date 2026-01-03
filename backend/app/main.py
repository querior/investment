from fastapi import FastAPI
from app.core.settings import settings
from app.api.router import api_router
from app.db.init_db import init_db

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    init_db()
    app.include_router(api_router, prefix=settings.api_prefix)
    return app

app = create_app()
