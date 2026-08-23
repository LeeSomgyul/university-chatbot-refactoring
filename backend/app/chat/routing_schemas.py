# ===============================================
#             라우터(클래스) 종류 정의
# ===============================================
# - routing_connector.py로 사용자 질문이 들어왔을 때 아래 라우터(클래스)들 중
#   적합한 클래스로 접근
from typing import Optional

from pydantic import BaseModel, Field

# ====== [관계형DB: 졸업사정 처리] ======
class CheckGraduationStatus(BaseModel):
    """
    [설명]
    - 사용자가 지금까지 이수한 과목을 바탕으로 졸업 가능 여부, 남은 학점, 
      미이수 과목을 계산할때 사용

    [예시 질문]
    - 나 졸업할 수 있어?
    - 남은 학점이 뭐야?
    - 나 지금까지 이수한 학점 알려줘
    - 나 들어야하는 남은 과목 알려줘
    - 나 창의교양쪽 학점 부족한데 뭐 더 들어야 하지?

    [참고]
    - 사용자의 학번, 이수한 과목 등 질문마다 필요한 데이터 다름
    - 필수 데이터가 부족하다면 사용자에게 다시 되물어야 함
    """
    pass

# ====== [관계형DB: 교육과정 조회] ======
class GetCurriculum(BaseModel):
    """
    [설명]
    - 특정 학번의 특정 조건(전공필수/전공선택/교양 등)에 해당하는
    과목 목록을 조회

    [예시 질문]
    - 2024학번 전공필수 과목 뭐야?
    - 25학번 교양 필수 알려줘
    - 전공영어1이랑 2중에 뭘 들어야 하지?
    """

    # admission_year: 입학 년도
    admission_year: Optional[int] = Field(
        default=None,
        description="질문에서 언급된 학번(입학년도). 예: '2024학번' -> 2024. 언급 없으면 비워둔다."
    )
    

# ====== [관계형DB: 동일/대체 과목 조회] ======
class GetEquivalentCourse(BaseModel):
    """
    [설명]
    - 특정 과목의 동일/대체 과목 정보 조회
    - 과목명이 바뀌었는지, 대체 과목이 뭔지, 중복/재수강 가능한지 등 물어보기

    [예시 질문]
    - 00과목 바뀐거 있어?
    - 00과목 대신 뭐 들으면 돼?
    - 00과목 학점 인정되는 다른 과목 있어?
    - 00랑 xx랑 같은 과목이야?
    - 00과목 들었는데 xx과목도 들어두 되나?

    [참고]
    - 과목 코드나 과목명, 학번(입학년도)이 필요함
    """

    # course_name: 과목 명 or 과목 코드
    course_name: str = Field(
        description="질문에서 언급된 과목명 원문. 예: '시스템프로그래밍 바뀐거 있어?' -> '시스템프로그래밍'. "
                    "과목코드가 언급된 경우 과목코드를 그대로 넣어도 된다. 예: 'CS0620 대신 뭐 들어?' -> 'CS0620'"
    )


# ====== [관계형DB: 강의평가 검색] ======
class SearchReviews(BaseModel):
    """
    [설명]
    - 특정 강의/교수의 수강 후기 열람
    - 강의 평가 작성 및 작성법 안내

    [예시 질문]
    - 자료구조 강의평가 보여줘
    - 김철수 교수님 강의 후기 있어?
    - 알고리즘 수업 후기 알려줘
    - 강의평가 작성하고싶어

    [참고]
    - 과목 코드나 과목명 필요함 (필수는 아닐 수 있음. 함수마다 다를듯)
    """
    pass

# ====== [벡터DB: 일반 정보 검색] ======
class SearchGeneral(BaseModel):
    """
    [설명]
    - 학사일정, 도서관, 장학금, 통학버스, 연락처, 실험실 등
      문장으로 저장되어져있는 정보 검색

    [예시 질문]
    - 2025년 1학기 개강일 언제야?
    - 도서관 몇시까지 운영하지?
    - 장학금 신청 기간이 언제야?
    - 통학버스 시간표 알려줘
    - 인공지능 연구실 교수님 누구야?
    """
    pass

# ======= [카카오맵 REST API 호출] 식도락 검색 ======
class SearchRestaurant(BaseModel):
    """
    [설명]
    - 학교 근처 음식점, 카페, 맛집 추천 요청 처리

    [예시 질문]
    - 정문 근처 떡볶이 맛집 추천해줘
    - 맛집 추천해줘
    - 순천대 근처 카페 알려줘

    [참고]
    - 위치나 음식 종류가 언급 안 될 수도 있음 (그럴 땐 null로 둔다)
    """
    location_keyword: Optional[str] = Field(
        None, description="사용자가 언급한 구체적 위치. 정문, 후문, 학생회관 등. 언급 없으면 null"
    )
    food_keyword: Optional[str] = Field(
        None, description="사용자가 언급한 구체적 음식명이나 카테고리. 떡볶이, 분식, 중식 등. 언급 없으면 null"
    )
    message: str = Field(
        None, description="사용자의 원본 메시지"
    )


# ====== [LLM 에게 전달할 전체 함수 목록] ======
FUNCTIONS = [
    CheckGraduationStatus,
    GetCurriculum,
    GetEquivalentCourse,
    SearchReviews,
    SearchGeneral,
    SearchRestaurant,
]

# 다른 파일에서 함수 쓸 수 있도록 "키:값" 형식으로 변경
# 예) {"CheckGraduationStatus":CheckGraduationStatus, ...반복}
FUNCTIONS_MAP = {cls.__name__: cls for cls in FUNCTIONS}
