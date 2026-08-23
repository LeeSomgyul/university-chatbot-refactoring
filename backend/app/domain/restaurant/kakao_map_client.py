"""
카카오맵 API 클라이언트
"""
import requests
from typing import List, Dict, Optional

from app.config import settings

class KakaoMapClient:
    """카카오맵 장소 검색 API 클라이언트"""

    # 카테고리 검색
    BASE_URL = "https://dapi.kakao.com/v2/local/search/category.json"

    # 공유 데이터(API 키가 담긴 인증 정보)
    def __init__(self):
        self.headers = {
            # 카카오 API가 요구하는 인증 형식 KakaoAK bb8232c6...
            "Authorization": f"KakaoAK {settings.kakao_map_rest_key}"
        }

    # (기본값)카테고리 검색
    def search_by_category(
            self,
            latitude: float,
            longitude: float,
            category_code: str = "FD6",
            ## ??
            radius: int = 1000,
            size: int = 15
    )->List[Dict]:
        # 카카오맵 API가 요구하는 파라미터 형식
        params = {
            "category_group_code": category_code,
            "x": longitude,
            "y": latitude,
            "radius": radius,
            "size": size,
            "sort": "distance"
        }

        try:
            # 카카오맵 API 요청 전송
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=5
            )
            # 요청 실패(404/500..) -> 에러 발생 (catch절이 잡을 수 있도록)
            response.raise_for_status()
            data = response.json()
            return data.get("documents",[])
        except requests.exceptions.RequestException as e:
            print(f"카카오맵 API 호출 실패")
            return []

    # (음식 키워드 있는 경우)키워드로 검색
    def search_by_keyword(
            self,
            query: str,
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
            radius: int = 1000
    ) -> List[Dict]:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        # 카카오맵 API가 요구하는 파라미터 형식
        params = {"query": query}

        if latitude and longitude:
            params["y"] = latitude
            params["x"] = longitude
            params["radius"] = radius

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=5
            )
            # 요청 실패(404/500..) -> 에러 발생 (catch절이 잡을 수 있도록)
            response.raise_for_status()
            data = response.json()
            return data.get("documents",[])
        except requests.exceptions.RequestException as e:
            print(f"카카오맵 API 호출 실패")
            return []


kakao_map_client = KakaoMapClient()