import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Tuple, Optional
import base64
from io import BytesIO
from PIL import Image

from app.config.settings import settings

class FaceDetectionService:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0: 2m 이내, 1: 5m 이내
            min_detection_confidence=settings.FACE_DETECTION_CONFIDENCE
        )
        self.countdown_timer = settings.COUNTDOWN_SECONDS
    
    def detect_faces_from_base64(self, image_data: str) -> Dict:
        """Base64 이미지에서 얼굴 감지"""
        try:
            # Base64 디코딩
            image_bytes = base64.b64decode(image_data.split(',')[1] if ',' in image_data else image_data)
            image = Image.open(BytesIO(image_bytes))
            
            # OpenCV 형식으로 변환
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            return self.detect_faces(opencv_image)
            
        except Exception as e:
            return {
                "detected": False,
                "confidence": 0.0,
                "face_count": 0,
                "faces": [],
                "error": str(e)
            }
    
    def detect_faces(self, image: np.ndarray) -> Dict:
        """OpenCV 이미지에서 얼굴 감지"""
        try:
            # RGB로 변환 (MediaPipe는 RGB 사용)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 얼굴 감지 수행
            results = self.face_detection.process(rgb_image)
            
            detected_faces = []
            max_confidence = 0.0
            
            if results.detections:
                for detection in results.detections:
                    # 신뢰도 점수
                    confidence = detection.score[0]
                    max_confidence = max(max_confidence, confidence)
                    
                    # 경계 상자 좌표
                    bbox = detection.location_data.relative_bounding_box
                    
                    # 이미지 크기 기준으로 절대 좌표 계산
                    h, w, _ = image.shape
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    # 얼굴 크기 및 위치 품질 평가
                    face_quality = self._evaluate_face_quality(
                        bbox, confidence, w, h
                    )
                    
                    detected_faces.append({
                        "confidence": confidence,
                        "bbox": {
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "x_rel": bbox.xmin,
                            "y_rel": bbox.ymin,
                            "width_rel": bbox.width,
                            "height_rel": bbox.height
                        },
                        "quality": face_quality
                    })
            
            # 얼굴 감지 결과 정리
            face_detected = len(detected_faces) > 0 and max_confidence >= settings.FACE_DETECTION_CONFIDENCE
            
            return {
                "detected": face_detected,
                "confidence": max_confidence,
                "face_count": len(detected_faces),
                "faces": detected_faces,
                "ready_for_capture": self._is_ready_for_capture(detected_faces),
                "feedback": self._get_user_feedback(detected_faces)
            }
            
        except Exception as e:
            return {
                "detected": False,
                "confidence": 0.0,
                "face_count": 0,
                "faces": [],
                "ready_for_capture": False,
                "feedback": "얼굴 감지 중 오류가 발생했습니다",
                "error": str(e)
            }
    
    def _evaluate_face_quality(self, bbox, confidence: float, image_width: int, image_height: int) -> Dict:
        """얼굴 품질 평가"""
        # 얼굴 크기 평가 (이미지 대비)
        face_area = bbox.width * bbox.height
        size_score = min(face_area * 10, 1.0)  # 10%가 최적
        
        # 중앙 위치 평가
        center_x = bbox.xmin + bbox.width / 2
        center_y = bbox.ymin + bbox.height / 2
        
        # 중앙에서의 거리 (0.5, 0.5가 중앙)
        center_distance = ((center_x - 0.5) ** 2 + (center_y - 0.5) ** 2) ** 0.5
        position_score = max(0, 1 - center_distance * 2)
        
        # 전체 품질 점수
        quality_score = (confidence * 0.4 + size_score * 0.3 + position_score * 0.3)
        
        return {
            "overall_score": quality_score,
            "confidence_score": confidence,
            "size_score": size_score,
            "position_score": position_score,
            "is_good_quality": quality_score >= 0.7
        }
    
    def _is_ready_for_capture(self, faces: List[Dict]) -> bool:
        """자동 촬영 준비 상태 확인"""
        if not faces:
            return False
        
        # 가장 좋은 품질의 얼굴 확인
        best_face = max(faces, key=lambda f: f["quality"]["overall_score"])
        
        return (
            len(faces) == 1 and  # 얼굴이 하나만 감지됨
            best_face["confidence"] >= 0.7 and  # 높은 신뢰도
            best_face["quality"]["is_good_quality"]  # 좋은 품질
        )
    
    def _get_user_feedback(self, faces: List[Dict]) -> str:
        """사용자 피드백 메시지 생성"""
        if not faces:
            return "얼굴을 카메라 앞에 위치시켜 주세요"
        
        if len(faces) > 1:
            return "한 명만 촬영해 주세요"
        
        face = faces[0]
        quality = face["quality"]
        
        if quality["confidence_score"] < 0.5:
            return "조명을 확인하고 얼굴을 더 명확하게 보여주세요"
        
        if quality["size_score"] < 0.3:
            return "카메라에 더 가까이 오세요"
        elif quality["size_score"] > 0.8:
            return "카메라에서 조금 멀어져 주세요"
        
        if quality["position_score"] < 0.5:
            return "얼굴을 화면 중앙에 위치시켜 주세요"
        
        if quality["is_good_quality"]:
            return "좋습니다! 잠시 후 자동으로 촬영됩니다"
        
        return "자세를 조정해 주세요"
    
    def draw_face_landmarks(self, image: np.ndarray, faces: List[Dict]) -> np.ndarray:
        """얼굴에 랜드마크 그리기 (디버깅용)"""
        annotated_image = image.copy()
        
        for face in faces:
            bbox = face["bbox"]
            confidence = face["confidence"]
            
            # 경계 상자 그리기
            color = (0, 255, 0) if face["quality"]["is_good_quality"] else (0, 255, 255)
            cv2.rectangle(
                annotated_image,
                (bbox["x"], bbox["y"]),
                (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
                color, 2
            )
            
            # 신뢰도 텍스트
            cv2.putText(
                annotated_image,
                f'{confidence:.2f}',
                (bbox["x"], bbox["y"] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, color, 1
            )
        
        return annotated_image
    
    def __del__(self):
        """리소스 정리"""
        if hasattr(self, 'face_detection'):
            self.face_detection.close()

# 전역 인스턴스 (메모리 효율성을 위해)
face_detector = None

def get_face_detector() -> FaceDetectionService:
    """얼굴 감지 서비스 인스턴스 반환"""
    global face_detector
    if face_detector is None:
        face_detector = FaceDetectionService()
    return face_detector
