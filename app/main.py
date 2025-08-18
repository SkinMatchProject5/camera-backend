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
    title="Skin Story Solver - Camera Backend API",
    description="""
    ## AI 기반 피부 분석 플랫폼의 카메라 및 이미지 처리 서비스
    
    이 API는 다음과 같은 기능을 제공합니다:
    
    ### 🎥 카메라 기능
    * **카메라 세션 관리**: 사용자별 카메라 촬영 세션 생성 및 관리
    * **실시간 얼굴 인식**: MediaPipe를 사용한 실시간 얼굴 감지
    * **자동 촬영**: 얼굴이 감지되면 자동으로 카운트다운 후 촬영
    * **WebSocket 통신**: 실시간 카메라 피드백 및 제어
    
    ### 📤 이미지 업로드
    * **다중 업로드 방식**: 카메라 촬영, 파일 업로드, 자동 촬영 지원
    * **이미지 최적화**: 자동 리사이징 및 압축
    * **썸네일 생성**: 빠른 로딩을 위한 썸네일 자동 생성
    * **메타데이터 추출**: 이미지 정보 자동 분석 및 저장
    
    ### 🔐 보안
    * **JWT 인증**: Spring Boot 인증 서버와 연동
    * **파일 검증**: 안전한 이미지 파일만 업로드 허용
    * **사용자별 격리**: 개인 데이터 보호
    
    ### 📊 분석 준비
    * **AI 분석 전처리**: 얼굴 영역 감지 및 정규화
    * **품질 검사**: 블러, 밝기, 해상도 등 이미지 품질 평가
    * **배치 처리**: 대량 이미지 처리 지원
    """,
    version="1.0.0",
    contact={
        "name": "Skin Story Solver Team",
        "email": "support@skinstorysolver.com",
        "url": "https://skinstorysolver.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development Server"
        },
        {
            "url": "https://camera-api.skinstorysolver.com", 
            "description": "Production Server"
        }
    ],
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 디렉토리 생성
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# 정적 파일 서빙 (업로드된 이미지)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")

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
