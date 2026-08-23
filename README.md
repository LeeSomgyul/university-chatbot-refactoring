# LLM 기반 대학교 학사 챗봇

> LLM 기반 자연어 질의응답으로 학사·공지·교육과정 정보를 안내하는 대학교 챗봇
>
> 🔗 **[서비스 바로가기](https://university-chatbot-frontend-lovat.vercel.app/)**

### 1. 서비스 시연 화면
<table width="100%">
  <tr>
    <td align="center" width="50%"><b>홈 화면</b></td>
    <td align="center" width="50%"><b>자연어 응답</b></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/1c1d5526-c290-4fa1-acf4-501164a04be4" width="100%"/></td>
    <td><img src="https://github.com/user-attachments/assets/47c2dbaf-895a-4954-a032-8951f2a0e19f" width="100%"/></td>
  </tr>
  <tr>
    <td align="center" width="50%"><b>질문 자동완성</b></td>
    <td align="center" width="50%"><b>FAQ 전체보기</b></td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/8461b6a7-cb58-400a-9c53-a5a2b9b98be1" width="100%"/></td>
    <td><img src="https://github.com/user-attachments/assets/fa2fd9fc-8943-4c8e-a7c2-35deebd31faa" width="100%"/></td>
  </tr>
</table>

---

### 2. 핵심 기능 
| 분류 | 기능 |
| :--- | :--- |
| 질의응답 | 자연어 질문 의도 분석 및 도구(함수) 자동 선택, 관계형 DB/벡터 DB 하이브리드 조회, LLM 기반 자연어 응답 생성 |
| 학사 정보 조회 | 교육과정, 졸업요건, 동일/대체 교과목, 학사일정, 연구실, 도서관 운영시간 등 안내 |
| 대화 관리 | 세션 기반 대화 맥락 유지, 캐시 기반 반복 질문 응답 |
| 데이터 수집 | 학과 공지사항 HTML 크롤링 자동 수집, 학사 데이터(엑셀) 파싱 및 DB 적재, 텍스트 문서 임베딩 생성 |
| FAQ | 카테고리별 자주 묻는 질문 제공, FAQ 전체보기 |
| 강의평 관리 | 구글폼 기반 강의평 제출 데이터 자동 수집 및 관리자 승인 프로세스 |

---

### 3. 기술 스택
#### 프론트엔드
| 분류 | 기술 |
| :--- | :--- |
| 언어 / 프레임워크 | TypeScript 5.8.3, React 19.1.0, Vite 7.0.0 |
| 라우팅 | React Router 7.6.3 |
| 스타일링 | Tailwind CSS 4.1.11 |
#### 백엔드
| 분류 | 기술 |
| :--- | :--- |
| 언어 / 프레임워크 | Python 3.11.9, FastAPI 0.115.0 |
| AI / LLM | LangChain 0.3.7, LangChain OpenAI 0.2.8, OpenAI API 1.54.0 |
| 임베딩 | Sentence-Transformers 2.7.0 |
| 데이터 처리 | Pandas 2.2.3 |
| 캐시 | Redis 5.2.0 |
#### 데이터베이
| 분류 | 기술 |
| :--- | :--- |
| DB / 벡터 검색 | Supabase (PostgreSQL 기반), pgvector |
#### 인프라
| 분류 | 기술 |
| :--- | :--- |
| 프론트엔드 배포 | Vercel |
| 백엔드 배포 | Render |
