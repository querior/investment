from pydantic_settings import BaseSettings, SettingsConfigDict
import os

ENV = os.getenv("ENV", "dev")

class Settings(BaseSettings):
    # app
    app_name: str = "investment-engine"
    api_prefix: str = "/api"
    environment: str = ENV
    
    # db
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str
    
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(
        env_file=f".env.{ENV}", 
        extra="ignore"
    )
    
settings = Settings()
