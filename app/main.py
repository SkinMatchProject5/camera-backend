from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

from app.config.settings import settings
from app.config.database import engine, Base
from app.api.camera.router import router as camera_router
from app.api.upload.router import router as upload_router
from app.websocket.camera_ws import router as websocket_router
from app.websocket.manager import start_cleanup_task

# 환경 변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(
    title="Skincare Camera Backend",
    description="Camera and Image Processing API for Skincare Application",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 디렉토리 생성
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# 정적 파일 서빙 (업로드된 이미지)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 데이터베이스 테이블 생성
@app.on_event("startup")
async def create_tables():
    Base.metadata.create_all(bind=engine)
    # WebSocket 연결 정리 백그라운드 태스크 시작
    start_cleanup_task()

# 라우터 등록
app.include_router(camera_router, prefix="/api/camera", tags=["camera"])
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(websocket_router, tags=["websocket"])

@app.get("/")
async def root():
    return {"message": "Skincare Camera Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "camera-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
