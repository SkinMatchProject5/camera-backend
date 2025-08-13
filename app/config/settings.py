from pydantic_settings import BaseSettings
from typing import List, Union

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:1234@localhost:3306/skincare_db"
    
    # JWT
    JWT_SECRET: str = "defaultSecretKeyForDevelopmentOnly123456789"
    JWT_ALGORITHM: str = "HS256"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB
    
    # CORS - Union으로 문자열 또는 리스트 허용
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://localhost:8081"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Camera Settings
    FACE_DETECTION_CONFIDENCE: float = 0.5
    COUNTDOWN_SECONDS: int = 3
    
    @property
    def cors_origins(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS
    
    class Config:
        env_file = ".env"

settings = Settings()
