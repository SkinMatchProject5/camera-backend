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

router = APIRouter()

# 카메라 세션 생성
@router.post("/session", response_model=CameraSessionResponse)
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

# 카메라 세션 조회
@router.get("/session/{session_id}", response_model=CameraSessionDetailResponse)
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

# 이미지 업로드 (카메라 촬영 or 파일 업로드)
@router.post("/capture", response_model=UploadedImageResponse)
async def capture_image(
    session_id: str = Form(...),
    capture_method: str = Form(...),
    device_info: Optional[str] = Form(None),
    file: UploadFile = File(...),
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

# 사용자의 모든 세션 조회
@router.get("/sessions", response_model=List[CameraSessionResponse])
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

# 세션 상태 업데이트
@router.patch("/session/{session_id}/status")
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

# 디바이스 타입 자동 감지
@router.get("/device-type")
async def detect_device(user_agent: str = None):
    """요청 헤더를 기반으로 디바이스 타입 감지"""
    try:
        device_type = detect_device_type(user_agent)
        return {
            "device_type": device_type,
            "user_agent": user_agent
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect device type: {str(e)}"
        )
