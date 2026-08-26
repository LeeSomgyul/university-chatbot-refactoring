# ===============================================
#  [복합 질문-2단계] 기존 핸들러 함수들을, LLM이 직접 실행할 수 있도록 형태 변환 
# ===============================================

from typing import List, Annotated, Optional
from app.chat.agent.state import AgentState
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from app.chat.agent.state import UpdateAgentState
from app.chat.handlers import (
    CheckGraduationStatus_handler,
    GetCurriculum_handler,
    GetEquivalentCourse_handler,
    SearchReviews_handler,
    SearchGeneral_handler,
    SearchRestaurant_handler
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
# state(읽기전용): 이전 답변을 통해 state에 저장되어 있는 user_profile 꺼내오는 역할
# tool_call_id: LLM이 도구(함수) 선택할 때 번호표도 같이 전달 (함수 이름 말고 번호로 함수 작업 끝났는지 확인함)
# Command(쓰기전용): 새롭게 얻은 정보를 state에 업데이트 하는 역할 
@tool
def check_graduation_status(
    message: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    개인 맞춤 졸업사정 - 사용자가 지금까지 이수한 과목을 바탕으로
    졸업 가능 여부, 남은 학점, 미이수 과목을 계산할 때 사용한다.
 
    이 함수를 사용해야 하는 질문 예시:
    - "나 졸업할 수 있어?"
    - "남은 학점이 뭐야?"
    - "2024학번이고 컴퓨터과학, 이산수학 들었어. 몇 학점 남았어?"
    """
    
    # 1. 도구(함수) 실행 후 결과 
    result = CheckGraduationStatus_handler.handle_check_graduation_status_query(
        message=message,
        user_profile=state.get("user_profile")
    )
    
    # 2. state에 message 및 user_profile 업데이트 
    update: UpdateAgentState = {
        "messages": [
            ToolMessage(content=result.message, tool_call_id=tool_call_id)
        ]
    }
    
    if result.user_profile is not None:
        update["user_profile"] = result.user_profile
    
    return Command(update=update)

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
    return result.message

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
    return result.message

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
    return result.message

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
    return result.message

# 6. 식도락 검색
# message: 사용자의 질문 원문
# location_keyword: 키위매칭/LLM 풀백으로 얻은 위치 키워드
# food_keyword: LLM으로 얻은 음식 키워드 (복수처리)
# combine_mode: 복수 음식키워드 and/or 판단 (섹션 처리용)
@tool
def search_restaurant(
    message: str,
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    location_keyword: Optional[str] = None,
    food_keyword: Optional[List[str]] = None,
    combine_mode: Optional[str] = None,
    review_query: Optional[str] = None,
)->Command:
    """
    학교 근처 음식점, 카페, 맛집 추천 요청을 처리한다. (카카오맵 실시간 검색)

    이 함수를 사용해야 하는 질문 예시:
    - "정문 근처 떡볶이 맛집 추천해줘"
    - "맛집 추천해줘"
    - "순천대 근처 카페 알려줘"
    - "정문 근처 중식이나 분식 맛집 추천해줘"

    위치나 음식 종류가 언급 안 될 수도 있다 (그럴 땐 인자를 비워둔다).

    중요: 음식 종류가 2개 이상 언급되면(예: "중식이나 분식", "떡볶이랑 마라탕"),
    이 함수를 여러 번 호출하지 말고 단 한 번만 호출하면서
    food_keyword에 언급된 모든 음식을 리스트로 함께 담아라.
    예: "중식이나 분식" → food_keyword=["중식", "분식"], combine_mode="or"
    예: "떡볶이랑 마라탕" → food_keyword=["떡볶이", "마라탕"], combine_mode="and"

    review_query: 사용자가 음식 종류가 아니라  맛/서비스/분위기 등
    가게의 특징을 언급하면 이 값을 채운다. 학생 리뷰를 기반으로 검색한다.
    예: "매운 거 잘하는 곳 추천해줘" → review_query="매운맛"
    예: "친절한 곳 알려줘" → review_query="친절함"
    예: "가성비 좋은 분식집" → review_query="가성비"
    예: "청결한 식당 추천" → review_query="청결도"
    단순 음식 종류 요청("떡볶이 맛집 추천해줘")에는 review_query를 채우지 않는다.
    """
    # 검색 전 이전 조건 읽기 (state)
    previous_search = state.get("last_restaurant_search")

    # 더 추천해줘 => 검색조건이 하나도 없을 경우에만 이전 조건 이어받기
    if not location_keyword and not food_keyword and not review_query and previous_search:
        location_keyword = previous_search.get("location_keyword")
        food_keyword = previous_search.get("food_keyword")
        review_query = previous_search.get("review_query")

    exclude_urls = previous_search.get("shown_place_urls") if previous_search else None

    # 함수실행
    result = SearchRestaurant_handler.handle_search_restaurant_query(
        location_keyword=location_keyword,
        food_keyword=food_keyword,
        combine_mode=combine_mode,
        message=message,
        review_query=review_query,
        exclude_urls=exclude_urls
    )

    # state 갱신 (artifact 대신 state 필드로 전달)
    update: UpdateAgentState = {
        "messages": [
            ToolMessage(content=result.message, tool_call_id=tool_call_id)
        ],
        "last_search_sections": result.sections,
    }

    if result.last_restaurant_search is not None:
        update["last_restaurant_search"] = result.last_restaurant_search

    return Command(update=update)


# [함수 묶기] LLM(에이전트)이 아래 세트에서 골라서 자동으로 함수 사용
AGENT_TOOLS = [
    check_graduation_status,
    get_curriculum,
    get_equivalent_course,
    search_reviews,
    search_general,
    search_restaurant,
]