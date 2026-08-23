# 폴더 구조

순천대 챗봇 백엔드(FastAPI) 프로젝트 구조 파악용 문서.

```
backend/
├── app/                        # FastAPI 애플리케이션
│   ├── main.py                 # 앱 진입점 (FastAPI 인스턴스, 라우터 등록)
│   ├── config.py                # 환경변수 설정 (pydantic-settings)
│   │
│   ├── api/                     # API 엔드포인트 (라우터)
│   │   ├── autocomplete.py      # 자동완성
│   │   ├── calendar.py          # 학사일정 API
│   │   ├── faq.py                # FAQ API
│   │   ├── graduation.py        # 졸업사정 API
│   │   └── review_admin.py      # 강의평가 승인 관리 API
│   │
│   ├── chat/                    # 챗봇 라우팅 & 핸들러
│   │   ├── dispatcher.py        # chat() 진입점 - 라우팅 결과에 따라 핸들러로 분기
│   │   ├── routing_connector.py # LLM function calling으로 카테고리 분류 (route())
│   │   ├── routing_schemas.py   # 분류 카테고리 정의 (Pydantic, FUNCTIONS 목록)
│   │   └── handlers/            # 카테고리별 실제 처리 로직
│   │       ├── CheckGraduationStatus_handler.py  # 졸업사정
│   │       ├── GetCurriculum_handler.py          # 교육과정 조회
│   │       ├── GetEquivalentCourse_handler.py    # 동일/대체 과목 조회
│   │       ├── SearchReviews_handler.py          # 강의평가 검색
│   │       └── SearchGeneral_handler.py          # 일반 정보 검색 (벡터DB)
│   │
│   ├── domain/                  # 도메인별 비즈니스 로직 (서비스 계층)
│   │   ├── curriculum/          # 교육과정 계산 (service.py, rules.py=학번별 졸업규칙)
│   │   ├── equivalent_course/   # 동일/대체 과목 서비스
│   │   ├── review/               # 강의평가 검색 서비스 (임베딩+LLM)
│   │   └── vector_search/       # 일반 벡터 검색 서비스 (SentenceTransformer + Supabase RPC)
│   │
│   ├── services/
│   │   └── entity_extractor.py  # 메시지에서 학번/과목코드/과목명 추출 (현재 정규식 기반)
│   │
│   ├── models/
│   │   ├── schemas.py            # API 요청/응답 Pydantic 스키마
│   │   └── session.py            # 사용자 세션 관리 (인메모리, 추후 Redis 전환 예정)
│   │
│   ├── database/
│   │   └── supabase_client.py    # Supabase 클라이언트 싱글톤
│   │
│   └── data/                     # 정적 JSON 데이터 (calendar.json, faq.json)
│
├── data/                         # 임베딩/DB 업로드용 원본 데이터 & 스크립트
│   ├── prepare_data.py           # 엑셀(raw_data) → Supabase 관계형 테이블 업로드
│   ├── create_embeddings.py      # text_data(.txt) → 임베딩 생성 → Supabase documents 테이블 업로드
│   └── text_data/                # 벡터 검색용 원문 텍스트 (학사일정, 도서관, 장학금, 통학버스 등)
│
├── test/                         # 라우팅 정확도 테스트 스크립트 & 결과 csv
│
├── supabase_schema.sql           # Supabase DB 스키마
├── google_sheets_sync.py         # 구글시트 연동 스크립트
├── requirements.txt
├── Dockerfile
└── ANALYSIS.md                   # (기존) 프로젝트 분석 문서
```

## 챗봇 요청 흐름

1. `app/chat/dispatcher.py`의 `chat()` 함수가 진입점.
2. `routing_connector.py`가 `routing_schemas.py`에 정의된 카테고리(FUNCTIONS) 중 하나로 LLM function calling을 통해 분류.
3. 분류 결과(`function_name`)에 따라 `chat/handlers/` 아래 해당 핸들러 호출.
4. 핸들러는 `domain/`의 서비스나 `services/entity_extractor.py`를 이용해 실제 응답 생성.

## 새 카테고리(예: 맛집 추천) 추가 시 건드릴 파일

- `app/chat/routing_schemas.py` — 새 Pydantic 클래스 추가 + `FUNCTIONS`에 등록
- `app/chat/dispatcher.py` — 새 `function_name` 분기 추가
- `app/chat/handlers/` — 새 핸들러 파일 생성
- (데이터 저장 방식에 따라) `app/domain/vector_search/` 또는 `app/services/entity_extractor.py` 참고/확장
