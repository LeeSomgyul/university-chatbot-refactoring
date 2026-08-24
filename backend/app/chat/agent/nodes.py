# ===============================================
#  [복합 질문-3단계] AgentState를 보고 도구(함수)를 더 선택할지, 최종 응답을 낼지 결정
# ===============================================

from langchain_openai import ChatOpenAI
from app.config import settings
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.chat.agent.state import AgentState
from app.chat.agent.tools import AGENT_TOOLS
from app.chat.agent.state import UpdateAgentState

_llm_with_tools = None

SYSTEM_PROMPT = """당신은 순천대학교 컴퓨터공학과 안내 챗봇입니다.
사용자 질문에 답하기 위해 필요한 도구를 순서대로 호출하세요.
 
중요 규칙:
1. 질문에 여러 가지 요청이 섞여 있으면, 필요한 도구를 전부 호출해서
   모든 요청에 답할 수 있는 정보를 다 모은 뒤에 최종 답변을 작성하세요.
   하나만 처리하고 끝내지 마세요.
2. 질문에 "이거", "그거", "그 과목", "그분"처럼 무엇을 가리키는지
   명확하지 않은 표현이 있다면, 이전 대화나 이미 얻은 도구 실행 결과를
   참고해서 그것이 무엇을 뜻하는지 먼저 파악하세요. 파악이 되면, 다음
   도구를 호출할 때는 그 모호한 표현 대신 실제로 파악한 내용을 풀어서
   전달하세요.
3. 모든 정보가 모였다면, 도구를 더 호출하지 말고 지금까지 얻은 정보를
   종합해서 자연스러운 한국어 문장으로 최종 답변을 작성하세요.
4. 도구 실행 결과에 없는 내용을 지어내지 마세요.
"""

# [보조 함수] LLM 엔진 1회 빌드 및 도구(함수) LLM에게 알려주기
def _get_llm_with_tools() -> ChatOpenAI:
    global _llm_with_tools
    
    if _llm_with_tools is None:
        llm = ChatOpenAI(
            model=settings.model_name,
            temperature=0,
            api_key=settings.openai_api_key
        )
        _llm_with_tools = llm.bind_tools(AGENT_TOOLS)
    return _llm_with_tools


# [메인 함수] 판단 노드
# - 역할: 도구(함수=AGENT_TOOLS)를 더 불러야 하나, 이제 답할 수 있나를 LLM에게 생각하도록 한 뒤 판단하도록 하는 노드
# - 응답1: 도구를 더 호출해야 한다고 판단하면 -> tool_calls가 채워진 AIMessage 생성
# - 응답2: 이제 답할 수 있다고 판단하면 -> tool_calls가 없는 최종 답변 내용을 담은 AIMessage 생성
def agent_node(state: AgentState) -> UpdateAgentState:
    # 1. LLM 1회 빌드 및 도구(함수) 가져오기
    llm_wiht_tools = _get_llm_with_tools()
    
    # 2. LLM에게 보여줄 메시지 생성 (명령어 프롬프트 + 누적된 state)
    message = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    # 3. LLM에게 메시지 전송 및 응답 받기
    llm_response = llm_wiht_tools.invoke(message)
    
    # 4. 판단 결과 (응답1 or 응답2)
    return UpdateAgentState(messages=[llm_response])

# [메인 함수] 실행 노드
# - 역할: 판단 노드에서 도구를 더 불러야 한다면, 해당 도구(함수)를 실행하는 노드
# - 참고: 도구를 실행하는 노드는 langgraph에서 기본 제공하기 때문에, 도구 리스트만 넘겨주면 된다.
tools_node = ToolNode(AGENT_TOOLS)
    