# 프로젝트 소개
| 항목 | 내용 |
|---|---|
| 프로젝트명 | LLM 기반 대학교 학사 챗봇 |
| 서비스 개요 | LLM 기반 자연어 질의응답으로 학사·공지·교육과정·맛집 정보를 안내하는 대학교 챗봇 |
| 개발 기간 | (1차) 2025.06.24 ~ 2025.11.15 (2차) 2026.08.22 ~ 2026.08.30 |
| 개발 인원 | 5인 |
| 배포 URL | https://university-chatbot-refactoring-i6yx.vercel.app |


# 사용한 기술
| 구분 | 기술/버전 |
|---|---|
| Backend | Python 3.12.10, FastAPI 0.115.0, OpenAI 3.3.1, kiwipiepy 0.23.2, LangGraph 1.2.11, LangChain 1.3.16, Redis(Valkey) 8.1.4, Pandas 2.2.3, Sentence-Transformers 2.7.0(Embedding) |
| Database |  Supabase 2.9.0, pgvector, PostgreSQL |
| Frontend | TypeScript 5.8.3, React 19.1.0, Tailwind CSS 4.1.11, Vite 7.0.0 |
| Infra | Render, Vercel, GitActions, GHCR(Github Container Registry), Docker |


# 핵심 기능 
| 분류 | 기능 |
| --- | --- |
| 질의응답 | 자연어 질문 의도 분석 및 도구(함수) 자동 선택, 관계형 DB/벡터 DB 하이브리드 조회, LLM 기반 자연어 응답 생성 |
| 학사 정보 조회 | 교육과정, 졸업요건, 동일/대체 교과목, 학사일정, 연구실, 도서관 운영시간 등 안내 |
| 대화 관리 | 세션 기반 대화 맥락 유지, 캐시 기반 반복 질문 응답 |
| 데이터 수집 | 학과 공지사항 HTML 크롤링 자동 수집, 학사 데이터(엑셀) 파싱 및 DB 적재, 텍스트 문서 임베딩 생성 |
| FAQ | 카테고리별 자주 묻는 질문 제공, FAQ 전체보기 |
| 강의평 관리 | 구글폼 기반 강의평 제출 데이터 자동 수집 및 관리자 승인 프로세스 |


# 팀원별 담당 기능
<table>
  <thead>
    <tr>
      <th>팀원</th>
      <th>담당 기능</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td nowrap>이솜귤</td>
      <td></td>
    </tr>
    <tr>
      <td nowrap>안은혜</td>
      <td>식도락(맛집 추천) 기능 설계·구현, 식도락 관련 RAG/벡터 검색 및 프론트엔드 연결, <br>화면설계서/플로우차트 작성, React 기반 레이아웃 및 CSS 퍼블리싱, 컴포넌트 UI 상태관리</td>
    </tr>
    <tr>
      <td nowrap>김의윤</td>
      <td></td>
    </tr>
    <tr>
      <td nowrap>최민서</td>
      <td></td>
    </tr>
    <tr>
      <td nowrap>이여원</td>
      <td></td>
    </tr>
  </tbody>
</table>

# 주요 실행화면
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


# 아키텍처 다이어그램
<img width="6942" height="5393" alt="image" src="https://github.com/user-attachments/assets/8bbd9b0b-a8f8-4d2d-9a61-3cb424451f73" />


# 실행 방법
## 백엔드
```
venv\Scripts\Activate.ps1  
pip install -r requirements.txt
docker compose up -d redis
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
## 프론트엔드
```
npm install
npm run dev
```
