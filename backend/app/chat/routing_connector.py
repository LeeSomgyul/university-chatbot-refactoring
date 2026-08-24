# ===============================================
#  [단일 질문 라우팅] 사용자의 질문이 들어왔을 때 라우터(클래스)와 연결
# ===============================================

from typing import NamedTuple, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.runnables import Runnable
from langchain_core.messages import AIMessage
from app.config import settings
from app.chat.routing_schemas import FUNCTIONS, FUNCTIONS_MAP

# [응답 형식 정의]
# function_name: routing_schemas에서 선택한 함수명
# arguments: 해당 함수에서 사용할 매개변수
class RoutingResponse(NamedTuple):
    function_name: str
    arguments: Dict[str, Any] 

class RoutingConnector:
    # [초기 셋팅] 서버 켜질 때 LLM 객체 생성 (일단 미리 null로 채워넣기)
    # _llm: OpenAi 서버와 통신하기 위한 기본 엔진
    # _llm_with_functions: routing_schemas에 있는 함수들을 갖고 있는 객체
    def __init__(self):
        self._llm = None
        self._llm_with_functions = None

    # [초기 셋팅] _llm_with_functions 에다가 routing_schemas 함수들 알려주기
    def _get_llm_with_functions(self) -> Runnable:
        # 1. 초기 객체 채워넣기
        if self._llm_with_functions is None:
            self._llm = ChatOpenAI(
                model=settings.model_name,
                temperature=0,
                api_key=settings.openai_api_key
            )
            
            # 함수 중 하나는 무조건 고르도록 강제
            self._llm_with_functions = self._llm.bind_tools(FUNCTIONS, tool_choice="required")
        return self._llm_with_functions
    
    # [메인] 사용자의 질문을 분석해서 어떤 함수로 보낼지 결정
    # message: 사용자 질문 원본 문장
    # RoutingResponse(function_name, arguments)
    def route(self, message: str) -> RoutingResponse:
        try:
            # 1. 함수들이 연결되어있는 도구 가져오기
            llm_with_tools = self._get_llm_with_functions()
            
            # 2. LLM에게 사용자 질문을 전달하여 실행 (OpenAI API 호출)
            llm_response = llm_with_tools.invoke(message)
            
            # 예외: LLM이 함수를 선택하지 않은 경우
            if not llm_response.tool_calls:
                print("⚠️ LLM이 함수를 선택하지 않음")
                return RoutingResponse("SearchGeneral", {})
            
            # 🚨 개선 예정: 현재는 함수를 1개만 고를 수 있는것으로 작성
            tool_call = llm_response.tool_calls[0]
            function_name = tool_call["name"]
            arguments = tool_call["args"]
            
            # 예외: LLM이 찾은 함수가 존재하지 않은 경우
            if function_name not in FUNCTIONS_MAP:
                print(f"⚠️ 알 수 없는 함수명: {function_name}, SearchGeneral로 강제 연결")
                return RoutingResponse("SearchGeneral", {})
            
            print(f"☑️ LLM이 결정한 함수: {function_name}({arguments})")
            return RoutingResponse(function_name, arguments)
        
        except Exception as e:
            print(f"❌ 라우팅 실패, SearchGeneral로 강제 연결: {e}")
            return RoutingResponse("SearchGeneral", {})
        
# 다른 파일에서 사용할 수 있도록 공유
routing_connector = RoutingConnector()