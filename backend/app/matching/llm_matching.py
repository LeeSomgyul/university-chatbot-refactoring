# ===============================================
# [5단계] LLM으로 동일/대체 교과목 질문 분석
# ===============================================
# - 역할: 1~4단계 알고리즘에서 모두 해결되지 못한 사용자의 질문은 LLM으로 답하기.

from typing import Optional
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from app.config import settings
from app.matching.fuzzy_matching import find_fuzzy_llm_candidates, FuzzLLMCandidate

_llm = None

# [LLM 결과물 DTO 형식 정의] 출력 결과를 아래 규칙을 따라 출력하도록 설정 
class LLMMactch(BaseModel):
    matched_name: Optional[str] = Field(
        description="후보 목록에 있는 과목명 중 사용자가 의도한 것과 정확히 일치하는 이름. "
                    "목록에 있는 이름을 글자 그대로 반환해야 하며, 확신이 서지 않으면 null."
    )

# [보조 함수] LLM 엔진 1회 빌드
def _get_llm() -> ChatOpenAI:
    global _llm
    
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.model_name,
            temperature=0,
            api_key=settings.openai_api_key
        )
    return _llm


# [메인 함수] Fuzzy Matching으로 추출한 후보 5개 중에서 LLM이 판단하여 답하기
def find_llm_match(text: str, num: int = 5) -> Optional[FuzzLLMCandidate]:
    # 1. Fuzzy Matching으로 추출한 5개의 후보
    candidates = find_fuzzy_llm_candidates(text, num)
    
    if not candidates:
        return None
    
    # 2. 5개 후보 리스트에서 과목명들만 추출
    candidate_names = [candidate.matched_name for candidate in candidates]
    
    # 3. LLM 엔진 빌드
    llm = _get_llm()
    
    # 4. LLM이 출력 양식을 인지
    structured_llm = llm.with_structured_output(LLMMactch)
    
    # 5. LLM에게 보낼 요청 정의
    prompt = f"""다음은 대학교 과목명 후보 목록입니다:
{chr(10).join(f"- {name}" for name in candidate_names)}
 
사용자 질문: "{text}"
 
위 후보 목록 중 사용자가 의도한 과목명을 정확히 골라주세요.
목록에 없는 이름을 만들어내지 마세요. 확신이 서지 않으면 null을 반환하세요."""

    # 6. LLM 호출
    try:
        result: LLMMactch = structured_llm.invoke(prompt)
    except Exception as e:
        # 예외: 네트워크 오류, 토큰 초과 등의 오류
        print(f"❌ LLM 최종 판단 실패: {e}")
        return None
    
    # 6-1. LLM이 과목명을 추출하지 못한 경우 
    if result.matched_name is None:
        print(f"❌ LLM도 확신하지 못함 (원본 질문: '{text}')")
        return None
    
    # 6-2. LLM이 후보에 없는 아무 과목명이나 추출한 경우 
    if result.matched_name not in candidate_names:
        print(f"❌ LLM이 후보 목록에 없는 이름 반환, 무시함: '{result.matched_name}'")
        return None

    # 6-3. LLM이 후보에 있는 경우 
    for candidate in candidates:
        if candidate.matched_name == result.matched_name:
            return candidate
    
    return None
    
    
    