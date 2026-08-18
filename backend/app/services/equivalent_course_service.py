"""
동일대체교과목 서비스(최적화 전 (백업 파일))
"""
from typing import Dict, List, Optional
from app.database.supabase_client import supabase


class EquivalentCourseService:
    """동일대체교과목 관리"""
    
    def get_equivalent_course(
        self, 
        course_code: str,
        direction: str = "old_to_new"
    ) -> Optional[Dict]:
        """
        대체 과목 조회
        
        Args:
            course_code: 과목 코드
            direction: "old_to_new" (구→신) or "new_to_old" (신→구)
        
        Returns:
            {
                "old_course_code": "CS0119",
                "old_course_name": "기초설계",
                "new_course_code": "CS0601",
                "new_course_name": "기초설계",
                "mapping_type": "동일",
                "allow_duplicate": False,
                "allow_retake": True
            }
        """
        try:
            if direction == "old_to_new":
                result = supabase.table('equivalent_courses')\
                    .select('*')\
                    .eq('old_course_code', course_code)\
                    .execute()
            else:  # new_to_old
                result = supabase.table('equivalent_courses')\
                    .select('*')\
                    .eq('new_course_code', course_code)\
                    .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"❌ 대체 과목 조회 실패: {e}")
            return None
        
    def get_latest_course_code(
        self, 
        course_code: str,
        max_depth: int = 10
    ) -> str:
        """
        재귀적으로 최신 과목 코드 찾기
        
        Args:
            course_code: 시작 과목 코드
            max_depth: 최대 추적 깊이 (무한루프 방지)
        
        Returns:
            최종 과목 코드
            
        Example:
            get_latest_course_code("CS0116")
            → CS0116 → CS0612 → CS0863
            → 반환: "CS0863"
        """
        current_code = course_code
        visited = set()  # 무한루프 방지
        depth = 0
        
        while depth < max_depth:
            if current_code in visited:
                # 순환 참조 감지
                print(f"⚠️ 순환 참조 감지: {current_code}")
                break
            
            visited.add(current_code)
            
            # 다음 단계 조회
            equiv = self.get_equivalent_course(current_code, "old_to_new")
            
            if equiv:
                # 다음 코드로 이동
                current_code = equiv['new_course_code']
                depth += 1
            else:
                # 더 이상 변경 없음
                break
        
        return current_code
    
    def get_course_history(
        self, 
        course_code: str,
        max_depth: int = 10
    ) -> List[Dict]:
        """
        과목 변경 이력 전체 조회
        
        Returns:
            [
                {
                    "code": "CS0116",
                    "name": "컴퓨터그래픽스",
                    "mapping_type": None  # 시작
                },
                {
                    "code": "CS0612",
                    "name": "컴퓨터그래픽스",
                    "mapping_type": "동일"
                },
                {
                    "code": "CS0863",
                    "name": "HCI(AR/VR/XR)",
                    "mapping_type": "대체"
                }
            ]
        """
        history = []
        current_code = course_code
        visited = set()
        depth = 0
        
        # 시작 과목 정보 조회 (curriculums 테이블에서)
        start_course = self._get_course_info(current_code)
        history.append({
            "code": current_code,
            "name": start_course['name'] if start_course else "알 수 없음",
            "mapping_type": None
        })
        
        while depth < max_depth:
            if current_code in visited:
                break
            
            visited.add(current_code)
            
            # 다음 단계 조회
            equiv = self.get_equivalent_course(current_code, "old_to_new")
            
            if equiv:
                history.append({
                    "code": equiv['new_course_code'],
                    "name": equiv['new_course_name'],
                    "mapping_type": equiv['mapping_type']
                })
                current_code = equiv['new_course_code']
                depth += 1
            else:
                break
        
        return history
    
    def format_course_history(self, course_code: str) -> str:
        """
        과목 변경 이력을 사용자 친화적으로 표시
        
        Returns:
            "CS0116 컴퓨터그래픽스 → CS0612 컴퓨터그래픽스 (동일) → CS0863 HCI(AR/VR/XR) (대체)"
        """
        history = self.get_course_history(course_code)
        
        if len(history) <= 1:
            return f"{course_code} (변경 이력 없음)"
        
        parts = []
        for i, item in enumerate(history):
            if i == 0:
                # 시작
                parts.append(f"{item['code']} {item['name']}")
            else:
                # 변경
                mapping = f"({item['mapping_type']})" if item['mapping_type'] else ""
                parts.append(f"{item['code']} {item['name']} {mapping}")
        
        return " → ".join(parts)
    
    def _get_course_info(self, course_code: str) -> Optional[Dict]:
        """
        curriculums 테이블에서 과목 정보 조회
        """
        try:
            result = supabase.table('curriculums')\
                .select('course_name')\
                .eq('course_code', course_code)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return {"name": result.data[0]['course_name']}
            return None
        except:
            return None
    
    def is_equivalent(
        self, 
        code1: str, 
        code2: str
    ) -> bool:
        """
        두 과목 코드가 동일/대체 과목인지 확인 (체인 고려)
        
        Example:
            is_equivalent("CS0116", "CS0863") → True
            (CS0116 → CS0612 → CS0863 체인)
        """
        if code1 == code2:
            return True
        
        # code1의 최종 코드
        latest1 = self.get_latest_course_code(code1)
        
        # code2의 최종 코드
        latest2 = self.get_latest_course_code(code2)
        
        # 최종 코드가 같으면 동일
        if latest1 == latest2:
            return True
        
        # code1의 전체 히스토리
        history1 = [h['code'] for h in self.get_course_history(code1)]
        
        # code2가 code1 히스토리에 있으면 True
        if code2 in history1:
            return True
        
        # code2의 전체 히스토리
        history2 = [h['code'] for h in self.get_course_history(code2)]
        
        # code1이 code2 히스토리에 있으면 True
        if code1 in history2:
            return True
        
        return False
    
    def resolve_course_code(self, course_code: str) -> str:
        """
        과목 코드를 최신 코드로 변환 (체인 추적)
        
        Example:
            resolve_course_code("CS0116") → "CS0863"
        """
        return self.get_latest_course_code(course_code)
    
    def get_all_equivalent_codes(self, course_code: str) -> List[str]:
        """
        특정 과목의 모든 동일/대체 과목 코드 목록 (체인 전체)
        
        Returns:
            ["CS0116", "CS0612", "CS0863"]
        """
        history = self.get_course_history(course_code)
        return [item['code'] for item in history]
    
    
    def get_mapping_info(self, course_code: str) -> Optional[str]:
        """
        과목이 바뀌었는지 확인하고 정보 반환 (전체 체인)
        
        Returns:
            "CS0116 컴퓨터그래픽스 → CS0612 컴퓨터그래픽스 (동일) → CS0863 HCI(AR/VR/XR) (대체)"
        """
        history = self.get_course_history(course_code)
        
        if len(history) <= 1:
            return None
        
        return self.format_course_history(course_code)
    
    def get_all_equivalents(self) -> List[Dict]:
        """모든 대체 과목 조회"""
        try:
            result = supabase.table('equivalent_courses')\
                .select('*')\
                .execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ 전체 대체 과목 조회 실패: {e}")
            return []


# 전역 서비스
equivalent_course_service = EquivalentCourseService()