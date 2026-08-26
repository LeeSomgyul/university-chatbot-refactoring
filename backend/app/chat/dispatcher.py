# ===============================================
#                  챗봇 시작점
# ===============================================
# 역할: routing_connector.py의 route() 함수를 실행하여 사용자 질문에 대해 함수 분기 처리

from typing import List
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.models.schemas import ChatRequest, ChatResponse
from app.chat.agent.graph_assemble import agent_graph


# [보조 함수]
# ChatRequest의 message(현재 질문)와 history(이전 질문 기억)를 더해서
# langGraph이 이해할 수 있는 AgentState로 합치기 (backend\app\chat\agent\state.py)
# - 참고: 챗봇은 이전 대화 문맥을 파악하기 위해 history(이전 질문) + message(현재 질문)을 합쳐서 받는다 
def _convert_messages(request: ChatRequest) -> List:
    message = []
    
    # 1. history (이전 질문 기억 저장)
    # 사용자의 이전 질문은 HumanMessage / 챗봇의 이전 답변은 AIMessage에 저장
    for hmsg in request.history:
        if hmsg.role == "user":
            message.append(HumanMessage(content=hmsg.content))
        elif hmsg.role == "assistant":
            message.append(AIMessage(content=hmsg.content))
            
    # 2. message (금방 사용자가 한 새로운 질문)
    message.append(HumanMessage(content=request.message))
    
    return message


# [메인 함수] 챗봇 시작
def chat(request: ChatRequest) -> ChatResponse:
    # 1. AgentState에 넘길 DTO
    initial_AgentState = {
        "messages": _convert_messages(request),
        "user_profile": request.user_profile,
        "last_restaurant_search": request.last_restaurant_search,
        "last_search_sections": None,
    }
    
    # 2. langgraph흐름으로 넘겨주기 -> 이후 LLM 돌고난 뒤 결과물 가져오기
    result_state = agent_graph.invoke(initial_AgentState)
    
    # 3. 최종 AI 답변(쌓인 state의 제일 마지막은 최종 답변이 있음)
    final_message = result_state["messages"][-1]
    final_text =  final_message.content if isinstance(final_message, AIMessage) else str(final_message)
    
    # 4. (확인용) 최종 답변을 얻는데까지 어떤 함수(도구)들을 거쳤나 확인
    tool_messages = []
    for msg in result_state["messages"]:
        if isinstance(msg, ToolMessage):
            tool_messages.append(msg)
            
    # 4-1. 최종 함수 이름들        
    sources = [{"tool": msg.name} for msg in tool_messages]
    print(f"tool:{sources}")
    
    # 5. (확인용) LLM이 추출한 맛집 목록
    restaurants = []
    for msg in tool_messages:
        if msg.name == "search_restaurant" and getattr(msg, "artifact", None):
            restaurants.extend(msg.artifact)
            
    return ChatResponse(
        message=final_text,
        sources=sources,
        matched_function="agent_graph",
        session_id=request.session_id,
        sections=result_state.get("last_search_sections"),
        user_profile=result_state.get("user_profile"),
        last_restaurant_search=result_state.get("last_restaurant_search"),
    )