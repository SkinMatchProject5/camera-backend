from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
from datetime import datetime

from app.config.database import get_db
from app.api.camera.schemas import (
    CameraSessionCreate, 
    CameraSessionResponse, 
    CameraSessionDetailResponse,
    UploadedImageResponse,
    ImageCaptureRequest
)
from app.services.camera_service import CameraSessionService
from app.services.upload_service import ImageUploadService
from app.core.security import get_current_user
from app.utils.device_utils import detect_device_type

router = APIRouter(tags=["Camera Sessions"])

@router.post(
    "/session", 
    response_model=CameraSessionResponse,
    summary="카메라 세션 생성",
    description="""
    새로운 카메라 촬영 세션을 생성합니다.
    
    **기능:**
    - 사용자별 고유한 세션 ID 생성
    - 디바이스 타입별 최적화 설정
    - 세션 상태 관리
    
    **디바이스 타입:**
    - `web`: 데스크톱/노트북 브라우저
    - `mobile`: 모바일 디바이스
    - `tablet`: 태블릿 디바이스
    """,
    responses={
        201: {"description": "세션 생성 성공"},
        401: {"description": "인증 실패"},
        500: {"description": "서버 오류"}
    }
)
async def create_camera_session(
    session_data: CameraSessionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 카메라 세션 생성"""
    try:
        session_service = CameraSessionService(db)
        session = await session_service.create_session(
            user_id=current_user["id"],
            device_type=session_data.device_type
        )
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create camera session: {str(e)}"
        )

@router.get(
    "/session/{session_id}", 
    response_model=CameraSessionDetailResponse,
    summary="카메라 세션 조회",
    description="""
    특정 카메라 세션의 상세 정보를 조회합니다.
    
    **포함 정보:**
    - 세션 기본 정보 (생성시간, 상태 등)
    - 촬영된 이미지 목록
    - 처리 상태 정보
    """,
    responses={
        200: {"description": "세션 조회 성공"},
        404: {"description": "세션을 찾을 수 없음"},
        401: {"description": "인증 실패 또는 권한 없음"}
    }
)
async def get_camera_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """카메라 세션 상세 정보 조회"""
    try:
        session_service = CameraSessionService(db)
        session = await session_service.get_session(session_id, current_user["id"])
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera session not found"
            )
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera session: {str(e)}"
        )

@router.post(
    "/capture", 
    response_model=UploadedImageResponse,
    summary="이미지 캡처/업로드",
    description="""
    카메라로 촬영하거나 파일을 업로드하여 이미지를 처리합니다.
    
    **지원 방식:**
    - `camera`: 웹캠을 통한 실시간 촬영
    - `upload`: 파일 선택을 통한 업로드
    - `auto_capture`: 얼굴 감지 후 자동 촬영
    
    **처리 과정:**
    1. 이미지 유효성 검사
    2. 얼굴 영역 감지 및 분석
    3. 메타데이터 추출
    4. 썸네일 생성
    5. AI 분석을 위한 전처리
    
    **지원 형식:** JPEG, PNG, WebP
    **최대 크기:** 10MB
    """,
    responses={
        200: {"description": "이미지 처리 성공"},
        400: {"description": "잘못된 파일 형식 또는 크기"},
        404: {"description": "세션을 찾을 수 없음"},
        413: {"description": "파일 크기 초과"}
    }
)
async def capture_image(
    session_id: str = Form(..., description="카메라 세션 ID"),
    capture_method: str = Form(..., description="촬영 방식: camera, upload, auto_capture"),
    device_info: Optional[str] = Form(None, description="디바이스 정보 (JSON 문자열)"),
    file: UploadFile = File(..., description="업로드할 이미지 파일"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """이미지 캡처/업로드 처리"""
    try:
        # 세션 검증
        session_service = CameraSessionService(db)
        session = await session_service.get_session(session_id, current_user["id"])
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera session not found"
            )
        
        # 이미지 업로드 처리
        upload_service = ImageUploadService(db)
        uploaded_image = await upload_service.process_upload(
            file=file,
            session_id=session.id,
            user_id=current_user["id"],
            capture_method=capture_method
        )
        
        return uploaded_image
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to capture image: {str(e)}"
        )

@router.get(
    "/sessions", 
    response_model=List[CameraSessionResponse],
    summary="사용자 세션 목록 조회",
    description="""
    현재 사용자의 모든 카메라 세션 목록을 조회합니다.
    
    **정렬:** 최신 생성순
    **페이징:** skip과 limit 파라미터로 제어
    """,
    responses={
        200: {"description": "세션 목록 조회 성공"},
        401: {"description": "인증 실패"}
    }
)
async def get_user_sessions(
    skip: int = 0,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 카메라 세션 목록 조회"""
    try:
        session_service = CameraSessionService(db)
        sessions = await session_service.get_user_sessions(
            user_id=current_user["id"],
            skip=skip,
            limit=limit
        )
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}"
        )

@router.patch(
    "/session/{session_id}/status",
    summary="세션 상태 업데이트",
    description="""
    카메라 세션의 상태를 업데이트합니다.
    
    **가능한 상태:**
    - `active`: 촬영 중
    - `completed`: 촬영 완료
    - `failed`: 오류 발생
    - `cancelled`: 사용자 취소
    """,
    responses={
        200: {"description": "상태 업데이트 성공"},
        404: {"description": "세션을 찾을 수 없음"},
        401: {"description": "권한 없음"}
    }
)
async def update_session_status(
    session_id: str,
    status: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """카메라 세션 상태 업데이트"""
    try:
        session_service = CameraSessionService(db)
        updated_session = await session_service.update_session_status(
            session_id=session_id,
            user_id=current_user["id"],
            status=status
        )
        
        if not updated_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera session not found"
            )
        
        return {"message": "Session status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session status: {str(e)}"
        )

@router.get(
    "/device-type",
    summary="디바이스 타입 감지",
    description="""
    User-Agent 헤더를 분석하여 디바이스 타입을 자동으로 감지합니다.
    
    **감지 결과:**
    - `mobile`: 스마트폰 (iOS, Android)
    - `tablet`: 태블릿 (iPad, Android 태블릿)
    - `web`: 데스크톱/노트북
    
    이 정보는 카메라 설정 최적화에 사용됩니다.
    """,
    responses={
        200: {"description": "디바이스 타입 감지 성공"}
    }
)
async def detect_device(user_agent: str = None):
    """요청 헤더를 기반으로 디바이스 타입 감지"""
    try:
        device_type = detect_device_type(user_agent)
        return {
            "device_type": device_type,
            "user_agent": user_agent,
            "recommendations": {
                "mobile": {
                    "camera_resolution": "1280x720",
                    "quality": "medium",
                    "auto_focus": True
                },
                "tablet": {
                    "camera_resolution": "1920x1080", 
                    "quality": "high",
                    "auto_focus": True
                },
                "web": {
                    "camera_resolution": "1920x1080",
                    "quality": "high", 
                    "auto_focus": False
                }
            }.get(device_type, {})
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect device type: {str(e)}"
        )
