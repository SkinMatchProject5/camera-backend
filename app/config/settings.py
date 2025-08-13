from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:1234@localhost:3306/skincare_db"
    
    # JWT
    JWT_SECRET: str = "defaultSecretKeyForDevelopmentOnly123456789"
    JWT_ALGORITHM: str = "HS256"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8081"
    ]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Camera Settings
    FACE_DETECTION_CONFIDENCE: float = 0.5
    COUNTDOWN_SECONDS: int = 3
    
    class Config:
        env_file = ".env"

settings = Settings()
