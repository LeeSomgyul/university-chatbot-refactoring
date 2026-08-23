# ===============================================
#        [핸들러] 관계형DB: 교육과정 조회
# ===============================================

from typing import Dict, Any, Optional
from app.services.entity_extractor import entity_extractor
from app.database.supabase_client import supabase
from app.models.schemas import HandlerResponse


def handle_curriculum_query(
    message: str,
    admission_year: Optional[int] = None
) -> HandlerResponse:
    if admission_year is None:
        extracted = entity_extractor.extract_course_info(message)
        admission_year = extracted.get('admission_year')

    if admission_year is None:
        return HandlerResponse(
            message="""교육과정 정보를 알려드리려면 입학년도가 필요해요! 😊

몇 학번이신가요?

💡 예시:
"2024학번 전공필수 뭐야?"
"25학번 교양 필수 알려줘"
""",
            matched_function="handle_curriculum_query",
            needs_profile=True
        )

    req_info = _extract_requirement_type(message)

    if req_info['type']:
        return _handle_requirement_list_query(admission_year, req_info['area'], req_info['type'])

    return HandlerResponse(
        message=f"""{admission_year}학번 어떤 과목 정보를 알려드릴까요? 😊

1️⃣ 전공필수 - 꼭 들어야 하는 전공 과목
2️⃣ 전공선택 - 선택할 수 있는 전공 과목
3️⃣ 교양 - 교양 필수 과목

💡 예시:
"{admission_year}학번 전공필수 뭐야?"
"{admission_year}학번 교양 필수 알려줘"
""",
        matched_function="handle_curriculum_query"
    )


# ===== 내부 유틸리티 =====

def _handle_requirement_list_query(
    admission_year: int,
    course_area: str,
    requirement_type: str
) -> HandlerResponse:
    """요건별 전체 과목 리스트 반환"""
    try:
        result = supabase.table('curriculums') \
            .select('*') \
            .eq('admission_year', admission_year) \
            .eq('course_area', course_area) \
            .eq('requirement_type', requirement_type) \
            .order('grade').order('semester').order('course_code') \
            .execute()

        if not result.data:
            available_result = supabase.table('curriculums') \
                .select('requirement_type') \
                .eq('admission_year', admission_year) \
                .eq('course_area', course_area) \
                .execute()
            available_types = list(set([r['requirement_type'] for r in available_result.data]))

            message = f"{admission_year}학번에는 '{requirement_type}' 요건이 없어요. 😥\n\n"
            if available_types:
                message += f"💡 {admission_year}학번 {course_area} 요건:\n"
                for req_type in sorted(available_types):
                    message += f"  • {req_type}\n"
                message += "\n위 요건 중 하나를 선택해서 질문해주세요!"
            else:
                message += f"{admission_year}학번 {course_area} 정보를 찾을 수 없어요."

            return HandlerResponse(
                message=message,
                matched_function="handle_curriculum_query"
            )

        seen = set()
        unique_courses = []
        for course in result.data:
            code = course['course_code']
            if code not in seen:
                seen.add(code)
                unique_courses.append(course)

        print(f"  총 {len(result.data)}개 → 중복 제거 후 {len(unique_courses)}개")

        answer = f"{admission_year}학번 {requirement_type} 과목 목록이에요!\n\n"
        current_grade = None
        for course in unique_courses:
            grade = course.get('grade')
            semester = course.get('semester')
            if grade != current_grade:
                current_grade = grade
                answer += f"\n🧑‍🎓 {grade}학년\n"
            answer += f"  • {course['course_code']} {course['course_name']} ({course['credit']}학점)"
            if semester:
                answer += f" - {semester}학기 권장"
            answer += "\n"

        total_courses = len(unique_courses)
        total_credits = sum(c['credit'] for c in unique_courses)

        if '선택' in requirement_type:
            required_credits = _get_required_credits(admission_year, requirement_type)
            if required_credits:
                answer += f"\n💡 총 {total_courses}개 과목 ({total_credits}학점) 중 선택하여 {required_credits}학점을 채우면 돼요!"
            else:
                answer += f"\n💡 총 {total_courses}개 과목 ({total_credits}학점) 중 선택하여 이수하면 돼요!"
        else:
            answer += f"\n💡 총 {total_courses}개 과목, {total_credits}학점 모두 이수해야 해요!"

        return HandlerResponse(
            message=answer,
            matched_function="handle_curriculum_query"
        )

    except Exception as e:
        print(f"❌ 요건 조회 실패: {e}")
        import traceback
        traceback.print_exc()
        return HandlerResponse(
            message="죄송해요, 과목 정보를 가져오는 중 오류가 발생했어요. 😥",
            matched_function="handle_curriculum_query"
        )


def _extract_requirement_type(message: str) -> Dict[str, str]:
    """메시지에서 요건 타입 추출"""
    req_type = None
    course_area = None

    if '전필' in message or '전공필수' in message:
        req_type, course_area = '전공필수', '전공'
    elif '전선' in message or '전공선택' in message:
        req_type, course_area = '전공선택', '전공'
    elif '교필' in message or '교양필수' in message:
        req_type, course_area = '공통교양', '교양'
    elif '교선' in message or '교양선택' in message:
        req_type, course_area = '교양선택', '교양'
    elif '기초교양' in message or '기초' in message:
        req_type, course_area = '기초교양', '교양'
    elif '심화교양' in message or '심화' in message:
        req_type, course_area = '심화교양', '교양'
    elif '창의교양' in message or '창의' in message:
        req_type, course_area = '창의교양', '교양'
    elif '교양' in message:
        req_type, course_area = '공통교양', '교양'

    return {'type': req_type, 'area': course_area}


def _get_required_credits(admission_year: int, requirement_type: str) -> Optional[int]:
    """요건별 필요 학점 반환 - DB에서 조회"""
    try:
        result = supabase.table('graduation_requirements') \
            .select('required_credits') \
            .eq('admission_year', admission_year) \
            .eq('requirement_type', requirement_type) \
            .execute()
        if result.data:
            return result.data[0]['required_credits']
        print(f"⚠️ {admission_year}학번에는 {requirement_type} 정보가 없음")
        return None
    except Exception as e:
        print(f"❌ 필요 학점 조회 실패: {e}")
        return None