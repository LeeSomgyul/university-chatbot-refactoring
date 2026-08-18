"""
API 요청/응답 스키마 정의 - 개선 버전
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CourseInput(BaseModel):
    """사용자가 입력한 수강 과목"""
    course_code: Optional[str] = None
    course_name: str
    credit: int
    grade: Optional[str] = None  # A+, A0, B+, etc.
    course_area: str  # "전공" or "교양"
    requirement_type: Optional[str] = None  # "전공필수", "전공선택", "공통교양"
    
    # 교양 과목의 경우 track 정보 (선택)
    liberal_arts_track: Optional[str] = None  # "기초", "핵심-인문학" 등
    
    class Config:
        # 예시
        schema_extra = {
            "example": {
                "course_code": "CS0614",
                "course_name": "컴퓨터과학",
                "credit": 3,
                "grade": "A+",
                "course_area": "전공",
                "requirement_type": "전공필수"
            }
        }


class UserProfile(BaseModel):
    """사용자 프로필 (세션 데이터)"""
    admission_year: int  # 학번 (예: 2024)
    current_semester: Optional[int] = None  # 현재 학기 (1~8)
    courses_taken: List[CourseInput] = Field(default_factory=list)
    track: str = "일반"  # 일반, AI트랙 등 (현재 사용 안 함)
    
    class Config:
        schema_extra = {
            "example": {
                "admission_year": 2024,
                "current_semester": 3,
                "courses_taken": [
                    {
                        "course_code": "CS0614",
                        "course_name": "컴퓨터과학",
                        "credit": 3,
                        "grade": "A+",
                        "course_area": "전공",
                        "requirement_type": "전공필수"
                    }
                ],
                "track": "일반"
            }
        }


class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """챗봇 요청"""
    message: str
    session_id: Optional[str] = None
    user_profile: Optional[UserProfile] = None
    history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """챗봇 응답"""
    message: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    query_type: Optional[str] = None  # "curriculum", "general", "hybrid"
    session_id: Optional[str] = None


class HealthCheck(BaseModel):
    """헬스체크 응답"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"