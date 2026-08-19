# ===============================================
#                  챗봇 시작점
# ===============================================
# 역할: routing_connector.py의 route() 함수를 실행하여 사용자 질문에 대해 함수 분기 처리

from typing import Dict, Any, Optional, List
from app.models.schemas import UserProfile, ChatMessage
from app.chat.routing_connector import routing_connector
from app.chat.handlers import (
    CheckGraduationStatus_handler,
    GetCurriculum_handler,
    GetEquivalentCourse_handler,
    SearchReviews_handler,
    SearchGeneral_handler,
)

# message: 사용자의 질문 문장
# user_profile: 사용자의 개인 맞춤 제공 정보 (학점, 학번 등)
# history: 이전 질문 기억
def chat(
    message: str,
    user_profile: Optional[UserProfile] = None,
    history: List[ChatMessage] = None    
) -> Dict[str, Any]:
    if history is None:
        history = []
        
    # 1. 사용자의 질문을 분석해서 어떤 함수로 보낼지 결정
    decision = routing_connector.route(message)
    
    # 2. 함수 판단에 따라서 실제 핸들러랑 연결
    if decision.function_name == "CheckGraduationStatus":
        return CheckGraduationStatus_handler.handle_check_graduation_status_query(
            message=message, user_profile=user_profile, history=history
        )
        
    if decision.function_name == "GetCurriculum":
        return GetCurriculum_handler.handle_curriculum_query(
            message=message, admission_year=decision.arguments.get("admission_year")
        )
    
    if decision.function_name == "GetEquivalentCourse":
        return GetEquivalentCourse_handler.handle_equivalent_course_query(
            course_name_or_code=decision.arguments["course_name"]
        )
        
    if decision.function_name == "SearchReviews":
        return SearchReviews_handler.handle_search_reviews_query(
            message=message, history=history
        )
        
    return SearchGeneral_handler.handle_search_general_query(
        message=message, history=history
    )