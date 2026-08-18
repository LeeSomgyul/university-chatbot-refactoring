"""
Supabase 클라이언트 싱글톤
"""
from supabase import create_client, Client
from functools import lru_cache
from app.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """Supabase 클라이언트 반환 (싱글톤)"""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key  # 백엔드에서는 service key 사용
    )


# 전역 클라이언트
supabase = get_supabase_client()