"""
강의평가 검색 서비스
"""
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.database.supabase_client import supabase


class ReviewSearchService:
    """강의평가 벡터 검색 서비스"""
    
    def __init__(self):
        print(f"🔧 강의평가 임베딩 모델 로딩: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        self.llm = None
        
        self.known_courses = self._load_courses_from_db()
        print(f"✅ 모델 로딩 완료 ({len(self.known_courses)}개 과목 로드됨)")
        
    def _get_llm(self) -> ChatOpenAI:
        """LLM 인스턴스 가져오기"""
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=settings.model_name,
                temperature=0,
                openai_api_key=settings.openai_api_key
            )
        return self.llm
        
    def _load_courses_from_db(self) -> List[str]:
        """DB에서 실제 과목명 목록 가져오기"""
        try:
            result = supabase.table('course_reviews')\
                .select('course_name')\
                .execute()
            
            if result.data:
                # 중복 제거
                courses = list(set([row['course_name'] for row in result.data]))
                return courses
            return []
        
        except Exception as e:
            print(f"❌ 과목 로드 실패: {e}")
            print("⚠️ 과목명 자동 매칭 비활성화됨")
            import traceback
            traceback.print_exc()
            return []
    
    
    def _find_best_course_match(self, query: str) -> Optional[str]:
        """쿼리에서 과목명 찾기 (DB 과목과 매칭)"""
        
        # DB에 과목이 없으면 None
        if not self.known_courses:
            return None
        
        # 1. 정확히 일치하는 과목명 찾기
        for course in self.known_courses:
            if course in query:
                return course
        
        # 2. 부분 일치 찾기
        import re
        
        # 불필요한 단어 제거
        filtered = query
        remove_words = ['강의', '후기', '평가', '수업', '과목', '교수님', '교수', 
                       '알려줘', '보여줘', '궁금', '어때', '있어', '님', '의']
        
        for word in remove_words:
            filtered = filtered.replace(word, ' ')
        
        # 한글 단어 추출 (2글자 이상)
        words = re.findall(r'[가-힣]{2,}', filtered.strip())
        
        # 추출된 단어들과 DB 과목명 비교
        for word in words:
            for course in self.known_courses:
                # 단어가 과목명에 포함되거나, 과목명이 단어에 포함
                if word in course or course in word:
                    return course
        
        return None
    
    def extract_professor_and_course(self, query: str) -> Dict[str, Optional[str]]:
        """
        LLM으로 교수명과 강의명 추출
        
        예: "김철수 교수님 데이터베이스 강의 후기"
        → professor: "김철수", course: "데이터베이스"
        """
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 강의평가 검색을 위한 정보 추출 전문가입니다.
사용자 질문에서 교수명과 강의명을 추출하세요.

추출 규칙:
1. 교수명: "김철수", "이영희" 같은 한글 이름 (성+이름)
   - "교수님", "교수" 같은 호칭은 제외
   - 성만 있는 경우 ("김교수") → 성만 추출
2. 강의명: "데이터베이스", "자료구조", "알고리즘" 같은 과목명
   - "강의", "수업", "과목" 같은 단어는 제외
3. 없으면 null 반환

응답 형식 (JSON만):
{{
  "professor": "김철수" 또는 null,
  "course": "데이터베이스" 또는 null
}}"""),
            ("user", f"질문: {query}\n\nJSON 응답:")
        ])
        
        try:
            llm = self._get_llm()
            chain = extraction_prompt | llm
            response = chain.invoke({})
            
            # JSON 파싱
            import json
            content = response.content.strip()
            
            # JSON 블록 제거
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            professor = result.get('professor')
            course = result.get('course')
            
            if not course:
                course = self._find_best_course_match(query)
                if course:
                    print(f"  🔍 DB 매칭으로 과목 찾음: {course}")
            
            print(f"  📋 추출 결과: professor={professor}, course={course}")
            
            return {'professor': professor, 'course': course}
        
        except Exception as e:
            print(f"⚠️ LLM 추출 실패, 정규식 사용: {e}")
            
            # 폴백: 정규식
            import re
            professor = None
            course = None
            
            professor_match = re.search(r'([가-힣]{2,4})\s*교수(?:님)?', query)
            if professor_match:
                professor = professor_match.group(1)
            
            course = self._find_best_course_match(query)
            
            print(f"  🔍 정규식+DB 추출: professor={professor}, course={course}")
            
            return {'professor': professor, 'course': course}
    
    def get_professors_by_course(self, course_name: str) -> List[Dict[str, Any]]:
        """
        특정 강의를 가르치는 교수님 목록 조회
        
        Returns:
            [{"professor_name": "김철수", "review_count": 3}, ...]
        """
        try:
            result = supabase.table('course_reviews')\
                .select('professor_name')\
                .ilike('course_name', f'%{course_name}%')\
                .execute()
            
            if not result.data:
                return []
            
            # 교수별 카운트
            professor_count = {}
            for row in result.data:
                prof = row['professor_name']
                professor_count[prof] = professor_count.get(prof, 0) + 1
            
            # 정렬
            professors = [
                {"professor_name": prof, "review_count": count}
                for prof, count in professor_count.items()
            ]
            professors.sort(key=lambda x: x['review_count'], reverse=True)
            
            return professors
        
        except Exception as e:
            print(f"❌ 교수 목록 조회 실패: {e}")
            return []
    
    def search_reviews(
        self, 
        query: str, 
        k: int = 5,
        professor_filter: Optional[str] = None,
        course_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        강의평가 벡터 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 후기 수
            professor_filter: 교수명 필터
            course_filter: 강의명 필터
        
        Returns:
            검색 결과 리스트
        """
        # 쿼리 임베딩 생성
        query_embedding = self.model.encode(query).tolist()
        
        # 필터 JSON 생성
        filter_json = {}
        if professor_filter:
            filter_json['professor_name'] = professor_filter
        if course_filter:
            filter_json['course_name'] = course_filter
        
        try:
            result = supabase.rpc(
                'match_course_reviews',
                {
                    'query_embedding': query_embedding,
                    'match_count': k,
                    'filter': filter_json
                }
            ).execute()
            
            return result.data if result.data else []
        
        except Exception as e:
            print(f"❌ 강의평가 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def format_review_summary(
        self, 
        results: List[Dict[str, Any]], 
        detail_mode: str = "summary",
        start_index: int = 0
    ) -> str:
        """
        검색 결과를 포맷팅
        
        Args:
            results: 검색 결과
            detail_mode: "summary" / "detail" / "more"
            start_index: 상세 후기 시작 인덱스 (more 모드용)
        """
        if not results:
            return ""
        
        # 기본 정보
        first = results[0]
        professor = first.get('professor_name', '알 수 없음')
        course = first.get('course_name', '알 수 없음')
        total_count = len(results)
        
        # ===== 요약 모드 =====
        if detail_mode == "summary":
            # 통계 계산
            stats = {
                'teaching_style': {},
                'assignment_load': {},
                'exam_difficulty': {}
            }
            
            for r in results:
                for key in stats.keys():
                    value = r.get(key, '알 수 없음')
                    stats[key][value] = stats[key].get(value, 0) + 1
            
            # 강의 방식
            teaching = max(stats['teaching_style'].items(), key=lambda x: x[1])[0]
            # 과제량
            assignment = max(stats['assignment_load'].items(), key=lambda x: x[1])[0]
            # 시험 난이도
            exam = max(stats['exam_difficulty'].items(), key=lambda x: x[1])[0]
            
            summary = f"""📚 **{course} - {professor} 교수님** (후기 {total_count}건)

📊 **종합 평가:**
• 강의방식: {teaching}
• 과제량: {assignment}
• 시험난이도: {exam}

💬 **학생들의 한마디:**
"""
            # 대표 후기 1-2개 (짧게)
            for i, r in enumerate(results[:2], 1):
                review_short = r.get('review_text', '')[:80] + "..."
                summary += f"{i}. \"{review_short}\"\n"
            
            summary += f"\n💡 상세 후기를 보려면 \"상세 후기 보여줘\"라고 말씀해주세요!"
            
            return summary
        
        # ===== 상세 모드 (첫 2개) =====
        elif detail_mode == "detail":
            detail_text = f"""📚 **{course} - {professor} 교수님** 상세 후기

"""
            # 처음 2개만 보여주기
            for i, result in enumerate(results[:2], 1):
                semester = result.get('semester', '')
                teaching_style = result.get('teaching_style', '')
                assignment_load = result.get('assignment_load', '')
                exam_difficulty = result.get('exam_difficulty', '')
                review_text = result.get('review_text', '')
                
                detail_text += f"""**[{i}] {semester}학기**
👨‍🏫 강의방식: {teaching_style}
📝 과제량: {assignment_load}
📊 시험난이도: {exam_difficulty}

💬 후기:
{review_text}

{'-'*50}

"""
            
            # 후기가 2개보다 많으면 "다른 평 보여줘" 유도
            if total_count > 2:
                detail_text += f"💡 후기가 {total_count-2}건 더 있어요! \"다른 평 보여줘\"라고 말씀해주세요!"
            
            return detail_text
        
        # ===== 추가 후기 모드 (다음 2개) =====
        elif detail_mode == "more":
            # start_index부터 2개
            end_index = min(start_index + 2, total_count)
            
            if start_index >= total_count:
                return "더 이상 후기가 없어요! 😊"
            
            more_text = f"""📚 **{course} - {professor} 교수님** 추가 후기

"""
            for i, result in enumerate(results[start_index:end_index], start_index + 1):
                semester = result.get('semester', '')
                teaching_style = result.get('teaching_style', '')
                assignment_load = result.get('assignment_load', '')
                exam_difficulty = result.get('exam_difficulty', '')
                review_text = result.get('review_text', '')
                
                more_text += f"""**[{i}] {semester}학기**
👨‍🏫 강의방식: {teaching_style}
📝 과제량: {assignment_load}
📊 시험난이도: {exam_difficulty}

💬 후기:
{review_text}

{'-'*50}

"""
            
            # 아직 더 있으면 계속 유도
            if end_index < total_count:
                more_text += f"💡 후기가 {total_count - end_index}건 더 있어요! \"다른 평 보여줘\"라고 말씀해주세요!"
            else:
                more_text += f"✅ 모든 후기를 다 봤어요!"
            
            return more_text


# 전역 서비스
review_service = None


def get_review_service() -> ReviewSearchService:
    """강의평가 서비스 싱글톤"""
    global review_service
    if review_service is None:
        review_service = ReviewSearchService()
    return review_service