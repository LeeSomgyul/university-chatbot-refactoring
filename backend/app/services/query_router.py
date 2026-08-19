# ===============================================
# 사용자의 질문이 들어왔을 때 라우터 처리 (curriculum/reviews/general)
# ===============================================

import re
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config import settings


class QueryRouter:
    """질문 유형 분류 - LLM + 키워드 하이브리드"""
    
    def __init__(self):
        self.llm = None
    
    def _get_llm(self) -> ChatOpenAI:
        """LLM 인스턴스 가져오기"""
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=settings.model_name,
                temperature=0,
                openai_api_key=settings.openai_api_key
            )
        return self.llm
    
    # 1. general 키워드(벡터db 관련)
    STRONG_GENERAL_KEYWORDS = [
        # 학사 일정
        '개강', '종강', '중간고사', '기말고사', '시험', '방학', '일정',
        '언제', '기간', '날짜',
        
        # 도서관
        '도서관', '책', '대출', '반납', '빌려', '빌릴', '열람실', '자료관',
        
        # 연락처/위치
        '연락처', '전화', '번호', '위치', '어디', '몇 번',
        '사무실', '실험실', '문의',
        
        # 동일대체
        '대신', '대체', '동일대체', '바뀐', '변경', '바꿔'
        
        # 기타 학교 정보
        '운영시간', '시간표', '통학', '버스', '장학금',
        '졸업생', '휴학생', '지역주민', '외부인'
    ]
    
    # 2. 교육과정 관련 키워드
    CURRICULUM_KEYWORDS = [
        # 과목 정보
        '들었', '이수했', '수강했', '완료했',
        
        # 요건
        '전공필수', '전공선택', '교양필수', '교양선택',
        '전필', '전선', '교필', '교선',
        
        # 졸업사정
        '졸업사정', '남은', '남았', '진행', '현황', '상태',
        
        # 학번
        '학번'
    ]
    
    def _has_course_info(self, query: str) -> bool:
        """과목 정보가 있는지 체크"""
        
        # 1. 과목 코드 패턴 (CS0614, XG0800 등)
        if re.search(r'\b[A-Z]{2}\d{4}\b', query.upper()):
            return True
        
        # 2. 이미 들은 과목 언급 (과거형만)
        taken_keywords = ['들었', '이수했', '수강했', '완료했', '들은', '이수한']
        has_taken_keyword = any(kw in query for kw in taken_keywords)
        
        if has_taken_keyword and ',' in query:
            return True
        
        if has_taken_keyword and any(kw in query for kw in ['과목은', '과목:', '수업은']):
            return True
        
        return False
    
    def classify(self, query: str) -> Literal["curriculum", "general", "review"]:
        """
        질문 분류
        """
        graduation_info_keywords = ['졸업요건', '졸업기준', '이수요건', '필요학점', '졸업하려면']
        graduation_check_keywords = ['졸업사정', '졸업할', '졸업가능', '남은학점']
        
        has_info = any(kw in query for kw in graduation_info_keywords)
        has_check = any(kw in query for kw in graduation_check_keywords)
        
        # 졸업요건 질문 (설명) → general
        if has_info and not has_check:
            print("  → 졸업요건 설명: general")
            return "general"
        
        # 졸업사정 질문 (개인) → curriculum
        if has_check:
            print("  → 졸업사정: curriculum")
            return "curriculum"
        
        # ===== LLM 분류 (나머지 케이스) =====
        try:
            classification_prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 대학 챗봇의 질문 분류 전문가입니다.
    사용자 질문을 3가지 카테고리로 분류하세요:

    1. **review** (강의평가)
    - 특정 교수/강의의 후기, 평가, 의견
    - 예: "데이터베이스 강의평 있어?", "김교수님 수업 어때?"

    2. **curriculum** (교육과정) - ⚠️ 오직 아래 2가지만!
    
    ① 개인 맞춤 졸업사정
        - 내가 들은 과목으로 졸업 가능한지, 남은 학점 계산
        - 예: "나 졸업할 수 있어?", "남은 학점 뭐야?"
    
    ② 교육과정 전체 리스트 조회
        - 특정 학번/요건의 과목 전체 목록
        - 예: "2024학번 전공필수 뭐야?", "공통교양 리스트 보여줘"

    3. **general** (일반 정보) - ⚠️ 나머지 전부!
    - 과목 추천, 설명, 소개, 정보
    - 학사 일정, 시설, 교수 정보
    - 동일대체 과목 조회 (과목명 변경 관련)
    - 예: "재밌는 교양 추천해줘", "음악 관련 과목 알려줘"
    - 예: "컴퓨터과학 대신 들을 수 있는 과목?", "과목명 바뀐거 있나?"

    **핵심 판단 기준:**

    ✅ curriculum (2가지만):
    - "나 **졸업할 수 있어**?" → curriculum (졸업사정)
    - "**남은 학점** 뭐야?" → curriculum (졸업사정)
    - "2024학번 **전공필수 뭐야**?" → curriculum (리스트)
    - "**공통교양 리스트** 보여줘" → curriculum (리스트)

    ✅ general (나머지):
    - "**재밌는** 교양 알려줘" → general (추천)
    - "음악 **관련** 과목" → general (추천)
    - "**쉬운** 교양 추천" → general (추천)
    - "컴퓨터과학 **대신** 들을 수 있는 과목?" → general (동일대체)
    - "과목명 **바뀐거** 있나?" → general (동일대체)

    **중요 규칙:**
    - 추천/설명/관련/배우고싶 키워드 → 무조건 general
    - 동일대체/대신/바뀐/변경 키워드 → 무조건 general
    - 교양/과목이 나와도 추천 의도면 → general
    - 졸업사정/리스트가 아니면 → general
    - 애매하면 → general (벡터 검색이 더 유연함)

    응답 형식 (단어 하나만):
    review / curriculum / general"""),
                ("user", f"질문: {query}\n\n분류:")
            ])
            
            llm = self._get_llm()
            chain = classification_prompt | llm
            response = chain.invoke({})
            
            result = response.content.strip().lower()
            
            # 응답 정리
            if 'review' in result:
                classification = 'review'
            elif 'curriculum' in result:
                classification = 'curriculum'
            elif 'general' in result:
                classification = 'general'
            else:
                # 파싱 실패 시 폴백
                print(f"⚠️ LLM 응답 파싱 실패: {result}, 폴백 사용")
                return self._fallback_classify(query)
            
            if classification == 'curriculum':
                recommendation_keywords = ['추천', '재밌', '쉬운', '좋은', '관련', '배우고싶', '듣고싶']
                if any(kw in query for kw in recommendation_keywords):
                    print(f"  ⚠️ LLM이 curriculum으로 분류했지만 추천 의도 감지 → general로 변경")
                    classification = 'general'
            
            print(f"  → LLM 분류: {classification}")
            return classification
        
        except Exception as e:
            print(f"❌ LLM 분류 실패, 폴백 사용: {e}")
            return self._fallback_classify(query)
    
    def _fallback_classify(self, query: str) -> Literal["curriculum", "general", "review"]:
        """
        LLM 실패 시 폴백: 기존 키워드 기반 분류
        """
        query_lower = query.lower()
        
        # ===== 1. 강의평가 키워드=====
        review_keywords = ['후기', '평가', '리뷰', '수강평', '강의평가', '강의평', 
                          '어때', '어떤', '어떠', '괜찮', '추천', '평판']
        if any(kw in query for kw in review_keywords):
            print("  → 폴백: review")
            return "review"
        
        # ===== 2. general 키워드 =====
        if any(kw in query_lower for kw in self.STRONG_GENERAL_KEYWORDS):
            print("  → 폴백: general (강력한 키워드)")
            return "general"
        
        # ===== 3. 교육과정 조회 (학번 + 요건 키워드) =====
        has_admission_year = '학번' in query or re.search(r'\b20\d{2}\b', query)
        requirement_keywords = [
            '전공필수', '전공선택', '교양필수', '교양선택',
            '전필', '전선', '교필', '교선', '교양', '전공'
        ]
        has_requirement = any(kw in query for kw in requirement_keywords)
        
        if has_admission_year and has_requirement:
            print("  → 폴백: curriculum (교육과정)")
            return "curriculum"
        
        # ===== 4. 졸업사정 요청 키워드 =====
        assessment_keywords = [
            '졸업사정', '남은 학점', '남은 과목', '졸업 가능',
            '이수 현황', '진행 현황', '졸업 확인'
        ]
        if any(kw in query for kw in assessment_keywords):
            print("  → 폴백: curriculum (졸업사정)")
            return "curriculum"
        
        # ===== 5. 졸업 요건 설명 (과목 정보 없음) =====
        if '졸업' in query:
            # 설명 요청 키워드
            explanation_keywords = ['뭐야', '어떻게', '설명', '구조', '알려줘']
            if any(kw in query for kw in explanation_keywords):
                print("  → 폴백: general (졸업 요건 설명)")
                return "general"
            
            # 명확하지 않으면 general (안전하게)
            print("  → 폴백: general (졸업 관련)")
            return "general"
        
        # ===== 6. curriculum 키워드 =====
        if any(kw in query_lower for kw in self.CURRICULUM_KEYWORDS):
            print("  → 폴백: curriculum")
            return "curriculum"
        
        # ===== 7. 기본값 =====
        print("  → 폴백: general (기본값)")
        return "general"
    
    def needs_user_profile(self, query: str) -> bool:
        """사용자 프로필이 필요한 질문인지 확인"""
        personal_indicators = [
            '나는', '내가', '저는', '제가',
            '남은', '들었', '이수했', '수강했'
        ]
        return any(indicator in query for indicator in personal_indicators)


# 전역 라우터
query_router = QueryRouter()