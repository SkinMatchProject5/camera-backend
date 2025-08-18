from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.routing import APIRouter
import json
import uuid
import asyncio
from datetime import datetime
from typing import Optional

from app.websocket.manager import manager
from app.services.face_detection import get_face_detector
from app.core.security import jwt_handler
from app.config.settings import settings

router = APIRouter()

class CameraWebSocketHandler:
    def __init__(self):
        self.face_detector = get_face_detector()
        self.countdown_duration = settings.COUNTDOWN_SECONDS
    
    async def handle_connection(
        self, 
        websocket: WebSocket, 
        session_id: str,
        token: Optional[str] = None
    ):
        """WebSocket 연결 처리"""
        connection_id = str(uuid.uuid4())
        user_id = None
        
        # JWT 토큰 검증 (선택적)
        if token:
            try:
                user_info = jwt_handler.verify_token(token)
                user_id = user_info["id"]
            except Exception as e:
                await websocket.close(code=1008, reason="Invalid token")
                return
        
        # 연결 수립
        await manager.connect(websocket, connection_id, session_id, user_id)
        
        try:
            # 연결 성공 메시지
            await manager.send_personal_message({
                "type": "connected",
                "connection_id": connection_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
            # 메시지 처리 루프
            while True:
                try:
                    # 메시지 수신 (타임아웃 5초)
                    data = await asyncio.wait_for(
                        websocket.receive_text(), 
                        timeout=5.0
                    )
                    
                    # 메시지 처리
                    await self.handle_message(connection_id, session_id, data)
                    
                except asyncio.TimeoutError:
                    # 주기적 핑 전송
                    await manager.send_personal_message({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    }, connection_id)
                    
                except WebSocketDisconnect:
                    break
                    
        except Exception as e:
            print(f"WebSocket error for {connection_id}: {e}")
        finally:
            manager.disconnect(connection_id)
    
    async def handle_message(self, connection_id: str, session_id: str, raw_data: str):
        """메시지 처리"""
        try:
            data = json.loads(raw_data)
            message_type = data.get("type")
            
            if message_type == "face_detection":
                await self.handle_face_detection(connection_id, session_id, data)
            elif message_type == "start_countdown":
                await self.handle_start_countdown(connection_id, session_id, data)
            elif message_type == "stop_countdown":
                await self.handle_stop_countdown(connection_id, session_id, data)
            elif message_type == "capture_ready":
                await self.handle_capture_ready(connection_id, session_id, data)
            elif message_type == "ping":
                await self.handle_ping(connection_id)
            else:
                await self.send_error(connection_id, f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error(connection_id, "Invalid JSON format")
        except Exception as e:
            await self.send_error(connection_id, f"Message handling error: {str(e)}")
    
    async def handle_face_detection(self, connection_id: str, session_id: str, data: dict):
        """얼굴 감지 처리"""
        try:
            image_data = data.get("image")
            if not image_data:
                await self.send_error(connection_id, "No image data provided")
                return
            
            # 얼굴 감지 수행
            detection_result = self.face_detector.detect_faces_from_base64(image_data)
            
            # 안전한 값 추출 (기본값 포함)
            detected = detection_result.get("detected", False)
            confidence = detection_result.get("confidence", 0.0)
            face_count = detection_result.get("face_count", 0)
            ready_for_capture = detection_result.get("ready_for_capture", False)
            feedback = detection_result.get("feedback", "얼굴을 카메라 앞에 위치시켜 주세요")
            
            # 에러가 있는 경우 처리
            if "error" in detection_result:
                print(f"Face detection error: {detection_result['error']}")
                await self.send_error(connection_id, f"Face detection failed: {detection_result['error']}")
                return
            
            # 결과 전송
            response = {
                "type": "face_detection_result",
                "session_id": session_id,
                "detected": detected,
                "confidence": confidence,
                "face_count": face_count,
                "ready_for_capture": ready_for_capture,
                "feedback": feedback,
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.send_personal_message(response, connection_id)
            
            # 자동 촬영 준비가 되면 카운트다운 시작
            if ready_for_capture:
                await self.start_auto_countdown(connection_id, session_id)
                
        except Exception as e:
            print(f"Face detection handler error: {str(e)}")
            await self.send_error(connection_id, f"Face detection error: {str(e)}")
    
    async def handle_start_countdown(self, connection_id: str, session_id: str, data: dict):
        """수동 카운트다운 시작"""
        countdown_duration = data.get("duration", self.countdown_duration)
        await self.start_countdown(connection_id, session_id, countdown_duration)
    
    async def handle_stop_countdown(self, connection_id: str, session_id: str, data: dict):
        """카운트다운 중지"""
        await manager.send_personal_message({
            "type": "countdown_stopped",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    
    async def handle_capture_ready(self, connection_id: str, session_id: str, data: dict):
        """촬영 준비 완료"""
        await manager.send_personal_message({
            "type": "capture_command",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    
    async def handle_ping(self, connection_id: str):
        """핑 응답"""
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }, connection_id)
    
    async def start_auto_countdown(self, connection_id: str, session_id: str):
        """자동 카운트다운 시작"""
        await self.start_countdown(connection_id, session_id, self.countdown_duration, auto=True)
    
    async def start_countdown(self, connection_id: str, session_id: str, duration: int, auto: bool = False):
        """카운트다운 시작"""
        try:
            # 카운트다운 시작 알림
            await manager.send_personal_message({
                "type": "countdown_started",
                "session_id": session_id,
                "duration": duration,
                "auto": auto,
                "timestamp": datetime.now().isoformat()
            }, connection_id)
            
            # 카운트다운 실행
            for remaining in range(duration, 0, -1):
                # 연결이 여전히 활성상태인지 확인
                if connection_id not in manager.active_connections:
                    return
                
                await manager.send_personal_message({
                    "type": "countdown_tick",
                    "session_id": session_id,
                    "remaining": remaining,
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
                
                await asyncio.sleep(1)
            
            # 카운트다운 완료 - 촬영 명령
            if connection_id in manager.active_connections:
                await manager.send_personal_message({
                    "type": "capture_command",
                    "session_id": session_id,
                    "auto": auto,
                    "timestamp": datetime.now().isoformat()
                }, connection_id)
                
        except Exception as e:
            await self.send_error(connection_id, f"Countdown error: {str(e)}")
    
    async def send_error(self, connection_id: str, error_message: str):
        """에러 메시지 전송"""
        await manager.send_personal_message({
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }, connection_id)

# WebSocket 핸들러 인스턴스
camera_handler = CameraWebSocketHandler()

@router.websocket("/ws/camera/{session_id}")
async def camera_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """카메라 WebSocket 엔드포인트"""
    await camera_handler.handle_connection(websocket, session_id, token)

@router.websocket("/ws/camera")
async def camera_websocket_no_session(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """세션 없는 카메라 WebSocket (테스트용)"""
    session_id = str(uuid.uuid4())
    await camera_handler.handle_connection(websocket, session_id, token)
