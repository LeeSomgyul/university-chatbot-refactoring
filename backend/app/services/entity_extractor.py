"""
사용자 메시지에서 정보 추출
"""
import re
from typing import List, Optional, Dict, Any
from app.database.supabase_client import supabase
from app.models.schemas import CourseInput


class EntityExtractor:
    """메시지에서 정보 추출"""
    
    def extract_admission_year(self, message: str) -> Optional[int]:
        """입학년도 추출"""
        # "2024학번", "24학번", "2024년도", "24년", "2024입학"
        patterns = [
            r'(\d{4})\s*학번',           # 2024학번
            r'(\d{2})\s*학번',            # 24학번
            r'(\d{4})\s*년\s*입학',       # 2024년 입학
            r'(\d{4})\s*년\s*입학생',     # 2024년 입학생
            r'(\d{4})\s*입학',            # 2024 입학
            r'(\d{4})\s*입학생',          # 2024 입학생
            r'(\d{4})\s*년도\s*입학',     # 2024년도 입학
            r'(\d{4})\s*년',              # 2024년 (마지막 우선순위)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                year = int(match.group(1))
                # 2자리면 20XX로 변환
                if year < 100:
                    year = 2000 + year
                # 유효성 체크 (2020~2030)
                if 2020 <= year <= 2030:
                    return year
        
        return None
    
    def extract_course_codes(self, message: str) -> List[str]:
        """과목 코드 추출 (CS0614, XG0800 등)"""
        pattern = r'\b[A-Za-z]{2}\d{4}\b'
        codes = re.findall(pattern, message, re.IGNORECASE)
        return [code.upper() for code in set(codes)]
    
    def extract_course_names(self, message: str) -> List[str]:
        """
        과목명 추출 (개선 버전)
        
        예시:
        "나 2024학번인데 컴퓨터구조응용, 컴퓨터애니메이션 과목 들어야하는데"
        → ["컴퓨터구조응용", "컴퓨터애니메이션"]
        
        "컴퓨터과학과 창업과진로, 명저읽기 들었어"
        → ["컴퓨터과학", "창업과진로", "명저읽기"]
        """
        
        original_message = message  # 디버깅용
        
        # ===== 1단계: 대대적 전처리 =====
        # 주어 제거 (나, 저 등)
        message = re.sub(r'(나|저)(는|가|도|요)?\s*', '', message)
        
        # 학번 관련 완전 제거
        message = re.sub(r'\d{2,4}\s*학번\s*(이고|인데|이며|에서|인데요)?', '', message)
        message = re.sub(r'\d{2,4}년\s*(입학|학번)?', '', message)
        
        # 동일대체/변경 관련 키워드 제거
        message = re.sub(r'(들어야\s*하는데|들어야\s*해|들어야)', '', message)
        message = re.sub(r'(이름\s*바뀐\s*거|바뀐\s*거|변경된\s*거|바뀐거)', '', message)
        message = re.sub(r'(있나\??|있어\??|없나\??)', '', message)
        
        # 과목 수강 관련 표현 제거
        message = re.sub(r'(들었|이수했|수강했|완료했)(어|습니다|어요)?', '', message)
        
        # 과목/수업 단어 제거 (뒤에만)
        message = re.sub(r'(과목|수업|강의)\s*(들었|이수했|수강했)?', '', message)
        
        # 졸업사정 관련 제거
        message = re.sub(r'(졸업사정|졸업)\s*(해줘|부탁해|알려줘)', '', message)
        
        # 특수문자 정리
        message = re.sub(r'[\.?!]+', '', message)
        
        # 여러 공백 → 단일 공백
        message = re.sub(r'\s+', ' ', message)
        message = message.strip()
        
        print(f"  🔍 전처리 후: '{original_message}' → '{message}'")
        
        # ===== 2단계: 콤마로 분리 =====
        parts = re.split(r'[,\n]+', message)
        
        course_names = []
        seen = set()
        
        # ===== 3단계: 각 파트 처리 =====
        for part in parts:
            part = part.strip()
            
            # 빈 문자열 스킵
            if not part:
                continue
            
            # "컴퓨터과학과 창업과진로" 형태 처리
            if '과 ' in part:
                sub_parts = part.split('과 ')
                for sub in sub_parts:
                    sub = sub.strip()
                    sub = self._clean_course_name(sub)
                    if sub and len(sub) >= 3:
                        if sub not in seen and re.search(r'[가-힣]', sub):
                            seen.add(sub)
                            course_names.append(sub)
                continue
            
            # 일반 파트 정리
            part = self._clean_course_name(part)
            
            # 최종 검증
            if part and len(part) >= 3 and re.search(r'[가-힣]', part):
                if part not in seen:
                    seen.add(part)
                    course_names.append(part)
        
        print(f"  ✅ 추출된 과목명: {course_names}")
        return course_names
    
    def _clean_course_name(self, text: str) -> str:
        """
        과목명 정리 헬퍼 함수
        
        조사, 불용어, 공백 제거
        """
        # 조사 제거
        text = re.sub(r'(이랑|과|와|랑|을|를|이|가|은|는|도)\s*$', '', text)
        
        # 뒤 불용어 제거
        stopwords_suffix = ['과목', '수업', '강의', '들어야하는데', '있나']
        for stop in stopwords_suffix:
            if text.endswith(stop):
                text = text[:-len(stop)]
        
        # 앞 불용어 제거
        stopwords_prefix = ['들은', '수강한', '이수한', '완료한']
        for stop in stopwords_prefix:
            if text.startswith(stop):
                text = text[len(stop):]
        
        # 공백 제거
        text = text.strip()
        
        # 내부 공백도 제거 (DB는 띄어쓰기 없음)
        text = re.sub(r'\s+', '', text)
        
        return text
    
    def search_course_by_name(
        self,
        course_name: str,
        admission_year: int
    ) -> Optional[Dict]:
        """
        과목명으로 검색 (DB 띄어쓰기 이미 제거됨)
        """
        try:
            # 정규화: 띄어쓰기 제거 + 소문자
            def normalize(text: str) -> str:
                return text.replace(' ', '').lower()
            
            course_name_normalized = normalize(course_name)
            
            if len(course_name_normalized) < 2:
                return None
            
            # === 1단계: 정확한 이름 매칭 (DB도 띄어쓰기 없음) ===
            result = supabase.table('curriculums')\
                .select('*')\
                .eq('admission_year', admission_year)\
                .eq('course_name', course_name_normalized)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            
            # === 2단계: LIKE 검색 (대소문자 무시) ===
            result = supabase.table('curriculums')\
                .select('*')\
                .eq('admission_year', admission_year)\
                .ilike('course_name', course_name_normalized)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            
            # === 3단계: 부분 매칭 (유연하게) ===
            result = supabase.table('curriculums')\
                .select('*')\
                .eq('admission_year', admission_year)\
                .ilike('course_name', f'%{course_name_normalized}%')\
                .limit(10)\
                .execute()
            
            if not result.data:
                return None
            
            # 가장 유사한 것 찾기
            best_match = None
            best_score = 0
            
            for row in result.data:
                db_name_normalized = normalize(row['course_name'])
                
                # 완전 일치
                if course_name_normalized == db_name_normalized:
                    return row
                
                # 부분 일치
                if course_name_normalized in db_name_normalized:
                    score = len(course_name_normalized) / len(db_name_normalized)
                    if score > best_score:
                        best_score = score
                        best_match = row
            
            # 유사도 60% 이상
            if best_match and best_score >= 0.6:
                return best_match
            
            return None
        
        except Exception as e:
            print(f"❌ 과목명 검색 실패 {course_name}: {e}")
            return None
    
    def get_course_details(
        self, 
        course_codes: List[str], 
        admission_year: int
    ) -> List[CourseInput]:
        """과목 코드 → 상세 정보 조회"""
        courses = []
        
        for code in course_codes:
            try:
                result = supabase.table('curriculums')\
                    .select('*')\
                    .eq('admission_year', admission_year)\
                    .eq('course_code', code)\
                    .limit(1)\
                    .execute()
                
                if result.data:
                    data = result.data[0]
                    courses.append(CourseInput(
                        course_code=data['course_code'],
                        course_name=data['course_name'],
                        credit=data['credit'],
                        course_area=data['course_area'],
                        requirement_type=data.get('requirement_type')
                    ))
                else:
                    print(f"⚠️ 과목을 찾을 수 없음: {code}")
            
            except Exception as e:
                print(f"❌ 과목 조회 실패 {code}: {e}")
        
        return courses
    
    def extract_course_info(
        self, 
        message: str
    ) -> Dict[str, Any]:
        """메시지에서 모든 정보 추출"""
        
        admission_year = self.extract_admission_year(message)
        
        if not admission_year:
            return {
                "admission_year": None,
                "course_codes": [],
                "courses": [],
                "has_enough_info": False
            }
            
        course_codes = self.extract_course_codes(message)
        course_names = self.extract_course_names(message)
        
        courses = []
        found_codes = set()
        
        # 1. 과목 코드로 조회
        if course_codes:
            courses.extend(self.get_course_details(course_codes, admission_year))
            found_codes.update(course_codes)
        
        # 2. 과목명으로 검색
        if course_names:
            for name in course_names:
                # 이미 찾은 과목은 스킵
                match = self.search_course_by_name(name, admission_year)
                
                if match and match['course_code'] not in found_codes:
                    courses.append(CourseInput(
                        course_code=match['course_code'],
                        course_name=match['course_name'],
                        credit=match['credit'],
                        course_area=match['course_area'],
                        requirement_type=match.get('requirement_type')
                    ))
                    found_codes.add(match['course_code'])
                    print(f"  ✅ '{name}' → {match['course_code']} {match['course_name']}")
                else:
                    print(f"  ⚠️ '{name}' 매칭 실패")
        
        return {
            "admission_year": admission_year,
            "course_codes": list(found_codes),
            "courses": courses,
            "has_enough_info": admission_year is not None and len(courses) > 0
        }
        
# 전역 인스턴스
entity_extractor = EntityExtractor()