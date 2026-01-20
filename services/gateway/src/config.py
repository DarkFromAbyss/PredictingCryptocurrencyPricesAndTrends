import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Crypto API Gateway"
    
    # Địa chỉ của các Microservices
    # Lưu ý: Khi chạy trong Docker, ta dùng tên service (container name) làm host
    # Khi chạy Local (ngoài Docker), ta dùng localhost:8001, localhost:8002
    
    # Mặc định cấu hình cho môi trường DOCKER
    DATA_ENGINE_URL: str = "http://data_engine:8000"
    ML_BRAIN_URL: str = "http://ml_brain:8000"

    # API Prefix
    API_V1_PREFIX: str = "/api/v1"

settings = Settings()