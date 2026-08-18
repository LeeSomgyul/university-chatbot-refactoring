"""
사용자 세션 관리 (인메모리)
나중에 Redis로 전환 가능
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid
from .schemas import UserProfile, ChatMessage


class SessionStore:
    """세션 저장소 (싱글톤)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.sessions = {}
        return cls._instance
    
    def create_session(self, user_profile: Optional[UserProfile] = None) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'user_profile': user_profile,
            'history': [],
            'created_at': datetime.now(),
            'last_accessed': datetime.now()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 조회"""
        if session_id in self.sessions:
            self.sessions[session_id]['last_accessed'] = datetime.now()
            return self.sessions[session_id]
        return None
    
    def update_profile(self, session_id: str, user_profile: UserProfile):
        """사용자 프로필 업데이트"""
        if session_id in self.sessions:
            self.sessions[session_id]['user_profile'] = user_profile
    
    def add_message(self, session_id: str, message: ChatMessage):
        """대화 히스토리에 메시지 추가"""
        if session_id in self.sessions:
            self.sessions[session_id]['history'].append(message)
    
    def clear_old_sessions(self, hours: int = 24):
        """오래된 세션 삭제"""
        cutoff = datetime.now() - timedelta(hours=hours)
        to_delete = [
            sid for sid, data in self.sessions.items()
            if data['last_accessed'] < cutoff
        ]
        for sid in to_delete:
            del self.sessions[sid]
        return len(to_delete)


# 전역 세션 저장소
session_store = SessionStore()