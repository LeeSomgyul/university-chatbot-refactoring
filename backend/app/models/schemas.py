# ===============================================
# API 요청/응답 (DTO 모음)
# ===============================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# [사용자가 입력한 수강 과목]
class CourseInput(BaseModel):
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

# [사용자 프로필 (세션 데이터)]
class UserProfile(BaseModel):
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

# [채팅 메시지]
class ChatMessage(BaseModel):
    role: str  # "user"(사용자) or "assistant"(챗봇)
    content: str
    timestamp: Optional[datetime] = None


# [벡터 검색 결과 응답] documents 테이블에서 벡터검색 후 질문에 맞는것 같은 데이터를 찾아온 형식
# - 설명: 해당 데이터는 정형화 되기 전의 형식으로, HandlerResponse를 만들기 위한 원본 재료이다.
class VectorSearchResult(BaseModel):
    id: int                                                 # documents 테이블의 실제 고유 id
    content: str                                            # documents 테이블의 검색된 텍스트 본문
    metadata: Dict[str, Any] = Field(default_factory=dict)  # category, title 등
    similarity: Optional[float] = None                      # supabase에서 제공하는 유사도 
    

# [키워드 검색 결과 응답] documents 테이블에서 키워드 검색 후 질문에 맞는것 같은 데이터를 찾아온 형식
class KeywordSearchResult(BaseModel):
    id: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    rank_score: Optional[float] = None  # ts_rank 점수 (사용자의 질문에 대한 content_tsv 값의 빈도수 및 포함 여부로 계산)

    
# [핸들러 응답] 각 핸들러 함수가 공통으로 반환하는 형식
class HandlerResponse(BaseModel):
    message: str                                                # 사용자에게 보여줄 최종 답변 문장
    matched_function: str                                       # 지금 실행 중인 핸들러(함수) 이름. 오류추적할때 사용 
    sources: List[Dict[str, Any]] = Field(default_factory=list) # 어떤 DB의 데이터를 참고했는지 이름 
    user_profile: Optional[UserProfile] = None                  # 각 개인의 정보 (졸업사정 등은 개인 학번, 입학년도 등이 필요함)
    needs_profile: bool = False                                 # 답변이 완료된게 아니라 사용자에게 추가적인 질문을 더 해야하는지 여부 (개인 맞춤형 질문에서 사용)
    restaurants: Optional[List[Dict[str, Any]]] = None


# [챗봇 요청] 사용자가 질문했을 때 프론트에서 들어오는 요청 형식
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_profile: Optional[UserProfile] = None
    history: List[ChatMessage] = Field(default_factory=list)


# [챗봇 응답] 백엔드에서 프론트로 전송해주는 최종 응답 형식 
class ChatResponse(BaseModel):
    message: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    matched_function: Optional[str] = None
    user_profile: Optional[UserProfile] = None
    session_id: Optional[str] = None
    restaurants: Optional[List[Dict[str, Any]]] = None
    

# [헬스 체크 응답]
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"