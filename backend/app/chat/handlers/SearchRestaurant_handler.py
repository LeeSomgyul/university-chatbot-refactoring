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

from typing import Dict, Any, Optional

from app.database.supabase_client import supabase
from app.domain.restaurant.kakao_map_client import kakao_map_client
from app.models.schemas import HandlerResponse

DEFAULT_LOCATION_KEYWORD = "순천대"

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
        return {"latitude": default['latitude'], "longitude": default['longitude'], "used_default": False}

    # 기본값이 db에 존재하지 않는다면
    return {"latitude": None, "longitude": None, "used_default": True}

# 주메서드?
def handle_search_restaurant_query(
        location_keyword: Optional[str] = None,
        food_keyword: Optional[str] = None
)-> HandlerResponse:
    # 위치 호출
    location = _resolve_location(location_keyword)

    # 위치 기본값도 매칭 못했다면
    if location["latitude"] is None:
        return HandlerResponse(
            message="위치 정보를 찾을 수 없어요. 다시 시도해주세요. 😥",
            matched_function="handle_search_restaurant_query"
        )

    # 카카오맵 검색(음식 키워드 있음,없음에 따라 분기)
    """
        음식 키워드가 있는 경우:
            음식명(예: "떡볶이")으로 키워드 검색
        음식 키워드가 없는 경우:
            좌표 기반으로 "음식점 전체"(FD6) 카테고리 검색
    """
    if food_keyword:
        results = kakao_map_client.search_by_keyword(food_keyword)
    else:
        results = kakao_map_client.search_by_category(
            latitude=location["latitude"],
            longitude=location["longitude"],
            category_code="FD6"
        )

    # 검색결과가 없는 경우
    if not results:
        return HandlerResponse(
            message="근처에서 해당 유형의 장소를 찾을 수 없습니다. 😥",
            matched_function="handle_search_restaurant_query"
        )

    # 결과 3개 자르기
    top3 = results[:3]

    # 기본위치 안내문구 준비
    if location["used_default"]:
        message = "순천대 본부 기준으로 찾아드렸어요! 📍"
    elif location_keyword:
        message = f"{location_keyword} 근처 맛집을 찾아드렸어요! 😊"
    else:
        message = "근처 맛집을 찾아드렸어요! 😊"

    # 결과 3개를 딕셔너리 리스트로 변환
    restaurants = []
    for place in top3:
        restaurants.append({
            "name": place.get('place_name'),
            "address": place.get('road_address_name') or place.get('address_name'),
            "url": place.get('place_url'),
            "phone": place.get('phone'),
            "category": place.get('category_name').split('>')[-1].strip(),
        })

    # 최종 응답
    return HandlerResponse(
        message=message,
        restaurants=restaurants,
        matched_function="handle_search_restaurant_query"
    )