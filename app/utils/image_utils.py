from PIL import Image, ExifTags
import os
import uuid
from typing import Tuple, Optional, Dict, Any
import mimetypes

def generate_unique_filename(original_filename: str) -> str:
    """유니크한 파일명 생성"""
    file_ext = os.path.splitext(original_filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    return unique_name

def get_image_info(image_path: str) -> Dict[str, Any]:
    """이미지 메타데이터 추출"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            format_name = img.format
            mode = img.mode
            
            # EXIF 데이터 추출
            exif_data = {}
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value
            
            return {
                "width": width,
                "height": height,
                "format": format_name,
                "mode": mode,
                "exif": exif_data,
                "has_transparency": mode in ("RGBA", "LA") or "transparency" in img.info
            }
    except Exception as e:
        return {
            "width": None,
            "height": None,
            "format": None,
            "mode": None,
            "exif": {},
            "has_transparency": False,
            "error": str(e)
        }

def resize_image(image_path: str, max_width: int = 1920, max_height: int = 1080, quality: int = 85) -> bool:
    """이미지 리사이징 (원본 파일 덮어쓰기)"""
    try:
        with Image.open(image_path) as img:
            # 원본 크기 확인
            original_width, original_height = img.size
            
            # 리사이징이 필요한지 확인
            if original_width <= max_width and original_height <= max_height:
                return True  # 리사이징 불필요
            
            # 비율 유지하면서 리사이징
            ratio = min(max_width / original_width, max_height / original_height)
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            
            # 이미지 리사이징
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # EXIF 정보 보존하면서 저장
            exif = img.info.get('exif')
            save_kwargs = {"quality": quality, "optimize": True}
            if exif:
                save_kwargs["exif"] = exif
            
            resized_img.save(image_path, **save_kwargs)
            return True
            
    except Exception as e:
        print(f"Image resize error: {e}")
        return False

def create_thumbnail(image_path: str, thumbnail_path: str, size: Tuple[int, int] = (300, 300)) -> bool:
    """썸네일 생성"""
    try:
        with Image.open(image_path) as img:
            # 썸네일 생성 (비율 유지)
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # RGB로 변환 (JPEG 저장을 위해)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(thumbnail_path, "JPEG", quality=80, optimize=True)
            return True
            
    except Exception as e:
        print(f"Thumbnail creation error: {e}")
        return False

def validate_image_file(file_path: str) -> bool:
    """이미지 파일 유효성 검증"""
    try:
        with Image.open(file_path) as img:
            # 이미지 로드 테스트
            img.verify()
        return True
    except Exception:
        return False

def get_mime_type(file_path: str) -> str:
    """파일의 MIME 타입 추출"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

def sanitize_filename(filename: str) -> str:
    """파일명에서 위험한 문자 제거"""
    # 위험한 문자들을 언더스코어로 대체
    import re
    safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # 파일명이 너무 길면 자르기
    name, ext = os.path.splitext(safe_filename)
    if len(name) > 100:
        name = name[:100]
    
    return f"{name}{ext}"

def rotate_image_by_exif(image_path: str) -> bool:
    """EXIF 정보에 따라 이미지 회전"""
    try:
        with Image.open(image_path) as img:
            # EXIF orientation 태그 확인
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                orientation = exif.get(274)  # Orientation 태그
                
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
                else:
                    return True  # 회전 불필요
                
                # 회전된 이미지 저장
                img.save(image_path, quality=95, optimize=True)
                return True
            
        return True
        
    except Exception as e:
        print(f"Image rotation error: {e}")
        return False
