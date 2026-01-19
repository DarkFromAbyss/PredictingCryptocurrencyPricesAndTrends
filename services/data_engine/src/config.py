import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- General Configuration---
    PROJECT_NAME: str = "Crypto Data Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # --- Binance Configuration ---
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""

    # --- 3. Database Configuration (PostgreSQL) ---
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "securepassword"
    POSTGRES_DB: str = "crypto_db"
    # The default is 'localhost' to run tests outside of Docker.
    # When running within Docker, we will override this variable to 'db' (the service name in docker-compose).
    POSTGRES_HOST: str = "localhost" 
    POSTGRES_PORT: int = 5432

    # --- 4. Logic create URL connect ---
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """
        Create a connection string for the Async driver (asyncpg).
        Use with the latest version of SQLAlchemy.
        Format: postgresql+asyncpg://user:pass@host:port/dbname
        """
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- 5. Pydantic Configuration ---
    model_config = SettingsConfigDict(
        # Find the .env file in the project root directory (go up 3 levels from this file)
        # src -> data_engine -> services -> ROOT
        env_file=os.path.join(
                    os.path.dirname(
                        os.path.dirname(
                            os.path.dirname(
                                os.path.dirname(__file__)
                            )
                        )
                    ), ".env"),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore' #Ignore redundant variables in .env (e.g., ML Service variables)
    )

# Create a unique instance for use in other files.
settings = Settings()

# Debug: Print loaded settings (remove or comment out in production)
if __name__ == "__main__":
    print(f"Loaded config for: {settings.PROJECT_NAME}")
    print(f"DB URL: {settings.DATABASE_URL_ASYNC}")