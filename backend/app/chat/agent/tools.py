# ===============================================
#  [복합 질문-2단계] 기존 핸들러 함수들을, LLM이 직접 실행할 수 있도록 형태 변환 
# ===============================================

from typing import List, Annotated, Optional
from app.chat.agent.state import AgentState
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import InjectedState
from app.chat.handlers import (
    CheckGraduationStatus_handler,
    GetCurriculum_handler,
    GetEquivalentCourse_handler,
    SearchReviews_handler,
    SearchGeneral_handler
)

# [관리 상속] 상태에 누적 저장되는 답변 데이터 DTO
# AgentState의 messages 중, 지금 막 들어온 마지막 메시지를 제외한 나머지를 '이전 대화 이력'으로 취급한다.
def _get_history(state: AgentState) -> List[BaseMessage]:
    messages = state.get("messages", [])
    return messages[:-1] if messages else []
    
    
# ======================= [메인 함수] =======================
# LLM이 스스로 실행할 함수들 (기존 함수 재사용)

# 1. 개인 맞춤 졸업사정 처리
# message: LLM이 의도를 파악해 놓은 사용자의 질문
# state: 내부의 user_profile 사용 (LLM이 자동으로 못 넣고 백엔드에서 직접 넣어줘야 하는 값)
@tool
def check_graduation_status(
    message: str,
    state: Annotated[AgentState, InjectedState] 
) -> str:
    """
    개인 맞춤 졸업사정 - 사용자가 지금까지 이수한 과목을 바탕으로
    졸업 가능 여부, 남은 학점, 미이수 과목을 계산할 때 사용한다.
 
    이 함수를 사용해야 하는 질문 예시:
    - "나 졸업할 수 있어?"
    - "남은 학점이 뭐야?"
    - "2024학번이고 컴퓨터과학, 이산수학 들었어. 몇 학점 남았어?"
    """
    result = CheckGraduationStatus_handler.handle_check_graduation_status_query(
        message=message,
        user_profile=state.get("user_profile")
    )
    return result["message"]

# 2. 교육과정 조회
# message: LLM이 의도를 파악해 놓은 사용자의 질문
# admission_year: 입학 년도 (LLM이 자동으로 파악해서 채워넣음)
@tool
def get_curriculum(
    message: str,
    admission_year: Optional[int] = None    
) -> str:
    """
    특정 학번의 특정 요건(전공필수/전공선택/교양 등)에 해당하는
    과목 전체 목록을 조회할 때 사용한다. (개인 이수 여부와 무관, 전체 리스트)
 
    이 함수를 사용해야 하는 질문 예시:
    - "2024학번 전공필수 과목이 뭐예요?"
    - "25학번 교양 필수 알려줘"
    """
    result = GetCurriculum_handler.handle_curriculum_query(
        message=message,
        admission_year=admission_year
    )
    return result["message"]

# 3. 동일/대체 과목 조회
# message: LLM이 의도를 파악해 놓은 사용자의 질문
# course_name_or_code: 과목명 또는 과목 코드 (LLM이 자동으로 파악해서 채워넣음)
@tool
def get_equivalent_course(
    message: str,
    course_name_or_code: str
) -> str:
    """
    특정 과목의 동일/대체 과목 정보를 조회할 때 사용한다.
    과목명이 바뀌었는지, 대체 과목이 무엇인지, 중복/재수강이 가능한지 등을 다룬다.
 
    이 함수를 사용해야 하는 질문 예시:
    - "OO과목 바뀐거 있어?"
    - "OO과목 대신 뭐 들으면 돼?"
    - "OO이랑 XX랑 같은 과목인가요?"
    """
    result = GetEquivalentCourse_handler.handle_equivalent_course_query(
        message=message,
        course_name_or_code=course_name_or_code
    )
    return result["message"]

# 4. 강의평가 검색
# message: LLM이 의도를 파악해 놓은 사용자의 질문
# state: 이전 질문 데이터 (LLM이 자동으로 못 넣고 백엔드에서 직접 넣어줘야 하는 값)
@tool
def search_reviews(
    message: str,
    state: Annotated[AgentState, InjectedState]    
) -> str:
    """
    특정 강의/교수의 수강 후기, 강의평가를 조회하거나 작성 방법을 안내할 때 사용한다.
 
    이 함수를 사용해야 하는 질문 예시:
    - "자료구조 강의평가 보여줘"
    - "김철수 교수님 강의 후기 있어요?"
    """
    result = SearchReviews_handler.handle_search_reviews_query(
        message=message,
        history=_get_history(state)
    )
    return result["message"]

# 5. 일반 정보 검색
# message: LLM이 의도를 파악해 놓은 사용자의 질문
# state: 이전 질문 데이터 (LLM이 자동으로 못 넣고 백엔드에서 직접 넣어줘야 하는 값)
@tool
def search_general(
    message: str,
    state: Annotated[AgentState, InjectedState]    
) -> str:  
    """
    학사일정, 도서관, 장학금, 통학버스, 연락처, 실험실 등
    고정된 서술형 정보를 검색할 때 사용한다.
 
    이 함수를 사용해야 하는 질문 예시:
    - "2025년 1학기 개강일이 언제예요?"
    - "장학금 신청 기간이 언제인가요?"
    """
    result = SearchGeneral_handler.handle_search_general_query(
        message=message,
        history=_get_history(state)
    )
    return result["message"]

# [함수 묶기] LLM(에이전트)이 아래 세트에서 골라서 자동으로 함수 사용
AGENT_TOOLS = [
    check_graduation_status,
    get_curriculum,
    get_equivalent_course,
    search_reviews,
    search_general
]