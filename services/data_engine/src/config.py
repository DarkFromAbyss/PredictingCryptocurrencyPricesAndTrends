import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- 1. Cấu hình chung ---
    PROJECT_NAME: str = "Crypto Data Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # --- 2. Cấu hình Binance ---
    # Nếu không tìm thấy trong .env, sẽ mặc định là chuỗi rỗng (cho phép tải data public)
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""

    # --- 3. Cấu hình Database (PostgreSQL) ---
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "securepassword"
    POSTGRES_DB: str = "crypto_db"
    # Mặc định là 'localhost' để chạy test bên ngoài Docker
    # Khi chạy trong Docker, ta sẽ override biến này thành 'db' (tên service trong docker-compose)
    POSTGRES_HOST: str = "localhost" 
    POSTGRES_PORT: int = 5432

    # --- 4. Logic tạo URL kết nối ---
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """
        Tạo chuỗi kết nối cho driver Async (asyncpg).
        Dùng cho SQLAlchemy phiên bản mới.
        Format: postgresql+asyncpg://user:pass@host:port/dbname
        """
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- 5. Cấu hình Pydantic ---
    model_config = SettingsConfigDict(
        # Tìm file .env ở thư mục gốc dự án (đi lên 3 cấp từ file này)
        # src -> data_engine -> services -> ROOT
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore' # Bỏ qua các biến thừa trong .env (ví dụ biến của ML Service)
    )

# Khởi tạo instance duy nhất để dùng ở các file khác
settings = Settings()

# In ra để debug (Chỉ in khi chạy local, cẩn thận lộ key)
if __name__ == "__main__":
    print(f"Loaded config for: {settings.PROJECT_NAME}")
    print(f"DB URL: {settings.DATABASE_URL_ASYNC}")