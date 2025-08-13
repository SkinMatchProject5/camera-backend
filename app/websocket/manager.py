from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # 활성 연결들
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 세션별 연결 매핑
        self.session_connections: Dict[str, Set[str]] = {}
        
        # 사용자별 연결 매핑
        self.user_connections: Dict[int, Set[str]] = {}
        
        # 연결 메타데이터
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, session_id: str = None, user_id: int = None):
        """WebSocket 연결 수립"""
        await websocket.accept()
        
        # 연결 저장
        self.active_connections[connection_id] = websocket
        
        # 메타데이터 저장
        self.connection_metadata[connection_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "connected_at": datetime.now(),
            "last_activity": datetime.now()
        }
        
        # 세션별 매핑
        if session_id:
            if session_id not in self.session_connections:
                self.session_connections[session_id] = set()
            self.session_connections[session_id].add(connection_id)
        
        # 사용자별 매핑
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        print(f"WebSocket connected: {connection_id} (session: {session_id}, user: {user_id})")
    
    def disconnect(self, connection_id: str):
        """WebSocket 연결 해제"""
        if connection_id in self.active_connections:
            # 메타데이터에서 정보 가져오기
            metadata = self.connection_metadata.get(connection_id, {})
            session_id = metadata.get("session_id")
            user_id = metadata.get("user_id")
            
            # 연결 제거
            del self.active_connections[connection_id]
            
            # 메타데이터 제거
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            # 세션별 매핑에서 제거
            if session_id and session_id in self.session_connections:
                self.session_connections[session_id].discard(connection_id)
                if not self.session_connections[session_id]:
                    del self.session_connections[session_id]
            
            # 사용자별 매핑에서 제거
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            print(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """특정 연결에 메시지 전송"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
                
                # 활동 시간 업데이트
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = datetime.now()
                
            except Exception as e:
                print(f"Failed to send message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_to_session(self, message: dict, session_id: str):
        """세션의 모든 연결에 메시지 전송"""
        if session_id in self.session_connections:
            connection_ids = list(self.session_connections[session_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def send_to_user(self, message: dict, user_id: int):
        """사용자의 모든 연결에 메시지 전송"""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            for connection_id in connection_ids:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast(self, message: dict):
        """모든 연결에 메시지 브로드캐스트"""
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    def get_session_connections(self, session_id: str) -> List[str]:
        """세션의 연결 ID 목록 반환"""
        return list(self.session_connections.get(session_id, set()))
    
    def get_user_connections(self, user_id: int) -> List[str]:
        """사용자의 연결 ID 목록 반환"""
        return list(self.user_connections.get(user_id, set()))
    
    def get_connection_info(self, connection_id: str) -> dict:
        """연결 정보 반환"""
        return self.connection_metadata.get(connection_id, {})
    
    def get_stats(self) -> dict:
        """연결 통계 정보 반환"""
        return {
            "total_connections": len(self.active_connections),
            "active_sessions": len(self.session_connections),
            "connected_users": len(self.user_connections),
            "connections_by_session": {
                session_id: len(connections) 
                for session_id, connections in self.session_connections.items()
            }
        }
    
    async def cleanup_inactive_connections(self, timeout_minutes: int = 30):
        """비활성 연결 정리"""
        current_time = datetime.now()
        inactive_connections = []
        
        for connection_id, metadata in self.connection_metadata.items():
            last_activity = metadata.get("last_activity", metadata.get("connected_at"))
            if (current_time - last_activity).total_seconds() > (timeout_minutes * 60):
                inactive_connections.append(connection_id)
        
        for connection_id in inactive_connections:
            try:
                if connection_id in self.active_connections:
                    await self.active_connections[connection_id].close()
                self.disconnect(connection_id)
            except Exception as e:
                print(f"Error cleaning up connection {connection_id}: {e}")

# 전역 연결 관리자 인스턴스
manager = ConnectionManager()

# 주기적 정리 작업
async def periodic_cleanup():
    """주기적으로 비활성 연결 정리"""
    while True:
        try:
            await manager.cleanup_inactive_connections(timeout_minutes=30)
            await asyncio.sleep(300)  # 5분마다 실행
        except Exception as e:
            print(f"Cleanup error: {e}")
            await asyncio.sleep(60)  # 오류 발생 시 1분 후 재시도

# 백그라운드 태스크로 정리 작업 시작
def start_cleanup_task():
    """정리 작업 백그라운드 태스크 시작"""
    asyncio.create_task(periodic_cleanup())
