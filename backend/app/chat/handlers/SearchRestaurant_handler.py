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

from typing import Dict, Any, Optional, List

from kiwipiepy import Kiwi

from app.database.supabase_client import supabase
from app.domain.restaurant.kakao_map_client import kakao_map_client

DEFAULT_LOCATION_KEYWORD = "순천대"

kiwi = Kiwi()
# 순천대 캠퍼스 내 위치는 유한하므로 사용자 사전에 등록
kiwi.add_user_word("정문","NNP")
kiwi.add_user_word("순천대", "NNP")

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

    candidates = [kw for kw in nouns if kw in keyword_priority]

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

def handle_search_restaurant_query(
        # LLM이 뽑아준 원본 값(참고용/폴백)
        location_keyword: Optional[str] = None,
        # LLM이 뽑아준 값 그대로 사용
        food_keyword: Optional[List[str]] = None,
        # 음식키워드 복수 조사 -or/and
        combine_mode: Optional[str] = None,
        # 원본 사용자 질문
        message: str = ""
)-> Dict[str,Any]:
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
        return{
            "message": "위치 정보를 찾을 수 없어요. 다시 시도해주세요. 😥",
            "matched_function": "handle_search_restaurant_query",
            "sources": [],
            "needs_profile": False
        }

    # =========2. 음식키워드별 카카오맵 검색=============
    """
        음식 키워드가 있는 경우:
            음식명(예: "떡볶이")으로 키워드 검색
        음식 키워드가 없는 경우:
            좌표 기반으로 "음식점 전체"(FD6) 카테고리 검색
    """
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

    # or분기 : 섹션별로 응답 생성
    if use_or:
        sections = []
        has_any_result = False
        for kw, results in results_by_food.items():
            top3 = results[:3] if results else []
            if top3:
                has_any_result = True
            sections.append({
                "keyword": kw,
                "restaurants": [_format_place(p) for p in top3]
            })
        if not has_any_result:
            return {
                "message": "근처에서 해당 유형의 장소를 찾을 수 없습니다. 😥",
                "matched_function": "handle_search_restaurant_query",
                "sources": [],
                "needs_profile": False
            }
        return {
            "message": response_message,
            "sections": sections,
            "matched_function": "handle_search_restaurant_query",
            "sources": [],
            "needs_profile": False
        }
    # # and이거나 단일 키워드: 기존처럼 통합 응답
    else:
        all_results = [r for results in results_by_food.values() for r in results]
        top3 = all_results[:3]
        if not top3:
            return {
                "message": "근처에서 해당 유형의 장소를 찾을 수 없습니다. 😥",
                "matched_function": "handle_search_restaurant_query",
                "sources": [],
                "needs_profile": False
            }
        label = "/".join(results_by_food.keys())
        return {
            "message": response_message,
            "sections": [
                {"keyword": label, "restaurants": [_format_place(p) for p in top3]}
            ],
            "matched_function": "handle_search_restaurant_query",
            "sources": [],
            "needs_profile": False
        }
