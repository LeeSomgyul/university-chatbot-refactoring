"""
졸업사정 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
#from app.services.curriculum_service import curriculum_service
from app.services.curriculum_service_optimized import curriculum_service_optimized as curriculum_service
from app.services.equivalent_course_service import equivalent_course_service
from app.models.schemas import UserProfile, CourseInput


router = APIRouter(
    prefix="/api/graduation",
    tags=["graduation"]
)


# ===== Request/Response 스키마 =====

class CalculateRequest(BaseModel):
    """남은 학점 계산 요청"""
    admission_year: int
    courses_taken: List[CourseInput]
    
    class Config:
        json_schema_extra = {
            "example": {
                "admission_year": 2024,
                "courses_taken": [
                    {
                        "course_code": "CS0614",
                        "course_name": "컴퓨터과학",
                        "credit": 3,
                        "course_area": "전공",
                        "requirement_type": "전공필수"
                    }
                ]
            }
        }


class NotTakenRequest(BaseModel):
    """미이수 필수 과목 조회 요청"""
    admission_year: int
    courses_taken: List[CourseInput]
    course_area: Optional[str] = None  # "전공" or "교양"
    requirement_type: Optional[str] = None  # "전공필수", "공통교양" 등


# ===== API 엔드포인트 =====

@router.post("/calculate")
async def calculate_remaining_credits(request: CalculateRequest):
    """
    남은 학점 계산
    
    사용자가 이수한 과목을 바탕으로 졸업까지 남은 학점을 계산합니다.
    """
    try:
        user_profile = UserProfile(
            admission_year=request.admission_year,
            courses_taken=request.courses_taken
        )
        
        result = curriculum_service.calculate_remaining_credits(user_profile)
        
        return {
            "success": True,
            "data": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/not-taken")
async def get_not_taken_courses(request: NotTakenRequest):
    """
    미이수 필수 과목 조회
    
    아직 이수하지 않은 필수 과목 목록을 반환합니다.
    """
    try:
        user_profile = UserProfile(
            admission_year=request.admission_year,
            courses_taken=request.courses_taken
        )
        
        not_taken = curriculum_service.get_required_courses_not_taken(
            user_profile,
            course_area=request.course_area,
            requirement_type=request.requirement_type
        )
        
        # 포맷팅된 텍스트도 함께 반환
        formatted = curriculum_service.format_not_taken_courses(
            not_taken,
            title=f"미이수 {'전공' if request.course_area == '전공' else '교양'} 필수 과목"
        )
        
        return {
            "success": True,
            "data": {
                "courses": not_taken,
                "formatted": formatted
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requirements/{admission_year}")
async def get_requirements(
    admission_year: int,
    course_area: Optional[str] = None,
    requirement_type: Optional[str] = None
):
    """
    입학년도별 졸업 요건 조회
    
    특정 입학년도의 졸업 요건을 반환합니다.
    """
    try:
        requirements = curriculum_service.get_graduation_requirements(admission_year)
        
        # 필터링
        if course_area:
            requirements = [r for r in requirements if r.get('course_area') == course_area]
        
        if requirement_type:
            requirements = [r for r in requirements if r.get('requirement_type') == requirement_type]
        
        return {
            "success": True,
            "data": requirements
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_code}")
async def get_course_info(course_code: str, admission_year: int):
    """
    과목 정보 조회
    
    특정 과목의 상세 정보를 반환합니다.
    """
    try:
        course_info = curriculum_service._get_course_info(admission_year, course_code)
        
        if not course_info:
            raise HTTPException(status_code=404, detail="과목을 찾을 수 없습니다.")
        
        # 동일대체 교과목 정보 추가
        course_info['alternative_codes'] = curriculum_service._get_alternative_codes(
            course_code,
            admission_year
        )
        
        return {
            "success": True,
            "data": course_info
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equivalent/{course_code}")
async def get_equivalent_course(course_code: str):
    """
    동일대체 교과목 조회
    
    구 과목 코드로 신 과목 코드를 찾거나, 그 반대를 수행합니다.
    """
    try:
        # 구 → 신
        equiv = equivalent_course_service.get_equivalent_course(course_code)
        
        # 신 → 구 (향후 변경)
        future_changes = curriculum_service._get_alternative_codes(course_code)
        
        return {
            "success": True,
            "data": {
                "old_to_new": equiv,  # 구 → 신
                "future_changes": future_changes  # 향후 변경
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    헬스 체크
    """
    return {"status": "ok"}