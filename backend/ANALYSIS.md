# Backend 구조 분석 (재파악용)

> 읽기 전용 분석 문서. 코드 수정 없음. 분석 시점: 2026-08-18, 커밋 `c0d813a` 기준 (전체 히스토리 2커밋: `369150f` 초기 커밋 → `c0d813a` 초기 세팅).
> frontend, venv, `__pycache__` 제외.

---

## 1. 디렉토리 구조

```
backend/
├── app/
│   ├── main.py                 # FastAPI 앱 진입점, 라우터 등록, /chat 엔드포인트
│   ├── config.py                # 환경변수 → Settings 객체 (pydantic-settings)
│   ├── data/                    # 정적 JSON 데이터 (FAQ, 학사일정) — DB 아님
│   │   ├── faq.json
│   │   └── calendar.json
│   ├── database/
│   │   └── supabase_client.py   # Supabase 클라이언트 싱글톤
│   ├── models/
│   │   ├── schemas.py           # Pydantic 요청/응답 스키마
│   │   └── session.py           # 인메모리 세션 저장소 (싱글톤)
│   ├── routers/                 # FAQ/자동완성/학사일정 API (다른 팀원 담당, JSON 파일 기반)
│   │   ├── autocomplete.py
│   │   ├── calendar.py
│   │   └── faq.py
│   ├── routes/                  # 챗봇 핵심 도메인 API (본인 담당, DB 기반)
│   │   ├── graduation.py        # 졸업사정 REST API
│   │   └── review_admin.py      # 강의평가 승인/거부 관리 API
│   ├── rules/
│   │   └── graduation_rules.py  # 학번별 졸업 규칙(overflow 등) 하드코딩 설정
│   └── services/                # 비즈니스 로직 9개 파일 (2번 항목 참고)
├── data/                        # (app/ 밖) 데이터 적재/임베딩 생성 스크립트 + 원본 텍스트
│   ├── create_embeddings.py
│   ├── prepare_data.py
│   └── text_data/                # 벡터 검색용 원본 .txt (===CATEGORY/===TITLE 포맷)
├── google_sheets_sync.py        # 구글폼 응답(구글시트) → pending_reviews 동기화 스크립트
├── requirements.txt
├── Dockerfile
├── supabase_schema.sql          # DB 스키마 정의(SQL)
├── .env.example
├── .dockerignore / .gitignore
```

**주의**: `app/data/` (JSON, FAQ·캘린더용)와 `data/` (프로젝트 루트, 텍스트/스크립트용)는 이름이 비슷하지만 완전히 다른 폴더입니다. 전자는 런타임에 라우터가 읽는 정적 파일, 후자는 배치 스크립트 + 원본 데이터입니다.

---

## 2. `app/services/` 9개 파일 역할과 호출 관계

| 파일 | 역할 | 실사용 여부 |
|---|---|---|
| `chatbot.py` | 전체 챗봇 로직 통합 (질문 분류 → 각 핸들러 라우팅) | ✅ `main.py`가 호출하는 핵심 엔트리 |
| `query_router.py` | 질문을 `curriculum`/`general`/`review`로 분류 (LLM 우선, 실패 시 키워드 폴백) | ✅ `chatbot.py`가 최초 호출 |
| `entity_extractor.py` | 메시지에서 학번/과목코드/과목명 추출, DB에서 과목 상세 조회 | ✅ `chatbot.py`가 curriculum 분기에서 호출 |
| `vector_service.py` | 일반 정보 벡터 검색 (`documents` 테이블, `match_documents` RPC) | ✅ `chatbot.py`의 general 핸들러가 호출 |
| `review_service.py` | 강의평가 벡터 검색 (`course_reviews` 테이블, `match_course_reviews` RPC) + LLM 기반 교수/강의명 추출 | ✅ `chatbot.py`의 review 핸들러가 호출 |
| `curriculum_service_optimized.py` | 졸업사정 계산(전공/교양 학점 매칭, overflow 처리), **캐싱 적용** | ✅ `chatbot.py`, `app/routes/graduation.py` 둘 다 이 버전을 사용 |
| `curriculum_service.py` | 위와 동일 로직의 **캐싱 없는 구버전** | ⚠️ **죽은 코드** (아래 참고) |
| `equivalent_course_service_optimized.py` | 동일대체 과목 판정, **앱 시작 시 전체를 메모리에 로드해 캐싱** | ✅ `curriculum_service_optimized.py`가 내부적으로 사용 |
| `equivalent_course_service.py` | 위와 동일 로직의 **매 호출마다 DB 조회하는 구버전** | ⚠️ 부분적으로 살아있음 (아래 참고) |

### 호출 관계 다이어그램

```
main.py (/chat)
  └─ chatbot.py (SchoolChatbot.chat)
       ├─ query_router.classify()               → curriculum/general/review 분류
       ├─ query_router.needs_user_profile()      → 계산만 하고 실제로 사용 안 됨 (버그, 9번 참고)
       ├─ [curriculum] entity_extractor.extract_course_info()
       │    └─ curriculum_service_optimized
       │         ├─ get_graduation_requirements() / get_selectable_courses()  (자체 캐시)
       │         └─ equivalent_course_service_optimized.is_equivalent()       (자체 캐시)
       ├─ [general]   vector_service.search()     → documents 테이블 (벡터)
       └─ [review]    review_service.search_reviews() / extract_professor_and_course()

app/routes/graduation.py (REST API, /api/graduation/*)
  ├─ curriculum_service_optimized  (chatbot.py와 동일 인스턴스 사용)
  └─ equivalent_course_service     ← 비최적화 구버전을 직접 import!
```

### 이름 겹치는 페어 확인 결과

**`curriculum_service.py` vs `curriculum_service_optimized.py`**
- `chatbot.py` 9번째 줄에 `from app.services.curriculum_service import curriculum_service`가 있지만 **주석 처리**되어 있고, 바로 다음 줄에서 `curriculum_service_optimized`를 `curriculum_service`라는 이름으로 alias import해서 사용합니다.
- `app/routes/graduation.py`도 동일한 패턴(주석 + optimized를 alias)입니다.
- 리포지토리 전체에서 `curriculum_service.py`(비최적화)를 실제로 import하는 곳은 **없습니다**. 즉 `curriculum_service.py`는 완전한 죽은 코드입니다. (자기 자신 안에서만 참조됨)
- 이 파일 안에는 실사용되지 않았기 때문에 발견되지 않은 버그도 있습니다 (`_get_alternative_codes`의 `return`이 for 루프 안에 들여쓰기 되어 있어 첫 번째 행만 처리하고 반환됨 — 9번 항목 참고).

**`equivalent_course_service.py` vs `equivalent_course_service_optimized.py`**
- `curriculum_service_optimized.py`(실사용 중)는 `equivalent_course_service_optimized`만 사용합니다.
- 하지만 `app/routes/graduation.py`는 `curriculum_service_optimized`를 쓰면서 **동시에** `equivalent_course_service`(비최적화, DB 매번 조회)를 별도로 import해서 `/api/graduation/equivalent/{course_code}` 엔드포인트에 사용합니다.
- 즉 `equivalent_course_service.py`는 죽은 코드가 아니라 **REST API 한 곳에서만 쓰이는 부분 사용 코드**입니다. 챗봇 대화 흐름(`/chat`)에서는 전혀 쓰이지 않습니다.
- 두 서비스는 로직상 동일한 결과를 내야 하지만, optimized 버전은 **앱 시작 시 1회 메모리 캐시**(`load_all_equivalents()`가 모듈 하단에서 즉시 호출됨) 방식이라 런타임 중 `equivalent_courses` 테이블이 바뀌어도 서버 재시작 전까지 반영되지 않는 반면, 비최적화 버전은 항상 DB를 직접 조회합니다. 두 경로가 서로 다른 신선도(freshness)를 가진 채 공존하는 셈입니다.

**참고**: 사용자가 채팅으로 "이 과목 대신 뭐 들을 수 있어?" 같은 동일대체 질문을 하면, `chatbot.py`는 이를 `equivalent_course_service`로 보내지 않고 **`general`(벡터 검색, `same_subject.txt` 데이터)로 우회**시킵니다. `equivalent_course_service`류는 졸업사정 계산 시 과목 매칭(`is_equivalent`)과 REST API 조회용으로만 쓰이고, 사용자 대화의 "동일대체 질문"은 별도 텍스트 데이터로 답변됩니다.

---

## 3. `app/routers/` vs `app/routes/`

`main.py` 주석에 이유가 명시되어 있습니다:
```python
# 챗봇 라우터 (당신 것)
app.include_router(graduation.router)
app.include_router(review_admin.router)
# FAQ/자동완성 라우터 (다른 팀원 것)
app.include_router(autocomplete_router)
app.include_router(calendar_router)
app.include_router(faq_router)
```

- **`app/routes/`** — 챗봇 핵심 도메인(작성자 본인 담당), Supabase DB 테이블(`curriculums`, `graduation_requirements`, `equivalent_courses`, `pending_reviews`, `course_reviews`)에 의존.
  - `graduation.py`: `/api/graduation/*` — 남은 학점 계산, 미이수 과목 조회, 요건 조회, 동일대체 조회
  - `review_admin.py`: `/admin/reviews/*` — 강의평가 승인/거부/삭제/통계 (구글폼 → pending_reviews로 들어온 데이터 관리)
- **`app/routers/`** — 다른 팀원이 만든 FAQ/자동완성/학사일정 기능, DB가 아니라 **`app/data/*.json` 정적 파일**을 직접 읽어서 서빙.
  - `autocomplete.py`: `/api/autocomplete/*`
  - `calendar.py`: `/api/calendar/*`
  - `faq.py`: `/api/faq/*`

즉 이름 차이는 실수가 아니라 **팀원별 작업 영역을 구분하려는 의도적 분리**로 보이며(주석에 명시), 데이터 소스도 DB vs JSON 파일로 확실히 다릅니다. 기능적으로 병합 못 할 이유는 없지만, 현재는 관례적으로 나뉜 상태입니다.

---

## 4. `app/rules/graduation_rules.py`

학번(입학년도)별로 다른 **졸업 요건 "overflow" 규칙**을 하드코딩한 설정 파일입니다. DB(`graduation_requirements`, `curriculums`)에는 담기 어려운 예외적 계산 로직을 코드로 표현합니다.

- `GRADUATION_RULES` 딕셔너리에 `2024`, `2025` 두 학번만 정의되어 있음.
- 각 학번마다:
  - `overflow`: 특정 과목군을 필요 이상 이수했을 때 초과분을 다른 교양 트랙(심화교양/창의교양)으로 넘겨 인정하는 규칙. 두 가지 타입:
    - `course_selection`: 택1 과목을 여러 개 들으면 초과분 인정 (예: 글로벌의사소통)
    - `track_based`: 트랙 필수 학점을 초과 이수하면 최대치까지 인정 (예: 핵심교양 8학점 초과분)
  - `track_names`: 학번별로 다르게 불리는 교양 트랙 이름 매핑 (2024는 "심화교양", 2025는 "창의교양" 등)
  - `notes`: 사람이 읽는 참고용 설명 (코드에서 사용 안 됨)
- `get_rules(admission_year)`: 해당 학번 규칙이 없으면 **2024학번 규칙으로 폴백** (경고 출력).
- `get_overflow_target_key(admission_year)`: overflow 학점이 최종적으로 귀속되는 트랙 키 반환.
- `curriculum_service_optimized.py`(와 죽은 `curriculum_service.py`)의 `_handle_overflow`, `_check_course_selection_overflow`, `_check_track_overflow`가 이 모듈을 사용합니다.

**주의**: 2026학번 이후가 입학하면 이 파일에 규칙을 추가하지 않는 한 자동으로 2024학번 규칙이 잘못 적용됩니다(9번 항목 참고).

---

## 5. `data/create_embeddings.py` vs `data/prepare_data.py`

두 스크립트는 독립적인 데이터 소스를 다루며, **`prepare_data.py`를 먼저 실행한 뒤 `create_embeddings.py`를 실행하는 순서**가 합리적입니다 (동시 실행도 가능하지만 의미상 선행 관계).

### 순서 ①: `prepare_data.py` — 정형 데이터(엑셀) → Supabase 테이블
- `data/raw_data/` 폴더의 엑셀 파일들(`curriculums.xlsx`, `equivalent_courses.xlsx`, `graduation_requirements.xlsx`, `academic_calendar.xlsx`, `laboratories.xlsx`, `library_hours.xlsx`)을 읽어 각각의 Supabase 테이블에 INSERT.
- 이 스크립트가 채우는 테이블(`curriculums`, `graduation_requirements`, `equivalent_courses`)이 바로 `curriculum_service_optimized.py`가 조회하는 테이블입니다. 즉 **졸업사정 기능이 동작하려면 이 스크립트가 먼저 돌아 DB에 데이터가 있어야 함**.
- **주의**: `data/raw_data/` 디렉토리 자체가 현재 저장소에 존재하지 않습니다(`.gitignore`로 제외되었거나 별도 관리 중). 원본 엑셀 없이는 이 스크립트를 재실행할 수 없습니다.

### 순서 ②: `create_embeddings.py` — 비정형 텍스트(.txt) → Supabase 벡터 테이블
- `data/text_data/*.txt`를 파싱해(`===CATEGORY:`/`===TITLE:` 기준) 문서 단위로 자르고, `SentenceTransformer(settings.embedding_model)`로 임베딩을 생성한 뒤 `documents` 테이블에 업로드.
- 이 테이블이 바로 `app/services/vector_service.py`의 `search()`가 조회하는 `documents` 테이블입니다. 즉 **일반 정보 질문(학사일정/도서관/장학금 등) 응답이 동작하려면 이 스크립트가 먼저 돌아야 함**.
- 추가로 Supabase `contact_info` 테이블에서 연락처 데이터를 가져와 문서화하는 기능도 있음(`load_from_db_tables`).
- 실행 시 대화형으로 "전체 재업로드 / 증분 업로드"를 선택하게 되어 있지만, `main()` 마지막 `upload_to_supabase()` 호출은 **항상 `clear_existing=True`로 하드코딩**되어 있어 사용자가 "2. 증분 업로드"를 선택해도 실제로는 매번 전체 삭제 후 재업로드됩니다(9번 항목의 버그 참고).

두 스크립트 모두 `sys.path.append(상위 디렉토리)`로 `app.config`를 import하므로 `backend/` 루트에서 실행하는 것을 전제로 합니다.

---

## 6. `data/text_data/*.txt` 샘플 분석

`library.txt`, `same_subject.txt`, `graduation.txt` 3개 파일을 샘플로 열어 포맷을 확인했습니다 (전체 내용은 읽지 않음).

**포맷**:
```
===CATEGORY: <카테고리명>
===TITLE: <문서 제목>
<본문 내용, 여러 줄 가능>

===CATEGORY: <다음 문서의 카테고리>
===TITLE: <다음 제목>
...
```
- `create_embeddings.py`의 `load_from_text_file()`이 `===CATEGORY:` 라인을 문서 구분자로 사용, `===TITLE:`은 메타데이터로 저장, 나머지 비어있지 않은 줄은 본문(`content`)으로 합쳐짐.
- 한 파일 안에 카테고리는 보통 고정(파일명과 대응)이지만 문서(TITLE)는 여러 개 반복됨.
- 본문에 이모지, FAQ 스타일 예시 질문("🤔 자주 묻는 질문: ...") 등이 포함되어 있어 벡터 검색 시 다양한 질문 표현과 매칭되도록 의도적으로 작성됨.

**파일 개수 및 카테고리 수**:
- `.txt` 파일 **10개**: `academic_calendar`, `contact`, `general_subject`, `graduation`, `laboratories`, `library`, `major_subject`, `same_subject`, `scholarship`, `school_bus`
- 파일당 `===CATEGORY:`(문서) 개수: academic_calendar 22, contact 74, general_subject 241, graduation 25, laboratories 16, library 54, major_subject 25, same_subject 64, scholarship 35, school_bus 42 → **총 문서 약 598개**
- 고유 카테고리 값은 **10개**: 교내 연락처, 교양과목, 도서관, 동일대체 과목, 실험실, 장학금, 전공과목, 졸업 요건, 통학버스, 학사일정 (파일 1개 = 카테고리 1개로 거의 1:1 대응)

---

## 7. `.env.example` 환경변수 추적

| 변수 | `.env.example` 값 | `config.py` 필드 | 실제 사용처 |
|---|---|---|---|
| `OPENAI_API_KEY` | (placeholder) | `openai_api_key: str` (필수) | `chatbot.py`, `query_router.py`, `review_service.py`의 `ChatOpenAI(openai_api_key=...)` |
| `SUPABASE_URL` | (placeholder) | `supabase_url: str` (필수) | `app/database/supabase_client.py`, `create_embeddings.py`, `prepare_data.py`, `google_sheets_sync.py`(간접) |
| `SUPABASE_KEY` | (placeholder) | `supabase_key: str` (필수) | **정의만 되고 코드에서 실사용처 없음** (아래 참고) |
| `SUPABASE_SERVICE_KEY` | (placeholder) | `supabase_service_key: str` (필수) | `supabase_client.py`, `create_embeddings.py`, `prepare_data.py`에서 실제 클라이언트 생성 시 사용 |
| `LANGCHAIN_TRACING_V2` | `false` | `langchain_tracing_v2: bool` | Settings 필드로만 존재, 앱 코드에서 참조 안 됨 (LangSmith는 보통 OS 환경변수를 langchain 라이브러리가 직접 읽음) |
| `LANGCHAIN_API_KEY` | placeholder | `langchain_api_key: str` | 위와 동일, 코드에서 미참조 |
| `LANGCHAIN_PROJECT` | placeholder | `langchain_project: str` | 위와 동일, 코드에서 미참조 |
| `ENVIRONMENT` | `development` | `environment: str` | `main.py` lifespan 로그 출력에만 사용 |
| `DEBUG` | `true` | `debug: bool` | `main.py`의 `/debug/sessions` 엔드포인트 노출 여부, uvicorn `reload` 옵션 |
| `HOST` | `0.0.0.0` | `host: str` | `main.py` uvicorn 실행 시 |
| `PORT` | `8000` | `port: int` (`os.getenv("PORT", 8000)`로 이중 정의, 아래 9번 참고) | `main.py` uvicorn 실행 시 |
| `MODEL_NAME` | `gpt-4o-mini` | `model_name: str` | `chatbot.py`, `query_router.py`, `review_service.py`의 LLM 모델명 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | `embedding_model: str = "jhgan/ko-sroberta-multitask"` | `vector_service.py`, `review_service.py`, `review_admin.py`, `create_embeddings.py`의 `SentenceTransformer(...)` — **8번 항목에서 상세 분석 (기본값과 예시값이 불일치)** |
| `MAX_TOKENS` | `1000` | `max_tokens: int = 500` (기본값 불일치) | `chatbot.py`의 `ChatOpenAI(max_tokens=...)` |
| `TEMPERATURE` | `0.7` | `temperature: float = 0.3` (기본값 불일치) | `chatbot.py`의 `ChatOpenAI(temperature=...)` |
| `REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` | localhost/6379/0 | 동일 필드 | **정의만 되고 실제 코드에서 미사용**. `session.py` 주석에 "나중에 Redis로 전환 가능"이라고만 되어 있고 현재 세션은 완전히 인메모리(dict) |
| `GOOGLE_SHEET_ID` | placeholder | `google_sheet_id: str` (필수) | `google_sheets_sync.py`에서 구글시트 열 때 사용 |
| (env에 없음) | — | `course_review_form_url: str` | `config.py`에 URL이 하드코딩된 기본값으로 있음, `chatbot.py`의 강의평가 작성 안내에 사용. `.env`로 오버라이드 가능하지만 예시 파일엔 없음 |
| (env에 없음) | — | — | `google_sheets_sync.py`가 읽는 `GOOGLE_CREDENTIALS`(os.getenv 직접 호출)는 `config.py`/`.env.example` 어디에도 없음 |

---

## 8. `EMBEDDING_MODEL` 심층 분석

### 코드에서의 사용

- **`vector_service.py`** (`__init__`): `self.model = SentenceTransformer(settings.embedding_model)` — `sentence-transformers` 라이브러리로 로컬(또는 HuggingFace Hub) 모델을 로드. 일반 정보 질문에 대한 쿼리 임베딩 생성용.
- **`review_service.py`** (`__init__`): 동일하게 `SentenceTransformer(settings.embedding_model)`로 강의평가 검색용 모델 로드.
- **`app/routes/review_admin.py`** (`get_embedding_model()`): 강의평가 승인 시 후기 텍스트를 임베딩하는 데도 동일 설정값 사용.
- **`data/create_embeddings.py`** (`EmbeddingCreator.__init__`): 텍스트 데이터를 벡터화해 `documents` 테이블에 넣을 때도 동일하게 `SentenceTransformer(settings.embedding_model)` 사용.

→ **네 곳 모두 `sentence-transformers`의 `SentenceTransformer` 클래스로 모델을 로드**하며, 이는 HuggingFace 계열 로컬 임베딩 모델(예: `jhgan/ko-sroberta-multitask`)을 기대하는 API입니다. OpenAI API 전용 모델명(`text-embedding-3-small`)을 넣으면 `SentenceTransformer`가 HuggingFace Hub에서 그 이름의 리포지토리를 찾으려다 실패합니다.

### 설정값 불일치

- `app/config.py`: `embedding_model: str = "jhgan/ko-sroberta-multitask"` (한국어 특화 sentence-transformers 모델, 기본값)
- `.env.example`: `EMBEDDING_MODEL=text-embedding-3-small` (OpenAI 임베딩 모델명, 예시값)

이 둘은 **양립 불가능**합니다. `.env.example`을 그대로 복사해 `.env`를 만들면 `SentenceTransformer("text-embedding-3-small")` 호출이 실패하여 서버가 아예 뜨지 않습니다(위 4곳 서비스 모두 `__init__`/모듈 로드 시점에 즉시 모델을 로드하므로).

### git 히스토리 확인 결과

```
git log -p --all -- backend/app/config.py backend/.env.example backend/data/create_embeddings.py backend/app/services/vector_service.py
```
전체 히스토리(2커밋) 중 `EMBEDDING_MODEL`/`embedding_model` 관련 변경은 **최초 커밋(`369150f`) 단 한 번**만 등장하며, 그 시점부터 이미:
- `.env.example` = `text-embedding-3-small`
- `config.py` 기본값 = `jhgan/ko-sroberta-multitask`

로 서로 다르게 작성되어 있었습니다. 즉 이후에 값이 바뀌면서 어긋난 것이 아니라, **"급하게 만든" 초기 커밋 시점부터 처음부터 불일치 상태로 커밋**된 것입니다. 실제로 운영 중인 `.env`(git에 커밋되지 않음, `.gitignore` 대상)에는 아마 `jhgan/ko-sroberta-multitask` 계열의 올바른 값이 들어있어서 지금까지 문제없이 동작해온 것으로 추정됩니다 — `.env.example`만 잘못된 예시값을 담고 있는 상태입니다.

---

## 9. 발견된 잠재적 버그 / 모순 정리

### 설정값 불일치
1. **`EMBEDDING_MODEL` 불일치** (8번 항목) — `.env.example`의 예시값(`text-embedding-3-small`)을 그대로 쓰면 `SentenceTransformer` 로딩이 실패해 서버가 부팅되지 않음. `.env.example`을 `jhgan/ko-sroberta-multitask` 계열 값으로 고치는 게 안전.
2. **`MAX_TOKENS`/`TEMPERATURE` 기본값 불일치** — `.env.example`은 `1000`/`0.7`, `config.py` 기본값은 `500`/`0.3`. 큰 장애는 아니지만 `.env` 없이 기본값만으로 배포하면 예시와 다른 동작(더 짧고 결정적인 답변)을 하게 됨.
3. **`PORT` 이중 정의** — `config.py`에 `port: int = int(os.getenv("PORT", 8000))`처럼 pydantic-settings의 자동 env 로딩과 별개로 수동으로 `os.getenv`를 또 호출. pydantic-settings가 `PORT` env를 이미 자동으로 매핑해주므로 이중 로직이며, `.env` 파일에만 `PORT`를 설정하고 실제 OS 환경변수로는 안 준 경우 `os.getenv("PORT", 8000)`가 `.env` 파일을 읽지 않아 8000으로 폴백될 수 있음(로딩 순서에 따라 미묘하게 달라질 수 있는 코드).

### 죽은 코드 / 미완성 코드
4. **`curriculum_service.py` 전체가 죽은 코드** (2번 항목) — 아무도 import하지 않음. 게다가 내부 `_get_alternative_codes()`의 `return alternatives`가 `for` 루프 안(if 블록 밖)에 들여쓰기 되어 있어, 실사용됐다면 첫 번째 조회 결과만 반환하고 순회를 중단하는 버그가 있었을 것 (동일대체 이력이 여러 단계인 경우 첫 단계만 반환).
5. **`equivalent_course_service.py`가 REST API(`app/routes/graduation.py`)에서만 쓰이고 챗봇 대화 흐름에서는 안 쓰임** — 캐시 없는 구버전이 API 응답 시마다 DB를 왕복하며, 캐시된 optimized 버전과 최신성이 다를 수 있음. 두 구현을 하나로 통합하거나 최소한 API도 optimized 버전을 쓰도록 정리할 필요.
6. **`query_router.needs_user_profile()` 계산 결과가 사용되지 않음** — `chatbot.py`의 `chat()`에서 `needs_profile = query_router.needs_user_profile(message)`를 호출해 변수에 담아두지만 이후 어디에서도 참조하지 않음(죽은 변수, 미완성 리팩토링 흔적으로 보임).
7. **`create_embeddings.py`의 업로드 모드 선택이 무의미함** — `main()`에서 사용자에게 "1. 전체 재업로드 / 2. 증분 업로드"를 입력받아 `clear_existing` 변수를 정하지만, 실제 `upload_to_supabase()` 호출부에는 `clear_existing=True`가 하드코딩되어 있어 사용자가 무엇을 선택하든 항상 전체 삭제 후 재업로드됨.
8. **`ChatResponse.query_type`의 `"hybrid"` 값이 스키마 주석에만 존재** — `app/models/schemas.py`에 `query_type: Optional[str] = None  # "curriculum", "general", "hybrid"`라고 되어 있지만 실제 코드에서 `"hybrid"`를 반환하는 경로는 없음(`curriculum`/`general`/`review` 3종류만 존재).

### 하드코딩된 값 / 취약한 로직
9. **`main.py`의 "더미 프로필" 판별이 하드코딩**된 특정 조건(`admission_year == 2020` and `course_code.startswith('CSE')`)으로 세션 프로필을 통째로 무시함. 테스트/개발 중 남은 디버그 코드로 보이며, 실제 학과 과목 코드 체계(`entity_extractor.py`의 정규식 기준 2글자+4자리, 예: `CS0614`)와는 다른 3글자 접두사(`CSE`)를 기준으로 하고 있어 우연히 일치할 위험은 낮지만, 의도가 불명확하고 운영 코드에 테스트용 필터가 그대로 남아있는 것 자체가 위험 요소.
10. **`graduation_rules.py`에 2024, 2025학번만 정의**되어 있고, 정의되지 않은 학번은 조용히 2024학번 규칙으로 폴백됨(`print` 경고만 출력, 예외 없음). 신입생 학번이 추가될 때마다 이 파일을 수동으로 갱신하지 않으면 잘못된 overflow 규칙이 조용히 적용될 수 있음.
11. **CORS 설정이 `allow_origins=["*"]` + `allow_credentials=True` 조합** (`main.py`) — 브라우저 CORS 스펙상 와일드카드 origin과 credentials 허용은 원래 상충되며, Starlette의 `CORSMiddleware`는 이 조합일 때 요청의 Origin을 그대로 반사(echo)하는 방식으로 우회 동작합니다. 결과적으로 사실상 "모든 출처에서 자격 증명 포함 요청 허용"이 되어 배포 환경에서는 보안상 바람직하지 않은 설정.
12. **`google_sheets_sync.py`가 사용하는 `gspread`, `oauth2client` 패키지가 `requirements.txt`에 없음** — 이 스크립트를 그대로 실행하면 `ModuleNotFoundError`가 발생함. 또한 이 스크립트가 읽는 `GOOGLE_CREDENTIALS` 환경변수도 `.env.example`에 없음.
13. **`data/prepare_data.py`가 참조하는 `data/raw_data/` 디렉토리가 저장소에 없음** — 원본 엑셀 파일 없이는 커리큘럼/졸업요건/동일대체 테이블을 재구축할 수 없음. 백업이 어디 있는지 확인 필요.
14. **`REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` 설정이 정의만 되고 전혀 사용되지 않음** — 세션은 완전히 인메모리(`app/models/session.py`)이며 서버 재시작 시 모든 세션이 소실됨. Redis 전환은 주석상 "나중에" 계획으로만 존재.
15. **`LANGCHAIN_TRACING_V2`/`LANGCHAIN_API_KEY`/`LANGCHAIN_PROJECT`가 `Settings` 객체 필드로는 존재하지만 앱 코드 어디에서도 `settings.langchain_*`을 참조하지 않음** — LangSmith 트레이싱을 켜려면 이 값들이 실제 OS 환경변수로 설정되어 있어야 하며(langchain이 자체적으로 os.environ을 읽음), `.env` 파일에만 넣는 것으로는 `python-dotenv`가 로드 시점에 os.environ에 반영해주지 않는 한 작동하지 않을 수 있음(pydantic-settings의 `Config.env_file`은 이를 Settings 객체 필드로만 파싱하고 os.environ에 다시 쓰지는 않음).
16. **`curriculum_service_optimized.py`의 캐시(`_graduation_requirements_cache`, `_selectable_courses_cache`)에 TTL/무효화 로직이 없음** — 서버가 켜져 있는 동안 관리자가 Supabase에서 `curriculums`/`graduation_requirements`를 수정해도 반영되지 않고, 재시작 전까지 이전 데이터로 계산됨. `equivalent_course_service_optimized.py`도 동일한 문제(앱 시작 시 1회 로드 후 갱신 없음).

---

## 요약 (한눈에 보기)

- **활성 경로**: `main.py` → `chatbot.py` → `query_router`/`entity_extractor`/`vector_service`/`review_service`/`curriculum_service_optimized`(+`equivalent_course_service_optimized`) + `app/routes/graduation.py`, `app/routes/review_admin.py`
- **죽은 코드**: `app/services/curriculum_service.py` (완전 미사용)
- **부분 사용/이중 관리 위험**: `app/services/equivalent_course_service.py` (REST API 한 곳에서만 사용, 캐시 없는 구버전과 캐시된 신버전이 공존)
- **가장 시급한 실무 이슈**: `.env.example`의 `EMBEDDING_MODEL` 예시값이 실제로 작동하지 않는 값 — 새 팀원이 `.env.example`을 그대로 복사하면 서버가 뜨지 않음.
