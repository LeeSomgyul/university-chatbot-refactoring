# backend/app/routers/autocomplete.py

from fastapi import APIRouter, Query, HTTPException
import json
from pathlib import Path
from typing import List, Dict, Any

router = APIRouter(
    prefix="/api/autocomplete",
    tags=["autocomplete"]
)

# JSON 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
JSON_FILE_PATH = BASE_DIR / "data" / "faq.json"

# 캐시 변수
_cached_data: List[Dict[Any, Any]] = None


def load_faq_data() -> List[Dict[Any, Any]]:
    """
    JSON 파일을 로드하고 autocomplete=true인 항목만 필터링
    """
    global _cached_data
    
    # 캐시가 있으면 캐시된 데이터 반환
    if _cached_data is not None:
        # print("✅ 캐시된 데이터 사용")
        return _cached_data
    
    # print(f"📂 JSON 파일 로드: {JSON_FILE_PATH}")
    
    try:
        # JSON 파일 읽기
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # print(f"📊 전체 데이터: {len(data)}개")
        
        # autocomplete=true인 항목만 필터링
        filtered_data = [item for item in data if item.get('autocomplete') == True]
        
        # print(f"✅ autocomplete=true 항목: {len(filtered_data)}개")
        
        # 캐시 저장
        _cached_data = filtered_data
        
        return filtered_data
        
    except FileNotFoundError:
        print(f"❌ JSON 파일을 찾을 수 없습니다: {JSON_FILE_PATH}")
        raise HTTPException(status_code=500, detail="JSON 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파싱 오류: {str(e)}")
    except Exception as e:
        print(f"❌ JSON 파일 로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파일 로드 중 오류: {str(e)}")


@router.get("/search")
async def search_autocomplete(
    q: str = Query(..., description="검색어"),
    limit: int = Query(10, ge=1, le=50, description="결과 개수 제한")
):
    """
    검색어를 기반으로 자동완성 제안 반환
    """
    try:
        data = load_faq_data()
        
        # 빈 검색어면 빈 배열 반환
        if not q or q.strip() == "":
            return {
                "success": True,
                "data": {
                    "suggestions": [],
                    "total": 0
                }
            }
        
        query = q.strip().lower()
        
        # question 또는 title에 검색어가 포함된 항목 필터링
        matched_items = []
        for item in data:
            question = item.get('question', '').lower()
            title = item.get('title', '').lower()
            
            if query in question or query in title:
                matched_items.append(item)
                
                # limit에 도달하면 중단
                if len(matched_items) >= limit:
                    break
        
        return {
            "success": True,
            "data": {
                "suggestions": matched_items,
                "total": len(matched_items)
            }
        }
        
    except Exception as e:
        print(f"❌ 검색 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": {
                "suggestions": [],
                "total": 0
            }
        }


@router.get("/children/{parent_id}")
async def get_children_by_parent_id(parent_id: int):
    """
    parent_id로 자식 질문들 가져오기
    """
    try:
        # 전체 데이터 로드 (autocomplete 필터 없이)
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        # parent_id가 일치하는 항목들 찾기
        children = [item for item in all_data if item.get('parent_id') == parent_id]
        
        # print(f"✅ parent_id={parent_id}인 자식 항목: {len(children)}개")
        
        return {
            "success": True,
            "data": {
                "children": children,
                "total": len(children)
            }
        }
        
    except Exception as e:
        print(f"❌ 자식 항목 조회 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": {
                "children": [],
                "total": 0
            }
        }