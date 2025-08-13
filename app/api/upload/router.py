from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from pathlib import Path

from app.config.database import get_db
from app.config.settings import settings
from app.api.camera.schemas import UploadedImageResponse
from app.services.upload_service import ImageUploadService
from app.core.security import get_current_user
from app.models.camera import UploadedImage

router = APIRouter()

@router.post("/image", response_model=UploadedImageResponse)
async def upload_image(
    session_id: int = Form(...),
    capture_method: str = Form(..., description="camera, upload, auto_capture"),
    device_type: str = Form(default="web", description="web, mobile, tablet"),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """이미지 파일 업로드"""
    try:
        upload_service = ImageUploadService(db)
        
        uploaded_image = await upload_service.process_upload(
            file=file,
            session_id=session_id,
            user_id=current_user["id"],
            capture_method=capture_method,
            device_type=device_type
        )
        
        return uploaded_image
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/images", response_model=List[UploadedImageResponse])
async def get_user_images(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자의 업로드된 이미지 목록 조회"""
    try:
        query = db.query(UploadedImage).filter(
            UploadedImage.user_id == current_user["id"]
        )
        
        if session_id:
            query = query.filter(UploadedImage.session_id == session_id)
        
        images = query.order_by(UploadedImage.uploaded_at.desc()).offset(skip).limit(limit).all()
        
        return [UploadedImageResponse.from_orm(img) for img in images]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get images: {str(e)}"
        )

@router.get("/image/{image_id}")
async def get_image_file(
    image_id: int,
    thumbnail: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """이미지 파일 다운로드"""
    try:
        # 이미지 소유권 확인
        image = db.query(UploadedImage).filter(
            UploadedImage.id == image_id,
            UploadedImage.user_id == current_user["id"]
        ).first()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        
        # 파일 경로 구성
        if thumbnail:
            file_dir = os.path.dirname(os.path.join(settings.UPLOAD_DIR, image.file_path))
            filename = f"thumb_{os.path.basename(image.file_path)}"
            file_path = os.path.join(file_dir, filename)
        else:
            file_path = os.path.join(settings.UPLOAD_DIR, image.file_path)
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        return FileResponse(
            path=file_path,
            media_type=image.mime_type,
            filename=image.original_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get image file: {str(e)}"
        )

@router.delete("/image/{image_id}")
async def delete_image(
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """이미지 삭제"""
    try:
        upload_service = ImageUploadService(db)
        
        success = await upload_service.delete_image(image_id, current_user["id"])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        
        return {"message": "Image deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )
