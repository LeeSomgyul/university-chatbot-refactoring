from typing import Optional, List, Dict, Any

from app.database.supabase_client import supabase
from app.utils import kiwi_client, embedding_client
from app.utils.llm_client import generate_review_summary

import re

DEFAULT_LOCATION_KEYWORD = "순천대"

model = embedding_client.get_embedding_model()
kiwi = kiwi_client.get_kiwi()

# 순천대 캠퍼스 내 위치는 유한하므로 사용자 사전에 등록
kiwi.add_user_word("정문","NNP")
kiwi.add_user_word("도서관","NNP")
kiwi.add_user_word("박물관","NNP")
kiwi.add_user_word("학생회관","NNP")
kiwi.add_user_word("기숙사","NNP")
kiwi.add_user_word("체육관","NNP")
kiwi.add_user_word("본부","NNP")
kiwi.add_user_word("공대","NNP")
kiwi.add_user_word("순천대", "NNP")

# 리뷰 유사도 임계값
SIMILARITY_THRESHOLD = 0.3

# [보조 메서드] 리뷰 기반 검색 -유사도 매칭 함수
# candidates: 카카오맵 반경 검색으로 가져온 가게 목록
# review_query: LLM이 추출한 사용자가 원하는 리뷰 특징
def match_by_review_query(candidates: list, review_query: str)-> list:
    # review_query를 벡터로 변환
    query_embedding = model.encode(review_query).tolist()

    # matched: 가게,유사도,리뷰내용 조합
    matched = []
    for place in candidates:
        place_url = place.get('place_url')
        if not place_url:
            continue
        try:
            # 한 가게의 리뷰내용과 가장 유사도 높은 리뷰 1개 반환
            # => rbc호출에서 병목이 생길 수 있음 최대 db 조회 : 15번
            result = supabase.rpc('match_reviews_by_place', {
                'query_embedding': query_embedding,
                'target_place_url': place_url,
                'match_count': 5
            }).execute()

            if result.data:
                similarity = result.data[0]['similarity']
                print(f"[REVIEW_MATCH] {place_url}: similarity={similarity:.3f}")
                if similarity >= SIMILARITY_THRESHOLD:
                    relevant_reviews = [r['content'] for r in result.data]
                    review_summary = generate_review_summary(relevant_reviews)
                    matched.append((similarity, place, review_summary))
        except Exception as e:
            print(f"[REVIEW_MATCH] {place_url} 조회 실패: {e}")

    # 유사도 높은 순 정렬
    matched.sort(key=lambda x: x[0], reverse=True)

    return matched

# [보조 메서드] 카카오맵 결과에 미리 생성해둔 리뷰 요약을 붙임
# place: 카카오맵 API의 원본 가게 데이터
def attach_review_summary(place: dict) -> dict:
    # 카카오맵 원본 데이터 저장
    formatted = format_place(place)
    place_url = place.get('place_url')
    if not place_url:
        formatted['review_summary'] = None
        return formatted

    try:
        # 리뷰 조회
        result = supabase.table('restaurant_review_summaries') \
            .select('summary') \
            .eq('place_url',place_url) \
            .execute()
        if result.data:
            formatted['review_summary'] = result.data[0]['summary']
        else:
            formatted['review_summary'] = None
    except Exception as e:
        print(f"[REVIEW_SUMMARY] {place_url} 리뷰 요약 조회 실패: {e}")
        formatted['review_summary'] = None
    # 카카오맵 원본데이터 + 리뷰요약
    return formatted


# [보조 메서드] Kiwi로 원본 문장에서 location_keywords와 매칭되는 위치 추출
def extract_location_keyword(user_message: str)->Optional[str]:
    # DB 위치 키워드 목록 조회
    try:
        result = supabase.table('location_keywords').select('keyword,priority').execute()
        keyword_priority = {row['keyword']: row['priority'] for row in result.data}
    except Exception as e:
        print(f"위치 키워드 목록 조회 실패: {e}")
        return None
    # kiwi 형태소 분석 결과
    tokens = kiwi.analyze(user_message)[0][0]
    nouns = {t.form for t in tokens if t.tag in ('NNG','NNP')}

    print(f"[LOCATION_DEBUG] Kiwi가 뽑은 명사: {nouns}")
    print(f"[LOCATION_DEBUG] DB 키워드 목록: {list(keyword_priority.keys())}")

    candidates = [kw for kw in nouns if kw in keyword_priority]
    print(f"[LOCATION_DEBUG] 후보(교집합): {candidates}")

    if not candidates:
        return None

    # 우선순위(작은 숫자)가 가장 높은 걸 선택. 동점이면 이름순으로 결정론적 tie-break
    best = min(candidates, key=lambda kw: (keyword_priority[kw], kw))
    return best


# [보조 메서드] 위치 키워드 -> 위경도 변환
def resolve_location(location_keyword: Optional[str]) -> Dict[str, Any]:
    try:
        result = supabase.table('location_keywords').select('*').execute()
        locations = {loc['keyword']: loc for loc in result.data}
    except Exception as e:
        print(f"위치 테이블 조회 실패: {e}")
        return {"latitude": None, "longitude": None, "used_default": True}

    # 사용자가 위치를 입력했고 그 위치 키워드가 db에 존재하다면
    if location_keyword and location_keyword in locations:
        loc = locations[location_keyword]
        return {"latitude": loc['latitude'], "longitude": loc['longitude'], "used_default": False}

    # 사용자가 위치를 입력하지않았거나 db에 키워드가 존재하지 않는 경우 -> 기본값 시도
    default = locations.get(DEFAULT_LOCATION_KEYWORD)
    if default:
        return {"latitude": default['latitude'], "longitude": default['longitude'], "used_default": True}

    # 기본값이 db에 존재하지 않는다면
    return {"latitude": None, "longitude": None, "used_default": True}

# 카카오맵 응답 답변 구조 생성
def format_place(place: dict) -> dict:
    return {
        "name": place.get('place_name'),
        "address": place.get('road_address_name') or place.get('address_name'),
        "url": place.get('place_url'),
        "phone": place.get('phone'),
        "category": place.get('category_name','').split('>')[-1].strip(),
    }

# or/and 판단용 조사 패턴 (or이 먼저 매칭되도록 순서 중요 - "이나"가 "이랑"보다 먼저 체크되게)
OR_PATTERN = re.compile(r'(이나|나)(?=\s|$)')
AND_PATTERN = re.compile(r'(이랑|랑|와|과)(?=\s|$)')


# [보조 메서드] "A나 B", "A랑 B" 패턴에서 연결된 음식 후보를 원문에서 직접 추출 (DB 불필요)
def _extract_connected_food_pairs(message: str) -> List[str]:
    tokens = kiwi.analyze(message)[0][0]

    candidates = []
    for i, t in enumerate(tokens):
        # 명사(NNG) 바로 뒤에 접속조사(JC, JX 중 이나/이랑/랑/와/과류)가 붙으면
        if t.tag == 'NNG' and i + 1 < len(tokens):
            next_t = tokens[i + 1]
            if next_t.tag in ('JC', 'JX') and next_t.form in ('나', '이나', '랑', '이랑', '와', '과'):
                candidates.append(t.form)
                # 그 다음에 오는 명사도 후보로
                if i + 2 < len(tokens) and tokens[i + 2].tag == 'NNG':
                    candidates.append(tokens[i + 2].form)

    return candidates

# [보조 메서드] 원문에서 or/and 조사를 규칙 기반으로 재확인 (LLM 판단 보정용)
def detect_combine_mode(message: str, llm_combine_mode: Optional[str]) -> Optional[str]:
    if OR_PATTERN.search(message):
        return "or"
    if AND_PATTERN.search(message):
        return "and"
    return llm_combine_mode  # 패턴 못 찾으면 LLM 판단 그대로 신뢰

def augment_food_keywords(message: str, llm_food_keyword: Optional[List[str]]) -> Optional[List[str]]:
    connected_pairs = _extract_connected_food_pairs(message)

    if not llm_food_keyword:
        return llm_food_keyword  # LLM이 아예 못 뽑았으면 굳이 추측하지 않음 (오탐 방지)

    # LLM이 하나라도 뽑았다면, 원문에서 접속조사로 연결된 명사들과 합집합
    combined = list(dict.fromkeys(llm_food_keyword + connected_pairs))
    return combined