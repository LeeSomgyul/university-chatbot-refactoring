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


from typing import Optional, List
from app.domain.restaurant.kakao_map_client import kakao_map_client
from app.domain.restaurant.service import match_by_review_query, attach_review_summary, format_place, \
    extract_location_keyword, resolve_location, augment_food_keywords, detect_combine_mode
from app.models.schemas import HandlerResponse



# 리뷰 기반 흐름
def _handle_review_based_search(location: dict, final_location_keyword: Optional[str], review_query: str,  exclude_urls: Optional[List[str]] = None,)-> HandlerResponse:
    candidates = kakao_map_client.search_by_category(
        latitude=location["latitude"],
        longitude=location["longitude"],
        category_code="FD6"
    )

    if exclude_urls:
        candidates = [p for p in candidates if p.get('place_url') not in exclude_urls]

    # 후보 => 벡터 유사도 매칭 => 임계값 넘는 장소들 정렬하여 반환
    matched = match_by_review_query(candidates, review_query)

    # 기본위치 안내문구 준비
    if location["used_default"]:
        response_message = f"순천대 본부 기준으로 맛집을 찾아드렸어요! "
    elif final_location_keyword:
        response_message = f"{final_location_keyword} 근처 맛집을 찾아드렸어요! "
    else:
        response_message = f"근처 맛집을 찾아드렸어요! "


    if not matched:
        top3 = candidates[:3]
        shown_urls = [p.get('place_url') for p in top3]
        return HandlerResponse(
            message=f"'{review_query}' 관련 리뷰를 찾지 못했어요. 대신 {response_message}",
            sections=[{"keyword": "전체", "restaurants": [attach_review_summary(p) for p in top3]}],
            matched_function="handle_search_restaurant_query",
            last_restaurant_search={
                "location_keyword": final_location_keyword,
                "food_keyword": None,
                "review_query": review_query,
                "shown_place_urls": shown_urls,
            }
        )
    top3 = matched[:3]
    restaurants = []
    for similarity, place, review_content in top3:
        formatted = format_place(place)
        formatted['review_summary'] = review_content
        restaurants.append(formatted)
    shown_urls = [r.get('url') for r in restaurants]
    print(f"f====================={shown_urls}")
    return HandlerResponse(
        message=f"'{review_query}' 관련 리뷰의 {response_message}",
        sections=[{"keyword": review_query, "restaurants": restaurants}],
        matched_function="handle_search_restaurant_query",
        last_restaurant_search={
            "location_keyword": final_location_keyword,
            "food_keyword": None,
            "review_query": review_query,
            "shown_place_urls": shown_urls,
        }
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
        exclude_urls: Optional[List[str]] = None,
)-> HandlerResponse:
    # =========1.위치 추출=============
    # 위치는 kiwi로 우선 추출
    kiwi_location = extract_location_keyword(message)
    # Kiwi 우선, 안 되면 LLM 값 폴백
    final_location_keyword = kiwi_location or location_keyword

    if kiwi_location:
        print(f"[LOCATION] Kiwi 매칭 성공: {kiwi_location}")
    elif location_keyword:
        print(f"[LOCATION] Kiwi 매칭 실패, LLM 폴백값 사용: {location_keyword}")
    else:
        print(f"[LOCATION] Kiwi/LLM 둘 다 실패, 기본값 사용 예정")

    # 좌표 추출
    location = resolve_location(final_location_keyword)

    # 위치 기본값도 매칭 못했다면
    if location["latitude"] is None:
        return HandlerResponse(
            message="위치 정보를 찾을 수 없어요. 다시 시도해주세요. ",
            matched_function="handle_search_restaurant_query",
            sources=[],
            user_profile=None,
            needs_profile=False,
            sections=[],
            restaurants=[],
        )

    # =========리뷰 키워드별 카카오맵 검색=============
    if review_query:
        return _handle_review_based_search(location, final_location_keyword, review_query,exclude_urls)

    # =========2. 음식키워드별 카카오맵 검색=============
    """
        음식 키워드가 있는 경우:
            음식명(예: "떡볶이")으로 키워드 검색
        음식 키워드가 없는 경우:
            좌표 기반으로 "음식점 전체"(FD6) 카테고리 검색
    """

    # ── 음식 키워드 / combine_mode 보정 ──
    food_keyword = augment_food_keywords(message, food_keyword)
    combine_mode = detect_combine_mode(message, combine_mode)

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

    if exclude_urls:
        results_by_food = {
            kw: [r for r in results if r.get('place_url') not in exclude_urls]
            for kw, results in results_by_food.items()
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
        response_message = f"순천대 본부 기준으로 {food_note}맛집을 찾아드렸어요! "
    elif final_location_keyword:
        response_message = f"{final_location_keyword} 근처 {food_note}맛집을 찾아드렸어요! "
    else:
        response_message = f"근처 {food_note}맛집을 찾아드렸어요! "

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
                "restaurants": [attach_review_summary(p) for p in top3]
            })
        if not has_any_result:
            return HandlerResponse(
                message= "근처에서 해당 유형의 장소를 찾을 수 없습니다. ",
                matched_function= "handle_search_restaurant_query",
            )
        shown_urls = [r.get('url') for s in sections for r in s['restaurants']]
        return HandlerResponse(
            message= response_message,
            sections= sections,
            matched_function= "handle_search_restaurant_query",
            last_restaurant_search={
                "location_keyword": final_location_keyword,
                "food_keyword": food_keyword,
                "review_query": None,
                "shown_place_urls": shown_urls,
            }
        )
    # # and이거나 단일 키워드: 기존처럼 통합 응답
    else:
        all_results = [r for results in results_by_food.values() for r in results]
        top3 = all_results[:3]
        if not top3:
            return HandlerResponse(
                message= "근처에서 해당 유형의 장소를 찾을 수 없습니다. ",
                matched_function= "handle_search_restaurant_query",
            )
        label = "/".join(results_by_food.keys())
        restaurant = [attach_review_summary(p) for p in top3]
        shown_urls = [r.get('url') for r in restaurant]
        return HandlerResponse(
            message= response_message,
            sections= [
                {"keyword": label,"restaurants": restaurant}
            ],
            matched_function= "handle_search_restaurant_query",
            last_restaurant_search={
                "location_keyword": final_location_keyword,
                "food_keyword": food_keyword,
                "review_query": None,
                "shown_place_urls": shown_urls,
            }
        )