# ===============================================
#    [핸들러] 관계형DB: 개인 맞춤 졸업사정 처리
# ===============================================
# 🚨 GetEquivalentCourse_handler.py 코드 스타일에 맞춰서 리팩토링하기

from typing import Optional
from app.models.schemas import UserProfile
from app.models.schemas import HandlerResponse
from app.services.entity_extractor import entity_extractor
from app.domain.curriculum.service import curriculum_service

# message: 사용자의 질문 원본
# user_profile: 사용자 개인 정보 (학번, 이수과목 등)
def handle_check_graduation_status_query(
    message: str,
    user_profile: Optional[UserProfile] = None  
) -> HandlerResponse:
        
    extracted = entity_extractor.extract_course_info(message)
    
    if extracted['has_enough_info']:
        user_profile = UserProfile(
            admission_year=extracted['admission_year'],
            courses_taken=extracted['courses']
        )
        print(f"✅ UserProfile 자동 생성: {extracted['admission_year']}학번, {len(extracted['courses'])}과목")
    elif extracted['admission_year']:
        user_profile = UserProfile(
            admission_year=extracted['admission_year'],
            courses_taken=[]
        )
        print(f"✅ 입학년도만 있음: {extracted['admission_year']}학번")
    elif user_profile:
        print(f"✅ 기존 UserProfile 사용: {user_profile.admission_year}학번")
    else:
        print("❌ 정보 부족: 안내 메시지 반환")
        return HandlerResponse(
            message="""개인 맞춤 답변을 위해 다음 정보가 필요해요! 😊
 
📅 입학년도: 몇 학번이신가요?
📚 이수한 과목: 학번과 과목명 또는 과목코드를 알려주세요.
   (과목명, 과목코드는 콤마로 구분해 주세요.)
 
💡 예시:
"2024학번이고 컴퓨터과학, 이산수학, 데이터베이스 들었어. 졸업사정 해줘."
또는
"24학번, CS0614, XG0800 들었어"
""",
            matched_function="handle_check_graduation_status_query",
            needs_profile=True
        )
 
    # 과목 정보 없으면 → 개인정보 요청
    if not user_profile.courses_taken:
        print("  → 과목 정보 없음, 개인정보 요청")
        return HandlerResponse(
            message="""개인 맞춤 답변을 위해 다음 정보가 필요해요! 😊
 
📅 입학년도: 몇 학번이신가요?
📚 이수한 과목: 학번과 과목명 또는 과목코드를 알려주세요.
(과목명, 과목코드는 콤마로 구분해 주세요.)
 
💡 예시:
"2024학번이고 컴퓨터과학, 이산수학, 데이터베이스 들었어. 졸업사정 해줘."
또는 "24학번, CS0614, XG0800 들었어"
""",
            matched_function="handle_check_graduation_status_query",
            needs_profile=True
        )
 
    # 과목 정보 있음 → 졸업사정 진행
    print("  → 과목 정보 있음, 졸업사정 처리")
    calculation = curriculum_service.calculate_remaining_credits(user_profile)
 
    if 'error' in calculation:
        return HandlerResponse(
            message=calculation['error'],
            matched_function="handle_check_graduation_status_query",
        )
 
    formatted_info = curriculum_service.format_curriculum_info(calculation)
 
    additional_info = ""
    if any(kw in message for kw in ['과목', '뭐', '어떤', '필수', '남은', '남았']):
        not_taken = curriculum_service.get_required_courses_not_taken(
            user_profile, course_area="전공", requirement_type="전공필수"
        )
        if not_taken:
            formatted_not_taken = curriculum_service.format_not_taken_courses(not_taken)
            additional_info = "\n\n" + formatted_not_taken
 
    return HandlerResponse(
        message=formatted_info + additional_info,
        matched_function="handle_check_graduation_status_query",
        user_profile=user_profile
    )
 