# ===============================================
#  사용자의 질문이 들어왔을 때 라우터(클래스)와 연결
# ===============================================

from typing import NamedTuple, Dict, Any

# [응답 형식 정의]
"""
    function_name: routing_schemas에서 선택한 함수명
    arguments: 해당 함수에서 사용할 매개변수
"""
class SchemasParams(NamedTuple):
    function_name: str
    arguments: Dict[str, Any] 

class RoutingConnector:
    # [초기 셋팅] 서버 켜질 때 LLM 객체 생성 (일단 미리 null로 채워넣기)
    """
        _llm: OpenAi 서버와 통신하기 위한 기본 엔진
        _llm_with_functions: routing_schemas에 있는 함수들을 갖고 있는 객체
    """
    def __init__(self):
        self._llm = None
        self._llm_with_functions = None

    # [초기 셋팅] _llm_with_functions 에다가 routing_schemas 함수들 알려주기
    def _llm_with_functions(self):
        # 1. 초기 객체 채워넣기
        if self._llm_with_functions is None:
            