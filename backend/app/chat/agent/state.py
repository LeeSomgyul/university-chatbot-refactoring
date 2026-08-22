# ===============================================
#  [복합 질문] LangGraph 그래프를 도는 동안 노드들 사이에서 공유되는 데이터 구조 
# ===============================================

from typing import Optional
from langgraph.graph import MessagesState
from app.models.schemas import UserProfile

# [상태에 누적 저장되는 것들] 1~4번은 MessagesState에서 제공 
# 1. HumanMessage: 사용자의 원본 질문
# 2. AIMessag: LLM이 해당 함수를 부르겠다고 판단한 기록
# 3. ToolMessage: 해당 함수를 실행한 결과 (복합 질문이기 때문에 여러번 반복 저장됨)
# 4. AIMessage: LLM이 최종 자연어 답변을 만든 것 (종료 조건)
# 5. (추가)user_profile: 개인 맞춤 정보가 필요한 도구를 호출할 때 필요 (예: 졸업사정)
class AgentStaget(MessagesState):
    user_profile: Optional[UserProfile]