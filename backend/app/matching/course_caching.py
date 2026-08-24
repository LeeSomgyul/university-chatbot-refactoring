# ===============================================
# [캐싱] DB의 equivalent_courses 테이블의 값들을 전체 읽어서 메모리에 캐싱(저장) 
# ===============================================
# - Aho-Corasick 알고리즘을 사용하기 위해서는 과목명이 모두 저장되어져있어야 함

from typing import Dict, List
from app.database.supabase_client import supabase
from app.matching.normalize import normalize


_course_list_cache: List[Dict] = None  # equivalent_courses 테이블의 원본 데이터 행 (과목코드, 과목명, 입학년도)
_normalized_course_list_cache: Dict[str, List[str]] = (None) # 실제 검색에 사용될 맵: {"정규화 완료된 과목명" : ["과목코드1", "과목코드2"]}


# [캐싱 실행]
def _load():
    global _course_list_cache, _normalized_course_list_cache

    # 1. 이미 메모리에 캐시가 채워져 있다면? -> DB 조회 안하고 즉시 종료
    if _course_list_cache is not None:
        return

    # 2. 캐시가 비어있다면 DB의 equivalent_courses 테이블 1회 전체 조회
    result = (
        supabase.table('equivalent_courses')
        .select('old_course_code, old_course_name, new_course_code, new_course_name, effective_year')
        .execute()
    )
    # 예: rows = [{"old_course_code": "CS0668","old_course_name": "시스템프로그래밍","new_course_code": "CS0675","new_course_name": "리눅스시스템","effective_year": 2013}, ...]
    rows = result.data or []

    # 과목코드, 과목명이 같은 행이 중복 저장될 수 있기 때문에 set으로 중복 제거
    seen_codes = set()
    course_list: List[Dict] = []

    # 3. 한 행을 2개 항목으로 나눔(old + new를 old 따로 new 따로 분리)
    for row in rows:
        for code_key, name_key in [('old_course_code', 'old_course_name'),
                                   ('new_course_code', 'new_course_name')]:
            code = row.get(code_key)
            name = row.get(name_key)

            if not code or not name:
                continue
            if code in seen_codes:
                continue
            seen_codes.add(code)
            course_list.append({
                'course_code': code,
                'course_name': name,
                'effective_year': row.get('effective_year'),
            })

    # 4. 캐시 변수에 저장
    _course_list_cache = course_list

    # 5. 정규화 완료된 과목명 map 생성
    mapping: Dict[str, List[str]] = {}

    # 5. 정규화
    for course in _course_list_cache:
        # 5-1. 과목명 정규화 실행
        key = normalize(course['course_name'])

        # 5-2. 기존 map에서 해당 과목명 데이터 없으면 빈 리스트로 초기화
        mapping.setdefault(key, [])

        # 5-3. 같은 과목명끼리 묶어서 저장하지만 과목코드는 중복저장하지 않음
        if course['course_code'] not in mapping[key]:
            mapping[key].append(course['course_code'])

    _normalized_course_list_cache = mapping


# [함수 공유] 다른 파일에서도 사용할 수 있도록 공유
# 1. 전체 과목 목록 리스트 원본
def get_course_list() -> List[Dict]:
    _load()
    return _course_list_cache

# 2. 실제 검색용 정규화 완료된 맵 데이터
# 예: {"데이터베이스개론": ["CS101", "CS102"],"운영체제": ["CS201"]}
def get_normalized_course_list() -> Dict[str, List[str]]:
    _load()
    return _normalized_course_list_cache