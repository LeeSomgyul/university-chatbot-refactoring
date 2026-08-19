# ===============================================
#      [핸들러] 관계형DB: 동일/대체 과목 조회
# ===============================================
"""
    [역할]
    routing_schemas.py의 GetEquivalentCourse로 사용자의 질문을 받아서
    관계형 DB(equivalent_courses 테이블)를 조회한 뒤, 답변을 생성하여 반환

    [응답 형식]
    "message": 사용자에게 보내줄 최종 응답 문장
    "matched_function": 어떤 함수가 실행되었는지
    "sources": 벡터 검색이라면 어떤 문서를 확인하였는지
    "needs_profile": 사용자 개인 데이터(학번, 이수과목 등)가 필요한지 여부
"""

import re
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config import settings
from app.database.supabase_client import supabase
from app.domain.equivalent_course.service import equivalent_course_service

# [보조 메서드] course_code를 받아서 course_name으로 변환
# 🚨임시 버전: 문제2(함수 다듬기) 해결할 때 정교하게 다듬기
def _change_course_code(course_name_or_code: str) -> Optional[str]:
    # 1. 이미 과목 코드 형식이라면 (예: CS0668) 그대로 사용
    code_pattern = re.match(r'^[A-Za-z]{2}\d{4}$',course_name_or_code.strip())
    if code_pattern:
        return course_name_or_code.strip().upper()

    # 2. curriculums 테이블에서 과목명(course_name)으로 과목코드(course_code) 조회
    try:
        result = supabase.table('curriculums') \
            .select('course_code, course_name') \
            .ilike('course_name', f'%{course_name_or_code.strip()}%') \
            .limit(1) \
            .execute()

        if result.data:
            return result.data[0]['course_code']
        return None

    except Exception as e:
        print(f"❌ 과목명 -> 코드 변환 실패: {e}")
        return None

# [보조 메서드] LLM 가져오기
def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            openai_api_key=settings.openai_api_key
        )
    return _llm


# [보조 메서드] JSON 형식 -> LLM 자연어 처리
def _generate_natural_answer(facts: Dict[str, Any]) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 순천대학교 컴퓨터공학과 안내 챗봇입니다.
아래 '확정된 사실'만 근거로 학생에게 친절하게 안내하는 답변을 작성하세요.
 
절대 규칙:
1. 확정된 사실에 없는 내용은 절대 추가하지 마세요 (지어내지 마세요).
2. 존댓말을 사용하고 이모지를 적절히 활용해 친근하게 답변하세요.
3. 마크다운 문법(**, ##, - 등)은 사용하지 말고 순수 텍스트만 사용하세요.
4. 간결하게 핵심만 전달하세요.
 
확정된 사실:
{facts_text}"""),
        ("user", "위 사실을 바탕으로 답변해주세요.")
    ])

    facts_text = "\n".join(f"- {k}: {v}" for k, v in facts.items())

    try:
        llm = _get_llm()
        chain = prompt | llm
        response = chain.invoke({"facts_text": facts_text})
        return response.content
    except Exception as e:
        print(f"⚠️ 자연어 답변 생성 실패, 사실 그대로 반환: {e}")
        return "\n".join(f"{k}: {v}" for k, v in facts.items())



# [핸들러] 동일/대체 과목 조회
def handle_equivalent_course(course_name_or_code: str) -> Dict[str, Any]:
    """
        Args:
            course_name: LLM이 질문에서 추출한 과목명 또는 과목 코드
        Returns:
            응답 형식은 모든 응답이 동일하게 Dict 형식
    """
    print(f"☑️ [핸들러 진입] 동일/대체 과목 조회: course_name 또는 code={course_name_or_code}")

    # 1. 과목명 -> 과목코드 변환
    course_code = _change_course_code(course_name_or_code)

    if not course_code:
        return{
            "message": f"'{course_name_or_code}' 과목을 찾을 수 없어요. 😥 정확한 과목명이나 과목코드로 다시 질문해주시겠어요?",
            "matched_function": "get_equivalent_course",
            "sources": [],
            "needs_profile": False
        }

    # 2. 과목이 바뀐적 있는지 확인
    history_course_info = equivalent_course_service.get_mapping_info(course_code)

    # 2-1. 과목이 바뀐적 없는 경우
    if history_course_info is None:
        return{
            "message": f"'{course_code}' 과목은 별도의 동일/대체 과목 변경 이력이 없어요. 😊",
            "matched_function": "get_mapping_info",
            "sources": [],
            "needs_profile": False
        }

    # 2-2. 과목 정보가 바뀐적 있는 경우
    facts = equivalent_course_service.get_equivalent_course(course_code)

    change_history = {"변경 이력": history_course_info}
    if facts:
        change_history["매핑 유형"] = facts.get('mapping_type', '정보없음')
        change_history["중복 이수 가능 여부"] = "가능" if facts.get('allow_duplicate') else "불가능"
        change_history["재수강 가능 여부"] = "가능" if facts.get('allow_retake', True) else "불가능"

    message = _generate_natural_answer(facts)

    return{
        "message": message,
        "matched_function": "get_equivalent_course",
        "sources": [{"table": "equivalent_courses", "course_code": course_code}],
        "needs_profile": False 
    }
