# ===============================================
# [1단계] Aho-Corasick 알고리즘을 사용한 정확한 교과목 매칭 
# ===============================================

import ahocorasick
from typing import NamedTuple, List, Optional
from app.matching.course_caching import get_normalized_course_list
from app.matching.normalize import normalize

_automaton = None

# [매칭된 결과물 DTO]
class ExactMatch(NamedTuple):
    matched_name: str       # 과목명
    course_codes: List[str] # 과목명에 해당하는 과목코드 목록
    start: int              # 사용자의 질문 문장에서 과목명 단어가 시작하는 인덱스 위치
    end: int                # 사용자의 질문 문장에서 과목명 단어가 끝나는 인덱스 위치


# [보조 함수] Aho-Corasick 검색 엔진 트리 1회 빌드
# course_caching.py에서 캐싱해놓은 과목명을 가져와서 트리에 등록
def _get_automaton():
    global _automaton

    # 1. 이미 트리 채워져있으면 패스
    if _automaton is not None:
        return _automaton

    # 2. 정규화 + 캐싱데이터로 저장되어져있는 과목명 및 과목코드 가져오기
    course_list = get_normalized_course_list()

    # 3. Aho-Corasick 엔진
    automaton = ahocorasick.Automaton()

    # 4. 정규화된 map에서 과목명 글자들만 한 글자씩 쪼개서 트리에 저장
    for normalized_course_name in course_list:
        automaton.add_word(normalized_course_name, normalized_course_name) 
    automaton.make_automaton()

    _automaton = automaton

    return _automaton

# [메인 함수] Aho-Corasick 알고리즘 실행 파이프라인
# text: 사용자의 질문 (정규화 완료)
def find_exact_match(text: str) -> Optional[ExactMatch]:
    # 1. 사용자가 보낸 질문 정규화된 문장
    # (예: "나고급자료구조수업듣고싶어")
    normalized_match = normalize(text)

    # 2. 과목명 트리 데이터들
    # (예: ["자료구조", "고급자료구조", "운영체제", ...])
    # Aho-Corasick 검색 엔진 트리 1회 빌드 / 채워져있으면 그대로 사용
    automaton = _get_automaton()

    # 3. 과목명 매핑 데이터들
    # (예: {"자료구조": ["CS0101"], "고급자료구조": ["CS0102"], ...})
    course_list = get_normalized_course_list()

    # 4. 알고리즘으로 찾은 과목명 리스트
    candidates: List[ExactMatch] = []

    # 4-1. 알고리즘 실행 
    # .iter 메서드는 end_index(끝지점), matched_name(트리에서 찾은 완성 단어)를 응답해 준다.
    for end_index, matched_name in automaton.iter(normalized_match):
        start_index = end_index - len(matched_name) + 1
        candidates.append(ExactMatch(
            matched_name=matched_name,
            course_codes=course_list[matched_name],
            start=start_index,
            end=end_index
        ))

    # 4-2. 찾은게 없다면
    if not candidates:
        return None

    # 5. 가장 긴 매칭을 우선
    # (예: '고급자료구조'가 '자료구조'에 걸리는 문제 방지)
    best = max(candidates, key=lambda m: len(m.matched_name))
    return best