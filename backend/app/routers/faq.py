from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/api/faq",
    tags=["faq"]
)

# JSON 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
JSON_FILE_PATH = BASE_DIR / "data" / "faq.json"


def load_faq_data() -> List[Dict[Any, Any]]:
    """
    faq.json 파일 로드
    """
    # print(f"📂 FAQ JSON 파일 로드: {JSON_FILE_PATH}")
    
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # print(f"📊 전체 FAQ 데이터: {len(data)}개")
        return data
        
    except FileNotFoundError:
        print(f"❌ FAQ JSON 파일을 찾을 수 없습니다: {JSON_FILE_PATH}")
        raise HTTPException(status_code=500, detail="FAQ JSON 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파싱 오류: {str(e)}")
    except Exception as e:
        print(f"❌ JSON 파일 로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파일 로드 중 오류: {str(e)}")


@router.get("/{faq_id}")
async def get_faq_by_id(faq_id: int):
    """
    특정 ID의 FAQ 항목 반환
    """
    try:
        data = load_faq_data()
        
        # ID로 FAQ 찾기
        faq_item = next((item for item in data if item.get('id') == faq_id), None)
        
        if not faq_item:
            print(f"❌ FAQ ID {faq_id}를 찾을 수 없음")
            return {
                "success": False,
                "message": f"FAQ ID {faq_id}를 찾을 수 없습니다.",
                "data": None
            }
        
        # print(f"✅ FAQ {faq_id} 찾음: {faq_item.get('question', 'Unknown')}")
        
        # 자식 질문들도 함께 가져오기
        children = [item for item in data if item.get('parent_id') == faq_id]
        
        return {
            "success": True,
            "data": {
                "id": faq_item.get('id'),
                "question": faq_item.get('question'),
                "answer_type": faq_item.get('answer_type'),
                "answer_content": faq_item.get('answer_content'),
                "parent_id": faq_item.get('parent_id'),
                "title": faq_item.get('title'),
                "children": children
            }
        }
        
    except Exception as e:
        print(f"❌ FAQ 조회 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": None
        }


@router.get("/parent/{parent_id}/children")
async def get_faq_children(parent_id: int):
    """
    특정 부모 ID의 자식 질문들 반환
    """
    try:
        data = load_faq_data()
        
        # 자식 질문들 찾기
        children = [item for item in data if item.get('parent_id') == parent_id]
        
        print(f"✅ FAQ {parent_id}의 자식: {len(children)}개")
        
        return {
            "success": True,
            "data": children,
            "total": len(children)
        }
        
    except Exception as e:
        print(f"❌ 자식 FAQ 조회 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": [],
            "total": 0
        }


@router.get("")
async def get_all_faqs():
    """
    모든 FAQ 항목 반환 (parent_id가 null인 것만)
    """
    try:
        data = load_faq_data()
        
        # 부모 FAQ만 필터링 (parent_id가 null)
        parent_faqs = [item for item in data if item.get('parent_id') is None]
        
        print(f"✅ 부모 FAQ: {len(parent_faqs)}개")
        
        return {
            "success": True,
            "data": parent_faqs,
            "total": len(parent_faqs)
        }
        
    except Exception as e:
        print(f"❌ 전체 FAQ 조회 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": [],
            "total": 0
        }