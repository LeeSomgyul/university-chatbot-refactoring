# ===============================================
# [2단계] ExactMatch의 과목코드 List에서 1개 선택
# ===============================================
# - 역할: ahocorasick_matching.py의 결과물인 ExactMatch에서는 course_codes를
# List[str] 형식으로 출력하기 때문에, 사용자의 상황에 맞는 course_codes로 1개 필터링 해야한다.

from typing import NamedTuple, Optional, List, Dict
from app.domain.equivalent_course.service import equivalent_course_service
from app.matching.course_caching import get_course_list

# [과목 코드 선택 결과 DTO]
class ResolveResult(NamedTuple):
    status: str                             # 선택 결과 상태 (예: "resolved"(확정) | "not_found"(없음.예외처리) | "ambiguous"(애매))
    course_code: Optional[str] = None       # 확정 과목 코드 (status == "resolved" 일때만 값 있음)
    candidates: Optional[List[Dict]] = None # 애매해서 선택 못한 과목 코드 리스트 (status == "ambiguous" 일때만 값 있음)


# [메인 함수] course_code 후보들 중에서 어떤걸 1개로 확정할지 판단 
def choose_course_code(course_code: List[str]) -> ResolveResult:
    # 예외) ExactMatch에서 course_code가 비워져 있을 경우 "not_found" 반환
    if not course_code:
        return ResolveResult(status="not_found")

    # 1. ExactMatch에서 course_code가 1개일 경우 (이미 확정되어있어서 추가적인 로직 필요 없음)
    if len(course_code) == 1:
        return ResolveResult(
            status="resolved",
            course_code=course_code[0]
        )

    # 2. ExactMatch에서 course_code가 2개 이상일 경우
    first_code = course_code[0]

    # 2-1. 두 과목 코드가 동일/대체 과목인지 판단
    all_same_chain = all(
        equivalent_course_service.is_equivalent(first_code, other_code)
        for other_code in course_code[1:]
    )

    # 2-2. 같은 체인(세트)에 속하면 첫 번째 과목 코드 선택하여 확정
    if all_same_chain:
        return ResolveResult(
            status="resolved",
            course_code=first_code
        )

    # 2-3. 다른 체인이면 사용자에게 되묻기 (다른 학과인 경우 등)
    all_courses = get_course_list()
    candidates = [
        {"course_code": c["course_code"], "effective_year": c.get("effective_year")}
        for c in all_courses
        if c["course_code"] in course_code
    ]
    return ResolveResult(
        status="ambiguous",
        candidates=candidates
    )