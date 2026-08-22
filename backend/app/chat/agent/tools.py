# ===============================================
#  [복합 질문] 기존 핸들러 함수들을, LLM이 직접 실행할 수 있도록 형태 변환 
# ===============================================

from app.chat.handlers import (
    CheckGraduationStatus_handler,
    GetCurriculum_handler,
    GetEquivalentCourse_handler,
    SearchGeneral_handler,
    SearchReviews_handler
)
