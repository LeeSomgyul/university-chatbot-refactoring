# ===============================================
# [1단계] Aho-Corasick 알고리즘을 사용한 정확한 교과목 매칭 
# ===============================================

import ahocorasick
from typing import NamedTuple, List
from app.matching.course_caching import get_normalized_course_list

_automaton = None

# [매칭된 결과물 DTO]
class ExactMatch(NamedTuple):
    matched_name: str       # 과목명
    course_codes: List[str] # 과목명에 해당하는 과목코드 목록
    start: int              # 사용자의 질문 문장에서 과목명 단어가 시작하는 인덱스 위치
    end: int                # 사용자의 질문 문장에서 과목명 단어가 끝나는 인덱스 위치


# [검색 엔진 트리 1회 빌드] course_caching.py에서 캐싱해놓은 과목명을 가져와서 트리에 등록
def _get_automaton():
    global _automaton

    # 1. 이미 트리 채워져있으면 패스
    if _automaton is not None:
        return _automaton

    # 2. 정규화 + 캐싱데이터로 저장되어져있는 과목명 및 과목코드 가져오기
    course_list = get_normalized_course_list()

    # 3. Aho-Corasick 엔진
    automaton = ahocorasick.Automaton()

    # 4. 정규화된 map에서 과목명만 트리에 저장
    for normalized_course_name in course_list:
        automaton.add_word(normalized_course_name, normalized_course_name) 
    automaton.make_automaton()

    _automaton = automaton

    return _automaton