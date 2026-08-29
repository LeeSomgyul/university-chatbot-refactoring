"""
사용자 세션 관리 (Redis)
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid
import json
import redis
from .schemas import UserProfile, ChatMessage
from app.config import settings
from ..utils.redis_client import get_redis_client

# 1시간 비활동 시 자동 만료 (기존 clear_old_session 대체)
SESSION_TTL_SECONDS = 3600

class SessionStore:
    """세션 저장소 (싱글톤, Redis 기반)"""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Redis Ping 추가 고려
            cls._instance.redis_client = get_redis_client()
        return cls._instance

    #=========== 내부 직렬화/역직렬화(파이썬 객체 <-> 문자열 변환)

    # (직렬화)dict -> 문자열 -> json
    def _serialize(self, data: Dict) -> str:
        payload = dict(data)  # 원본 훼손 방지
        if payload.get('user_profile') is not None:
            payload['user_profile'] = payload['user_profile'].model_dump()
        payload['created_at'] = payload['created_at'].isoformat()
        payload['last_accessed'] = payload['last_accessed'].isoformat()
        payload['history'] = [
            # 날짜 문자열 변환
            {**msg, 'timestamp': msg['timestamp'].isoformat()
            if isinstance(msg.get('timestamp'), datetime) else msg.get('timestamp')}
            for msg in payload.get('history', [])
        ]
        # 문자열 -> json직렬화
        return json.dumps(payload, ensure_ascii=False)

    # (역직렬화)문자열 파싱 -> dict 복원 -> 각 필드 타입 복원
    def _deserialize(self, raw: str) -> Dict:
        data = json.loads(raw)
        if data.get('user_profile') is not None:
            data['user_profile'] = UserProfile(**data['user_profile'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        for msg in data.get('history', []):
            if msg.get('timestamp'):
                msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
        return data

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _save(self, session_id: str, data: Dict):
        self.redis_client.setex(
            self._key(session_id), SESSION_TTL_SECONDS, self._serialize(data)
        )

    # ================기존 메서드
    def create_session(self, user_profile: Optional[UserProfile] = None) -> str:
        """새 세션 생성"""
        session_id = str(uuid.uuid4())
        data = {
            'user_profile': user_profile,
            'history': [],
            'created_at': datetime.now(),
            'last_accessed': datetime.now()
        }
        self._save(session_id, data)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """세션 조회"""
        raw = self.redis_client.get(self._key(session_id))
        if raw is None:
            return None
        data = self._deserialize(raw)
        # TTL 갱신 후 재저장
        data['last_accessed'] = datetime.now()
        self._save(session_id, data)
        return data
    
    def update_profile(self, session_id: str, user_profile: UserProfile):
        """사용자 프로필 업데이트"""
        data= self.get_session(session_id)
        if data is not None:
            data['user_profile'] = user_profile
            self._save(session_id, data)

    def update_last_restaurant_search(self, session_id: str, last_restaurant_search):
        data = self.get_session(session_id)
        if data is not None:
            data['last_restaurant_search'] = last_restaurant_search
            self._save(session_id, data)

    def add_message(self, session_id: str, message: ChatMessage):
        """대화 히스토리에 메시지 추가"""
        data = self.get_session(session_id)
        if data is not None:
            data['history'].append(message)
            self._save(session_id, data)
    
    def clear_old_sessions(self, hours: int = 24):
        """오래된 세션 삭제: TTL 자동 처리"""
        return 0


# 전역 세션 저장소
session_store = SessionStore()