from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os
import json

ENV = os.getenv("ENVIRONMENT", "development")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    environment: str = Field(...)
    
    # app
    app_name: str = Field(...)
    
    api_prefix: str = Field(...)
    
    database_url: str = Field(...)

    fred_api_key: str = Field(...)
    
    # auth
    JWT_SECRET: str = Field(...)
    JWT_ISSUER: str = "querior-investment"
    JWT_AUDIENCE: str = "querior-investment-users"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000"
    ]
    
settings = Settings() # type: ignore
