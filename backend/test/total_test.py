"""
1단계: 복합 질문 테스트셋 + Before 측정

역할: 2개 이상의 함수가 필요한 질문 10개를, 지금 구조(라우터가 딱 하나의
      함수만 고름)에 넣어서 어떻게 실패하는지 실측한다.

기대하는 실패 양상:
  - 두 가지 요청 중 하나만 답하고 나머지는 무시
  - 또는 애매한 절충안으로 어설프게 답함
  - 또는 needs_profile 되묻기로 빠져서 아무것도 진행 안 됨

사용법 (backend 폴더에서, 가상환경 활성화 상태로):
    python test/complex_questions_before.py

사전 조건: uvicorn app.main:app --reload 로 서버가 이미 떠 있어야 함
"""
import requests

tests = [
    # GetEquivalentCourse + CheckGraduationStatus
    ("컴퓨터네트워크 대신 정보보호를 들었는데, 이거 졸업 학점으로 인정되는지랑 몇 학점 남았는지 같이 알려줘",
     "동일대체 인정 여부 + 남은 학점 계산 (2개 함수 필요)"),

    # GetEquivalentCourse + GetCurriculum
    ("컴퓨터그래픽스가 요즘 뭘로 바뀌었고, 그 과목이 2024학번 전공필수에 들어가는지 알려줘",
     "동일대체 조회 + 커리큘럼 요건 조회"),

    # CheckGraduationStatus + GetCurriculum
    ("2024학번이고 컴퓨터과학, 이산수학 들었어. 남은 학점 알려주고, 전공선택 리스트도 같이 보여줘",
     "졸업사정 + 교육과정 리스트 (같은 학번 데이터를 두 함수가 각각 씀)"),

    # SearchReviews + GetEquivalentCourse
    ("데이터베이스설계및응용 강의평가 보여주고, 이 과목 대체과목도 있는지 알려줘",
     "강의평가 + 동일대체 조회"),

    # SearchGeneral + CheckGraduationStatus
    ("이번 학기 종강일이 언제인지랑, 저 2024학번인데 몇 학점 남았는지 같이 알려줘",
     "학사일정(general) + 졸업사정 (전혀 다른 DB 소스 2개)"),

    # GetCurriculum + SearchReviews
    ("2024학번 전공필수 과목 중에 자료구조 강의평가 좀 보여줘",
     "커리큘럼 리스트 + 강의평가"),

    # CheckGraduationStatus + SearchGeneral
    ("졸업하려면 몇 학점 더 필요한지랑, 장학금 신청 기간도 알려줘",
     "졸업사정 + 장학금 정보(general)"),

    # GetEquivalentCourse + SearchGeneral
    ("모바일프로그래밍 대체과목 알려주고, 그 과목 담당 교수님 연구실 위치도 알려줘",
     "동일대체 조회 + 연구실 정보(general)"),

    # 3개 이상 (극단적 케이스)
    ("2024학번인데 컴퓨터네트워크 대신 정보보호 들었고, 이거 인정되는지랑 전공필수 리스트, 개강일도 다 알려줘",
     "동일대체 + 졸업사정 + 커리큘럼 + 학사일정 (4개 함수)"),

    # GetEquivalentCourse (역방향) + CheckGraduationStatus
    ("이산수학 옛날 이름이 뭐였는지 알려주고, 2024학번인데 그거 들었다고 하면 졸업 학점 얼마나 남는지 계산해줘",
     "역방향 동일대체 조회 + 졸업사정"),
]

for question, note in tests:
    r = requests.post("http://localhost:8000/chat", json={"message": question})
    data = r.json()

    print("=" * 70)
    print(f"[{note}]")
    print(f"질문: {question}")
    print(f"matched_function: {data.get('matched_function')}")
    print(f"응답 전체:\n{data.get('message', '')}")
    print()