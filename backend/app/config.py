"""
환경변수 설정 및 관리
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI
    openai_api_key: str
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    
    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "school-chatbot"
    
    # Application
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", 8000))
    
    # LLM Settings
    model_name: str = "gpt-4o-mini"
    embedding_model: str = "jhgan/ko-sroberta-multitask"
    max_tokens: int = 500
    temperature: float = 0.3
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # 강의평가
    course_review_form_url: str = "https://docs.google.com/forms/d/e/1FAIpQLSc7NdgfqFv3L8RvgrnVqNA5dcgGZOXfF3VNBJfJyy7XAkwaOg/viewform"
    google_sheet_id: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


# 전역 설정 객체
settings = get_settings()
