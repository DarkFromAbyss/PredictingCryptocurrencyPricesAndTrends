import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Crypto ML Brain"

    # --- Database Config (Read from .env) ---
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # --- Logic Create Database URL ---
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        # Async URL for SQLAlchemy with asyncpg
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        # Load variables from a .env file located 4 levels up
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()