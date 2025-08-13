import re
from typing import Dict, Any

def detect_device_type(user_agent: str = None) -> str:
    """User-Agent 문자열을 기반으로 디바이스 타입 감지"""
    if not user_agent:
        return "unknown"
    
    user_agent = user_agent.lower()
    
    # 모바일 디바이스 패턴
    mobile_patterns = [
        r'android.*mobile',
        r'iphone',
        r'ipod',
        r'blackberry',
        r'opera.*mini',
        r'iemobile',
        r'mobile'
    ]
    
    # 태블릿 디바이스 패턴
    tablet_patterns = [
        r'ipad',
        r'android(?!.*mobile)',
        r'tablet',
        r'kindle',
        r'playbook',
        r'nook'
    ]
    
    # 태블릿 체크 (모바일보다 먼저 체크)
    for pattern in tablet_patterns:
        if re.search(pattern, user_agent):
            return "tablet"
    
    # 모바일 체크
    for pattern in mobile_patterns:
        if re.search(pattern, user_agent):
            return "mobile"
    
    # 기본값은 웹(데스크톱)
    return "web"

def get_device_capabilities(device_type: str) -> Dict[str, Any]:
    """디바이스 타입별 기능 설정"""
    capabilities = {
        "web": {
            "face_detection": True,
            "auto_capture": True,
            "countdown": True,
            "camera_selection": True,
            "file_upload": True,
            "drag_drop": True,
            "keyboard_shortcuts": True,
            "real_time_preview": True
        },
        "mobile": {
            "face_detection": False,
            "auto_capture": False,
            "countdown": False,
            "camera_selection": True,
            "file_upload": True,
            "drag_drop": False,
            "keyboard_shortcuts": False,
            "real_time_preview": False,
            "native_camera": True,
            "touch_gestures": True
        },
        "tablet": {
            "face_detection": False,
            "auto_capture": False,
            "countdown": False,
            "camera_selection": True,
            "file_upload": True,
            "drag_drop": True,
            "keyboard_shortcuts": False,
            "real_time_preview": False,
            "native_camera": True,
            "touch_gestures": True
        }
    }
    
    return capabilities.get(device_type, capabilities["web"])

def validate_file_for_device(file_size: int, file_type: str, device_type: str) -> bool:
    """디바이스별 파일 업로드 제한 검증"""
    max_sizes = {
        "web": 10 * 1024 * 1024,      # 10MB
        "mobile": 5 * 1024 * 1024,    # 5MB
        "tablet": 8 * 1024 * 1024     # 8MB
    }
    
    allowed_types = [
        "image/jpeg",
        "image/jpg", 
        "image/png",
        "image/webp"
    ]
    
    max_size = max_sizes.get(device_type, max_sizes["web"])
    
    return (
        file_size <= max_size and 
        file_type.lower() in allowed_types
    )
