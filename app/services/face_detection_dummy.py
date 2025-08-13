# 임시 더미 얼굴 인식 서비스 (의존성 문제 해결 전까지)
from typing import Dict

class FaceDetectionService:
    def __init__(self):
        self.countdown_timer = 3
    
    def detect_faces_from_base64(self, image_data: str) -> Dict:
        """더미 얼굴 감지 (항상 감지됨으로 반환)"""
        return {
            "detected": True,
            "confidence": 0.8,
            "face_count": 1,
            "faces": [{
                "confidence": 0.8,
                "bbox": {"x": 100, "y": 100, "width": 200, "height": 200},
                "quality": {"overall_score": 0.8, "is_good_quality": True}
            }],
            "ready_for_capture": True,
            "feedback": "얼굴이 감지되었습니다 (더미 모드)"
        }

def get_face_detector() -> FaceDetectionService:
    return FaceDetectionService()
