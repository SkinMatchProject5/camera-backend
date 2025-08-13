from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime
from typing import Optional

from app.models.camera import UploadedImage
from app.api.camera.schemas import UploadedImageResponse
from app.config.settings import settings
from app.utils.image_utils import (
    generate_unique_filename,
    get_image_info,
    resize_image,
    create_thumbnail,
    validate_image_file,
    get_mime_type,
    sanitize_filename,
    rotate_image_by_exif
)
from app.utils.device_utils import validate_file_for_device

class ImageUploadService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = settings.UPLOAD_DIR
        self.max_file_size = settings.MAX_FILE_SIZE
    
    async def process_upload(
        self, 
        file: UploadFile, 
        session_id: int, 
        user_id: int, 
        capture_method: str,
        device_type: str = "web"
    ) -> UploadedImageResponse:
        """이미지 업로드 전체 프로세스"""
        
        # 1. 파일 유효성 검증
        await self._validate_upload_file(file, device_type)
        
        # 2. 파일 저장 경로 생성
        file_path, relative_path = await self._create_file_path(user_id, file.filename)
        
        # 3. 파일 저장
        await self._save_file(file, file_path)
        
        # 4. 이미지 처리
        image_info = await self._process_image(file_path)
        
        # 5. 데이터베이스 저장
        db_image = await self._save_to_database(
            session_id=session_id,
            user_id=user_id,
            original_filename=file.filename,
            file_path=relative_path,
            file_size=image_info["file_size"],
            mime_type=image_info["mime_type"],
            width=image_info["width"],
            height=image_info["height"],
            capture_method=capture_method
        )
        
        return UploadedImageResponse.from_orm(db_image)
    
    async def _validate_upload_file(self, file: UploadFile, device_type: str):
        """업로드 파일 유효성 검증"""
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # 파일 크기 체크 (메모리에서)
        content = await file.read()
        file_size = len(content)
        
        # 파일을 처음으로 되돌리기
        await file.seek(0)
        
        # MIME 타입 체크
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )
        
        # 디바이스별 파일 크기 및 타입 검증
        if not validate_file_for_device(file_size, file.content_type, device_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large or invalid type for {device_type} device"
            )
    
    async def _create_file_path(self, user_id: int, filename: str) -> tuple[str, str]:
        """파일 저장 경로 생성"""
        # 안전한 파일명 생성
        safe_filename = sanitize_filename(filename)
        unique_filename = generate_unique_filename(safe_filename)
        
        # 사용자별 디렉토리 구조
        user_dir = os.path.join(self.upload_dir, f"user_{user_id}")
        date_dir = datetime.now().strftime("%Y/%m/%d")
        full_dir = os.path.join(user_dir, date_dir)
        
        # 디렉토리 생성
        os.makedirs(full_dir, exist_ok=True)
        
        # 전체 파일 경로
        file_path = os.path.join(full_dir, unique_filename)
        
        # DB에 저장할 상대 경로
        relative_path = os.path.join(f"user_{user_id}", date_dir, unique_filename)
        
        return file_path, relative_path
    
    async def _save_file(self, file: UploadFile, file_path: str):
        """파일을 디스크에 저장"""
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    async def _process_image(self, file_path: str) -> dict:
        """이미지 후처리"""
        try:
            # 이미지 유효성 검증
            if not validate_image_file(file_path):
                os.remove(file_path)  # 잘못된 파일 삭제
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image file"
                )
            
            # 이미지 정보 추출
            image_info = get_image_info(file_path)
            
            # EXIF 기반 이미지 회전
            rotate_image_by_exif(file_path)
            
            # 이미지 리사이징 (큰 이미지인 경우)
            resize_image(file_path, max_width=1920, max_height=1080)
            
            # 썸네일 생성
            thumbnail_dir = os.path.dirname(file_path)
            thumbnail_name = f"thumb_{os.path.basename(file_path)}"
            thumbnail_path = os.path.join(thumbnail_dir, thumbnail_name)
            create_thumbnail(file_path, thumbnail_path)
            
            # 파일 크기 재계산
            file_size = os.path.getsize(file_path)
            mime_type = get_mime_type(file_path)
            
            return {
                "width": image_info.get("width"),
                "height": image_info.get("height"),
                "file_size": file_size,
                "mime_type": mime_type,
                "format": image_info.get("format"),
                "has_thumbnail": os.path.exists(thumbnail_path)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # 오류 발생 시 파일 삭제
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image processing failed: {str(e)}"
            )
    
    async def _save_to_database(
        self, 
        session_id: int,
        user_id: int,
        original_filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        width: Optional[int],
        height: Optional[int],
        capture_method: str
    ) -> UploadedImage:
        """데이터베이스에 이미지 정보 저장"""
        try:
            db_image = UploadedImage(
                session_id=session_id,
                user_id=user_id,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                width=width,
                height=height,
                capture_method=capture_method,
                processing_status="completed"
            )
            
            self.db.add(db_image)
            self.db.commit()
            self.db.refresh(db_image)
            
            return db_image
            
        except Exception as e:
            self.db.rollback()
            # DB 저장 실패 시 파일 삭제
            full_file_path = os.path.join(self.upload_dir, file_path)
            if os.path.exists(full_file_path):
                os.remove(full_file_path)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database save failed: {str(e)}"
            )
    
    async def delete_image(self, image_id: int, user_id: int) -> bool:
        """이미지 삭제"""
        db_image = self.db.query(UploadedImage).filter(
            UploadedImage.id == image_id,
            UploadedImage.user_id == user_id
        ).first()
        
        if not db_image:
            return False
        
        try:
            # 파일 삭제
            full_file_path = os.path.join(self.upload_dir, db_image.file_path)
            if os.path.exists(full_file_path):
                os.remove(full_file_path)
            
            # 썸네일 삭제
            thumbnail_path = os.path.join(
                os.path.dirname(full_file_path),
                f"thumb_{os.path.basename(full_file_path)}"
            )
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            
            # DB에서 삭제
            self.db.delete(db_image)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Failed to delete image: {e}")
            return False
