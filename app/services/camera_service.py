from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.camera import CameraSession, UploadedImage
from app.api.camera.schemas import CameraSessionResponse, CameraSessionDetailResponse, UploadedImageResponse

class CameraSessionService:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_session(self, user_id: int, device_type: str) -> CameraSessionResponse:
        """새로운 카메라 세션 생성"""
        session_id = str(uuid.uuid4())
        
        db_session = CameraSession(
            user_id=user_id,
            session_id=session_id,
            device_type=device_type,
            status="active"
        )
        
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        
        return CameraSessionResponse.from_orm(db_session)
    
    async def get_session(self, session_id: str, user_id: int) -> Optional[CameraSessionDetailResponse]:
        """카메라 세션 상세 정보 조회"""
        db_session = self.db.query(CameraSession).filter(
            CameraSession.session_id == session_id,
            CameraSession.user_id == user_id
        ).first()
        
        if not db_session:
            return None
        
        # 관련 이미지들도 함께 조회
        images = self.db.query(UploadedImage).filter(
            UploadedImage.session_id == db_session.id
        ).order_by(desc(UploadedImage.uploaded_at)).all()
        
        # 응답 객체 생성
        session_response = CameraSessionDetailResponse.from_orm(db_session)
        session_response.images = [UploadedImageResponse.from_orm(img) for img in images]
        
        return session_response
    
    async def get_user_sessions(self, user_id: int, skip: int = 0, limit: int = 10) -> List[CameraSessionResponse]:
        """사용자의 카메라 세션 목록 조회"""
        sessions = self.db.query(CameraSession).filter(
            CameraSession.user_id == user_id
        ).order_by(desc(CameraSession.created_at)).offset(skip).limit(limit).all()
        
        return [CameraSessionResponse.from_orm(session) for session in sessions]
    
    async def update_session_status(self, session_id: str, user_id: int, status: str) -> Optional[CameraSessionResponse]:
        """카메라 세션 상태 업데이트"""
        db_session = self.db.query(CameraSession).filter(
            CameraSession.session_id == session_id,
            CameraSession.user_id == user_id
        ).first()
        
        if not db_session:
            return None
        
        db_session.status = status
        db_session.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_session)
        
        return CameraSessionResponse.from_orm(db_session)
    
    async def get_active_session(self, user_id: int) -> Optional[CameraSessionResponse]:
        """사용자의 활성 세션 조회"""
        active_session = self.db.query(CameraSession).filter(
            CameraSession.user_id == user_id,
            CameraSession.status == "active"
        ).order_by(desc(CameraSession.created_at)).first()
        
        if not active_session:
            return None
        
        return CameraSessionResponse.from_orm(active_session)
    
    async def close_session(self, session_id: str, user_id: int) -> bool:
        """카메라 세션 종료"""
        result = await self.update_session_status(session_id, user_id, "completed")
        return result is not None
    
    async def get_session_statistics(self, user_id: int) -> dict:
        """사용자의 세션 통계 정보"""
        total_sessions = self.db.query(CameraSession).filter(
            CameraSession.user_id == user_id
        ).count()
        
        completed_sessions = self.db.query(CameraSession).filter(
            CameraSession.user_id == user_id,
            CameraSession.status == "completed"
        ).count()
        
        total_images = self.db.query(UploadedImage).filter(
            UploadedImage.user_id == user_id
        ).count()
        
        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "active_sessions": total_sessions - completed_sessions,
            "total_images": total_images,
            "average_images_per_session": total_images / max(total_sessions, 1)
        }
