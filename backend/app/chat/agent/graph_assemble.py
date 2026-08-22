# ===============================================
#  [복합 질문-4단계] state - tools - nodes 연결하여, 반복 가능한 그래프 완성 
# ===============================================

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition
from app.chat.agent.state import AgentState
from app.chat.agent.nodes import agent_node, tools_node

# 1. 빈 상태 가져오기
graph = StateGraph(AgentState)

# 2. 노드 등록
graph.add_node("agent", agent_node)
graph.add_node("tools", tools_node)

# 3. 시작 노드 선택 ("agent" 노드부터 시작)
graph.set_entry_point("agent")

# 4. 조건부: agent_node("agent") 실행 직후, tool_calls의 존재 여부에 따라 "tools"로 갈지 END로 갈지 자동 결정
graph.add_conditional_edges(
    "agent",
    tools_condition, # tool_calls 존재 여부 판단하여 "tools"로 갈지, END로 갈지 결정
    {
        "tools": "tools",
        END: END,
    }
)

# 5. 도구 실행이 끝나면 무조건 다시 판단 노드로 복귀
graph.add_edge("tools", "agent")

# 6. 반복 끝나면 흐름을 최종 조립
agent_graph = graph.compile()

