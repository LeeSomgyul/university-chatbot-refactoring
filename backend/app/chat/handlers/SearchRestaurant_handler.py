# ===============================================
#      [핸들러] 카카오맵 REST API: 식도락 검색
# ===============================================
"""
    [역할]
    routing_schemas.py의 SearchRestaurant로 사용자의 질문을 받아서
    카카오맵 API를 실시간 호출한 뒤, 답변을 생성하여 반환
    (검색 결과는 DB에 저장하지 않음 - FOOD-003 요구사항)

    [응답 형식]
    "message": 사용자에게 보내줄 최종 응답 문장
    "matched_function": 어떤 함수가 실행되었는지
    "sources": 벡터 검색이라면 어떤 문서를 확인하였는지 (식도락은 항상 빈 리스트)
    "needs_profile": 사용자 개인 데이터가 필요한지 여부
"""

import re

from typing import Dict, Any, Optional, List

from app.utils.embedding import get_embedding_model
from app.utils.llm_client import generate_review_summary
from kiwipiepy import Kiwi

from app.database.supabase_client import supabase
from app.domain.restaurant.kakao_map_client import kakao_map_client
from app.models.schemas import HandlerResponse

DEFAULT_LOCATION_KEYWORD = "순천대"

kiwi = Kiwi()
# 순천대 캠퍼스 내 위치는 유한하므로 사용자 사전에 등록
kiwi.add_user_word("정문","NNP")
kiwi.add_user_word("순천대", "NNP")

# 리뷰 유사도 임계값
SIMILARITY_THRESHOLD = 0.3

# [보조 메서드] 리뷰 기반 검색 -유사도 매칭 함수
# candidates: 카카오맵 반경 검색으로 가져온 가게 목록
# review_query: LLM이 추출한 사용자가 원하는 리뷰 특징
def _match_by_review_query(candidates: list, review_query: str)-> list:
    # review_query를 벡터로 변환
    model = get_embedding_model()
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
def _attach_review_summary(place: dict) -> dict:
    # 카카오맵 원본 데이터 저장
    formatted = _format_place(place)
    place_url = place.get('place_url')
    if not place_url:
        formatted['review_summary'] = None
        return formatted

    try:
        # 리뷰 조회
        result = supabase.table('restaurant_review_summaries')\
            .select('summary')\
            .eq('place_url',place_url)\
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
def _extract_location_keyword(user_message: str)->Optional[str]:
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
def _resolve_location(location_keyword: Optional[str]) -> Dict[str, Any]:
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
def _format_place(place: dict) -> dict:
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
def _detect_combine_mode(message: str, llm_combine_mode: Optional[str]) -> Optional[str]:
    if OR_PATTERN.search(message):
        return "or"
    if AND_PATTERN.search(message):
        return "and"
    return llm_combine_mode  # 패턴 못 찾으면 LLM 판단 그대로 신뢰

def _augment_food_keywords(message: str, llm_food_keyword: Optional[List[str]]) -> Optional[List[str]]:
    connected_pairs = _extract_connected_food_pairs(message)

    if not llm_food_keyword:
        return llm_food_keyword  # LLM이 아예 못 뽑았으면 굳이 우리가 추측하지 않음 (오탐 방지)

    # LLM이 하나라도 뽑았다면, 원문에서 접속조사로 연결된 명사들과 합집합
    combined = list(dict.fromkeys(llm_food_keyword + connected_pairs))
    return combined

# 리뷰 기반 흐름
def _handle_review_based_search(location: dict, final_location_keyword: Optional[str], review_query: str)-> HandlerResponse:
    candidates = kakao_map_client.search_by_category(
        latitude=location["latitude"],
        longitude=location["longitude"],
        category_code="FD6"
    )

    # 후보 => 벡터 유사도 매칭 => 임계값 넘는 장소들 정렬하여 반환
    matched = _match_by_review_query(candidates, review_query)

    # 기본위치 안내문구 준비
    if location["used_default"]:
        response_message = f"순천대 본부 기준으로 맛집을 찾아드렸어요! 📍"
    elif final_location_keyword:
        response_message = f"{final_location_keyword} 근처 맛집을 찾아드렸어요! 😊"
    else:
        response_message = f"근처 맛집을 찾아드렸어요! 😊"


    if not matched:
        top3 = candidates[:3]
        return HandlerResponse(
            message=f"'{review_query}' 관련 리뷰를 찾지 못했어요. 대신 {response_message}",
            sections=[{"keyword": "전체", "restaurants": [_attach_review_summary(p) for p in top3]}],
            matched_function="handle_search_restaurant_query"
        )
    top3 = matched[:3]
    restaurants = []
    for similarity, place, review_content in top3:
        formatted = _format_place(place)
        formatted['review_summary'] = review_content
        restaurants.append(formatted)

    return HandlerResponse(
        message=f"'{review_query}' 관련 리뷰의 {response_message}",
        sections=[{"keyword": review_query, "restaurants": restaurants}],
        matched_function="handle_search_restaurant_query",
    )


def handle_search_restaurant_query(
        # LLM이 뽑아준 원본 값(참고용/폴백)
        location_keyword: Optional[str] = None,
        # LLM이 뽑아준 값 그대로 사용
        food_keyword: Optional[List[str]] = None,
        # 음식키워드 복수 조사 -or/and
        combine_mode: Optional[str] = None,
        # 원본 사용자 질문
        message: str = "",
        # LLM이 뽑아준 리뷰 키워드
        review_query:  Optional[str] = None,
)-> HandlerResponse:
    # =========1.위치 추출=============
    # 위치는 kiwi로 우선 추출
    kiwi_location = _extract_location_keyword(message)
    # Kiwi 우선, 안 되면 LLM 값 폴백
    final_location_keyword = kiwi_location or location_keyword

    if kiwi_location:
        print(f"[LOCATION] Kiwi 매칭 성공: {kiwi_location}")
    elif location_keyword:
        print(f"[LOCATION] Kiwi 매칭 실패, LLM 폴백값 사용: {location_keyword}")
    else:
        print(f"[LOCATION] Kiwi/LLM 둘 다 실패, 기본값 사용 예정")

    # 좌표 추출
    location = _resolve_location(final_location_keyword)

    # 위치 기본값도 매칭 못했다면
    if location["latitude"] is None:
        return HandlerResponse(
            message="위치 정보를 찾을 수 없어요. 다시 시도해주세요. 😥",
            matched_function="handle_search_restaurant_query",
            sources=[],
            user_profile=None,
            needs_profile=False,
            sections=[],
            restaurants=[],
        )

    # =========리뷰 키워드별 카카오맵 검색=============
    if review_query:
        return _handle_review_based_search(location, final_location_keyword, review_query)

    # =========2. 음식키워드별 카카오맵 검색=============
    """
        음식 키워드가 있는 경우:
            음식명(예: "떡볶이")으로 키워드 검색
        음식 키워드가 없는 경우:
            좌표 기반으로 "음식점 전체"(FD6) 카테고리 검색
    """

    # ── 음식 키워드 / combine_mode 보정 ──
    food_keyword = _augment_food_keywords(message, food_keyword)
    combine_mode = _detect_combine_mode(message, combine_mode)

    print(f"[FOOD] 보정 후 food_keyword={food_keyword}, combine_mode={combine_mode}")

    # 음식 키워드 없음
    if not food_keyword:
        results_by_food = {
            "전체": kakao_map_client.search_by_category(
                latitude=location["latitude"], longitude=location["longitude"], category_code="FD6"
            )
        }
    # 음식 키워드 단일
    elif len(food_keyword) == 1:
        results_by_food = {
            food_keyword[0]: kakao_map_client.search_by_keyword(
                food_keyword[0],
                latitude=location["latitude"],
                longitude=location["longitude"],
            )
        }
    # 음식 키워드가 2개 이상 -> 각각 검색
    else:
        results_by_food = {
            kw: kakao_map_client.search_by_keyword(
                kw, latitude=location["latitude"], longitude=location["longitude"]
            )
            for kw in food_keyword
        }
    print(f"[KAKAO] 검색 결과 개수: { {kw: len(v) for kw, v in results_by_food.items()} }")

    # 음식 키워드 안내 문구 준비
    if not food_keyword:
        food_note = ""
    elif len(food_keyword) == 1:
        food_note = f"{food_keyword[0]} "
    else:
        food_note = f"{'와 '.join(food_keyword)} "

    # 기본위치 안내문구 준비
    if location["used_default"]:
        response_message = f"순천대 본부 기준으로 {food_note}맛집을 찾아드렸어요! 📍"
    elif final_location_keyword:
        response_message = f"{final_location_keyword} 근처 {food_note}맛집을 찾아드렸어요! 😊"
    else:
        response_message = f"근처 {food_note}맛집을 찾아드렸어요! 😊"

    # =========3.or인지 and인지 판단==========
    use_or = combine_mode == "or" or (food_keyword and len(food_keyword) > 1 and combine_mode != "and")
    print(f"[DEBUG] food_keyword={food_keyword}, combine_mode={combine_mode}, use_or={use_or}")    # or분기 : 섹션별로 응답 생성

    if use_or:
        sections = []
        has_any_result = False
        for kw, results in results_by_food.items():
            top3 = results[:3] if results else []
            if top3:
                has_any_result = True
            sections.append({
                "keyword": kw,
                "restaurants": [_attach_review_summary(p) for p in top3]
            })
        if not has_any_result:
            return HandlerResponse(
                message= "근처에서 해당 유형의 장소를 찾을 수 없습니다. 😥",
                matched_function= "handle_search_restaurant_query",
            )
        return HandlerResponse(
            message= response_message,
            sections= sections,
            matched_function= "handle_search_restaurant_query"
        )
    # # and이거나 단일 키워드: 기존처럼 통합 응답
    else:
        all_results = [r for results in results_by_food.values() for r in results]
        top3 = all_results[:3]
        if not top3:
            return HandlerResponse(
                message= "근처에서 해당 유형의 장소를 찾을 수 없습니다. 😥",
                matched_function= "handle_search_restaurant_query",
            )
        label = "/".join(results_by_food.keys())
        return HandlerResponse(
            message= response_message,
            sections= [
                {"keyword": label,"restaurants": [_attach_review_summary(p) for p in top3]}
            ],
            matched_function= "handle_search_restaurant_query",
        )