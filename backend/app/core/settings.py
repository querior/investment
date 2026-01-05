from pydantic_settings import BaseSettings, SettingsConfigDict
import os

ENV = os.getenv("ENVIRONMENT", "dev")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    
    environment: str
    
    # app
    app_name: str
    
    api_prefix: str
    
    database_url: str

    fred_api_key: str
    
settings = Settings()
