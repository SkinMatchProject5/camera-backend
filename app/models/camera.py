from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class CameraSession(Base):
    __tablename__ = "camera_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    device_type = Column(String(50), nullable=False)  # 'web', 'mobile', 'tablet'
    status = Column(String(50), default="active")  # 'active', 'completed', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 카메라 세션과 관련된 이미지들
    images = relationship("UploadedImage", back_populates="session")

class UploadedImage(Base):
    __tablename__ = "uploaded_images"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("camera_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 파일 정보
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # 이미지 메타데이터
    width = Column(Integer)
    height = Column(Integer)
    capture_method = Column(String(50))  # 'camera', 'upload', 'auto_capture'
    
    # 처리 상태
    processing_status = Column(String(50), default="uploaded")  # 'uploaded', 'processing', 'completed', 'failed'
    
    # 타임스탬프
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # 관계
    session = relationship("CameraSession", back_populates="images")
