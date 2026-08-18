# 순천대학교 컴퓨터공학과 웹 챗봇

![메인화면](mainpage.png)

**순천대학교 컴퓨터공학과 재학생 및 궁금해하는 사람들을 위한 웹 기반 챗봇 시스템입니다.**  
이 프로젝트는 순천대학교 컴퓨터공학과와 관련된 다양한 정보를 쉽고 빠르게 제공하는 인터랙티브 챗봇입니다. 학생들이 학과 정보, 교육과정, 교수진, 공지사항 등에 대해 자연어로 질문하고 실시간으로 답변을 받을 수 있습니다.

---

## 목표

- 순천대학교 **컴퓨터공학과 재학생** 또는 **진학 희망자**가  
  학사 관련 질문을 **웹 상에서 자연스럽게 물어보고**, 정보를 얻어갈 수 있는 환경 제공
- 복잡한 졸업 요건 및 학사 규정도 **챗봇을 통해 쉽게 안내**
- 실제 웹 서비스로 사용할 수 있도록 **프론트·백엔드·DB 완전 연동**

---

## 기술 스택

### 프론트엔드
- **React** + **TypeScript** (with [Vite](https://vitejs.dev/))
- **Zustand**: 전역 상태 관리
- **Axios**: API 통신
- **Tailwind CSS**: UI 스타일링

### 백엔드 및 크롤링
- **FastAPI**: Python 기반 웹 프레임워크
- **BeautifulSoup + requests**: 학사공지, 일정 등 크롤링
- **SQLAlchemy + MySQL (RDS)**: 데이터베이스 저장 및 ORM 처리

### 자연어 처리 (NLP)
- **LangChain**: 사용자 질의 응답 흐름 구성
- **KoNLPy**: 형태소 분석 등 한국어 처리
- **FastAPI** 기반 챗봇 API 통합

---

## 주요 기능

- **실시간 채팅**: 자연어 기반 질의응답
- **학과 정보 제공**: 교육과정, 교수진, 연구실 정보
- **공지사항 조회**: 최신 학과 공지사항 및 소식
- **입학 정보**: 입시 관련 정보 및 FAQ
- **반응형 디자인**: 모바일 및 데스크톱 지원

---

## 파일 구조

```
├── frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── components/      # React 컴포넌트
│   │   ├── stores/          # Zustand 스토어
│   │   ├── api/             # Axios API 설정
│   │   └── types/           # TypeScript 타입 정의
│   ├── package.json
│   └── vite.config.ts
├── backend/                 # FastAPI 백엔드
│   ├── app/
│   │   ├── api/             # API 라우터
│   │   ├── models/          # SQLAlchemy 모델
│   │   ├── schemas/         # Pydantic 스키마
│   │   ├── services/        # 비즈니스 로직
│   │   └── nlp/             # 자연어 처리 모듈
│   └── requirements.txt
├── scraper/                 # 웹 크롤링 모듈
│   ├── scrapers/            # 크롤러 구현
│   └── data_processor.py    # 데이터 전처리
├── README.md
└── .gitignore
```

---

## 실행 방법

### 1. 백엔드 실행 (FastAPI)

```bash
cd backend
```

### 2. 프론트엔드 실행 (React)

```bash
cd frontend
npm install
npm run dev
```

---

## 버전
node : v22.15.0
tailwindCSS : 4.1.11


---

## 데이터 소스

- 순천대학교 공식 홈페이지
- 컴퓨터공학과 홈페이지
