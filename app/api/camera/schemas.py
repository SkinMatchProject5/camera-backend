from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# 요청 스키마
class CameraSessionCreate(BaseModel):
    device_type: str = Field(..., description="Device type: web, mobile, tablet")
    
class CameraSessionUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Session status: active, completed, failed")

class ImageCaptureRequest(BaseModel):
    session_id: str = Field(..., description="Camera session ID")
    capture_method: str = Field(..., description="Capture method: camera, upload, auto_capture")
    device_info: Optional[dict] = Field(None, description="Device information")

# 응답 스키마
class CameraSessionResponse(BaseModel):
    id: int
    user_id: int
    session_id: str
    device_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UploadedImageResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    width: Optional[int]
    height: Optional[int]
    capture_method: str
    processing_status: str
    uploaded_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class CameraSessionDetailResponse(CameraSessionResponse):
    images: List[UploadedImageResponse] = []

# WebSocket 메시지 스키마
class FaceDetectionMessage(BaseModel):
    type: str = "face_detection"
    detected: bool
    confidence: float
    countdown: Optional[int] = None
    session_id: str

class CaptureCommandMessage(BaseModel):
    type: str = "capture"
    session_id: str
    
class ErrorMessage(BaseModel):
    type: str = "error"
    message: str
    session_id: str
