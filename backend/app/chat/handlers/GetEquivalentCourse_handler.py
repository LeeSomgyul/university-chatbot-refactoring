# ===============================================
#      [핸들러] 관계형DB: 동일/대체 과목 조회
# ===============================================
# - 역할: routing_schemas.py의 GetEquivalentCourse로 사용자의 질문을 받아서
# 관계형 DB(equivalent_courses 테이블)를 조회한 뒤, 답변을 생성하여 반환

import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config import settings
from app.domain.equivalent_course.service import equivalent_course_service
from app.matching.ahocorasick_matching import find_exact_match
from app.matching.course_code_choosing import choose_course_code
from app.matching.morpheme_analyzing import extract_nouns
from app.matching.normalize import normalize
from app.matching.fuzzy_matching import find_fuzzy_match, FuzzLLMCandidate
from app.matching.llm_matching import find_llm_match


_llm = None

# [보조 함수] LLM 가져오기
def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            openai_api_key=settings.openai_api_key
        )
    return _llm


# [보조 함수] JSON 형식 -> LLM 자연어 처리
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

# [보조 함수] 과목명의 코드 선택이 애매한 경우 사용자에게 학번 질문 
# 예) matched_name = "컴퓨터개론"
# 예) candidates = {"course_code": "CS101", "effective_year": 2018}, ...
def _build_ambiguous_message(matched_name: str, candidates: list) -> str:
    years = sorted({str(c["effective_year"]) for c in candidates if c.get("effective_year")})
    codes = sorted({c["course_code"] for c in candidates})

    years_example = ", ".join(years) if years else "예: 2025"
    codes_example = ", ".join(codes)

    return f"""'{matched_name}'이라는 이름의 과목이 여러 개 있어서 정확히 어느 과목을 말씀하시는지 확인이 필요해요! 😊
 
몇 년도 기준으로 알고 계신 과목명인가요? (예: {years_example})
또는 정확한 과목코드를 알려주시면 더 빠르게 찾아드릴게요. (예: {codes_example})"""

# [보조 함수] LLM이 추측한 결과를 1개 보여주면서 사용자에게 정확한 과목명 또는 과목코드 질문
def _build_llm_suggestion_message(llm_result: FuzzLLMCandidate) -> str:
    codes = ", ".join(sorted(set(llm_result.course_codes)))
    
    return f"""정확히 어떤 과목을 말씀하시는지 확신이 서지 않지만, 혹시 '{llm_result.matched_name}'(과목코드: {codes})을 찾으시는 건가요? 🤔
 
맞다면 정확한 과목명이나 과목코드로 다시 한번 질문해주시겠어요?
아니라면 조금 더 구체적으로 과목명을 알려주시면 정확히 찾아드릴게요!"""


# [메인 함수] 동일/대체 과목 조회
# course_name_or_code: LLM이 질문에서 추출한 과목명 또는 과목 코드
def handle_equivalent_course_query(course_name_or_code: str, message: str = None) -> Dict[str, Any]:
    print(f"☑️ [핸들러 진입] 동일/대체 과목 조회: course_name 또는 code={course_name_or_code}")
    
    if message is None:
        message = course_name_or_code

    # 1. 앞뒤 공백 제거된 질문에서 추출한 과목명 또는 과목 코드
    query = normalize(course_name_or_code.strip()) 

    # 2. 과목명 -> 과목코드 변환
    # 2-1. 이미 과목 코드 형식이라면 
    if re.match(r'^[A-Za-z]{2}\d{4}$', query):
        course_code = query.upper()
    else:
        # 2-2. 과목 명 형식이라면 Aho-Corasick 알고리즘 실행
        match = find_exact_match(query)

        # 2-3. Aho-Corasick 알고리즘 실패하면 형태소분석 실행 후 다시 Aho-Corasick 알고리즘 실행
        if match is None:
            nouns_only = extract_nouns(query)
            if nouns_only != query:
                match = find_exact_match(nouns_only)
                
        # 2-4. 형태소분석도 실패하면 Fuzzy Matching 알고리즘으로 실행
        if match is None:
            fuzzy_result = find_fuzzy_match(query)
            if fuzzy_result:
                match = fuzzy_result
                
        # 2-5. Fuzzy Matching 알고리즘도 실패하면 LLM으로 질문
        if match is None:
            llm_result = find_llm_match(message)
            if llm_result:
                return{
                    "message": _build_llm_suggestion_message(llm_result),
                    "matched_function": "handle_equivalent_course_query",
                    "sources": [],
                    "needs_profile": False
                }

        if match is None:
            return{
                "message": f"'{course_name_or_code}' 과목을 찾을 수 없어요. 😥 정확한 과목명이나 과목코드로 다시 질문해주시겠어요?",
                "matched_function": "handle_equivalent_course_query",
                "sources": [],
                "needs_profile": False
            }

        # 2-3. 과목의 코드 선택
        result = choose_course_code(match.course_codes)

        if result.status == "ambiguous":
            return{
                "message": _build_ambiguous_message(match.matched_name, result.candidates),
                "matched_function": "handle_equivalent_course_query",
                "sources": [],
                "needs_profile": True
            }

        course_code = result.course_code

    # 3. 과목이 바뀐적 있는지 확인
    history_course_info = equivalent_course_service.get_mapping_info(course_code)

    # 3-1. 과목이 바뀐적 없는 경우
    if history_course_info is None:
        return{
            "message": f"'{course_code}' 과목은 별도의 동일/대체 과목 변경 이력이 없어요. 😊",
            "matched_function": "handle_equivalent_course_query",
            "sources": [],
            "needs_profile": False
        }

    # 3-2. 과목 정보가 바뀐적 있는 경우
    facts = equivalent_course_service.get_equivalent_course(course_code)

    change_history = {"변경 이력": history_course_info}
    if facts:
        change_history["매핑 유형"] = facts.get('mapping_type', '정보없음')
        change_history["중복 이수 가능 여부"] = "가능" if facts.get('allow_duplicate') else "불가능"
        change_history["재수강 가능 여부"] = "가능" if facts.get('allow_retake', True) else "불가능"

    message = _generate_natural_answer(change_history)

    return{
        "message": message,
        "matched_function": "handle_equivalent_course_query",
        "sources": [{"table": "equivalent_courses", "course_code": course_code}],
        "needs_profile": False 
    }
