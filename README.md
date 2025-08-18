# 🎥 Skin Story Solver - Camera Backend API

AI 기반 피부 분석 플랫폼의 카메라 및 이미지 처리 서비스입니다.

## ✨ 주요 기능

### 🎥 카메라 기능
- **실시간 얼굴 인식**: MediaPipe를 사용한 고정밀 얼굴 감지
- **자동 촬영**: 얼굴 감지 시 자동 카운트다운 후 촬영
- **플랫폼별 최적화**: 웹(전면 카메라), 모바일(후면 카메라) 지원
- **WebSocket 통신**: 실시간 피드백 및 제어

### 📤 이미지 업로드
- **다중 업로드 방식**: 카메라 촬영, 파일 업로드, 자동 촬영
- **이미지 최적화**: 자동 리사이징 및 압축
- **썸네일 생성**: 빠른 로딩을 위한 썸네일 자동 생성
- **메타데이터 추출**: 이미지 정보 자동 분석

### 🔐 보안 및 인증
- **JWT 인증**: Spring Boot 인증 서버와 연동
- **사용자별 격리**: 개인 데이터 보호
- **파일 검증**: 안전한 이미지 파일만 업로드 허용

## 🛠 기술 스택

- **Framework**: FastAPI 0.104+
- **WebSocket**: uvicorn[standard] + websockets
- **Database**: MySQL + SQLAlchemy
- **Image Processing**: OpenCV 4.8+, MediaPipe 0.10+, Pillow 10.1+
- **Authentication**: python-jose + passlib
- **Other**: pydantic, python-dotenv

## 🚀 설치 및 실행

### 1. 환경 준비
```bash
# Python 3.8+ 필요
python --version

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 추가합니다:

```env
# Database
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/skincare_db

# JWT
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Camera
FACE_DETECTION_CONFIDENCE=0.5
COUNTDOWN_SECONDS=3

# Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB
```

### 4. 서버 실행
```bash
# 개발 서버 실행
python run.py

# 또는 직접 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🌐 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 📊 주요 엔드포인트

#### 카메라 세션 관리
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/camera/session` | 새 카메라 세션 생성 |
| GET | `/api/camera/session/{session_id}` | 세션 상세 조회 |
| GET | `/api/camera/sessions` | 사용자 세션 목록 |
| PATCH | `/api/camera/session/{session_id}/status` | 세션 상태 업데이트 |

#### 이미지 처리
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/camera/capture` | 이미지 캡처/업로드 |
| POST | `/api/upload/image` | 파일 업로드 |
| GET | `/uploads/{filename}` | 업로드된 이미지 조회 |

#### 유틸리티
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/camera/device-type` | 디바이스 타입 감지 |
| GET | `/health` | 서버 상태 확인 |
| GET | `/` | API 정보 |

## 📡 WebSocket API

### 연결
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/camera/{session_id}?token={jwt_token}');
```

### 메시지 타입

#### 클라이언트 → 서버
```json
{
  "type": "face_detection",
  "image": "data:image/jpeg;base64,..."
}

{
  "type": "start_countdown",
  "duration": 3
}

{
  "type": "ping"
}
```

#### 서버 → 클라이언트
```json
{
  "type": "face_detection_result",
  "detected": true,
  "confidence": 0.95,
  "face_count": 1,
  "ready_for_capture": true,
  "feedback": "좋습니다! 잠시 후 자동으로 촬영됩니다"
}

{
  "type": "countdown_started",
  "duration": 3,
  "auto": true
}

{
  "type": "capture_command",
  "auto": true
}
```

## 🐛 문제 해결

### 카메라가 보이지 않는 경우

1. **브라우저 콘솔 확인**: F12 → Console 탭에서 에러 메시지 확인
2. **카메라 권한 확인**: 브라우저 주소창 옆 카메라 아이콘 클릭 → 허용
3. **HTTPS 사용**: 일부 브라우저에서는 HTTPS가 필요할 수 있습니다
4. **다른 프로그램**: 다른 애플리케이션에서 카메라를 사용 중인지 확인

### WebSocket 연결 실패

1. **서버 상태 확인**: `curl http://localhost:8000/health`
2. **CORS 설정**: `.env` 파일의 `ALLOWED_ORIGINS` 확인
3. **방화벽**: 8000번 포트가 열려있는지 확인

## 📞 지원

- **API 문서**: http://localhost:8000/docs
- **이메일**: support@skinstorysolver.com

## 📄 라이선스

MIT License
