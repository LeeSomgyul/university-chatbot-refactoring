
from typing import Dict, List, Optional
from app.database.supabase_client import supabase


class EquivalentCourseServiceOptimized:
    """동일대체교과목 관리 - 최적화 버전"""
    
    def __init__(self):
        # 메모리 캐시
        self._equivalents_cache: Dict[str, Dict] = {}  # {old_code: {new_code, name, type, ...}}
        self._reverse_cache: Dict[str, List[str]] = {}  # {new_code: [old_codes]}
        self._course_chains: Dict[str, List[str]] = {}  # {code: [code1, code2, ...]}
        self._is_loaded = False
        
    def load_all_equivalents(self):
        """앱 시작 시 모든 동일대체 정보를 메모리에 로드"""
        if self._is_loaded:
            return
        
        try:
            result = supabase.table('equivalent_courses')\
                .select('*')\
                .execute()
            
            if not result.data:
                print("⚠️ 동일대체 정보 없음")
                self._is_loaded = True
                return
            
            # 1. 기본 매핑 구축
            for row in result.data:
                old_code = row['old_course_code']
                new_code = row['new_course_code']
                
                self._equivalents_cache[old_code] = {
                    'new_course_code': new_code,
                    'new_course_name': row.get('new_course_name', ''),
                    'mapping_type': row.get('mapping_type', ''),
                    'allow_duplicate': row.get('allow_duplicate', False),
                    'allow_retake': row.get('allow_retake', True)
                }
                
                # 역방향 매핑
                if new_code not in self._reverse_cache:
                    self._reverse_cache[new_code] = []
                self._reverse_cache[new_code].append(old_code)
            
            # 2. 체인 구축 (CS0116 → CS0612 → CS0863)
            all_codes = set(self._equivalents_cache.keys()) | set(self._reverse_cache.keys())
            
            for code in all_codes:
                chain = self._build_chain(code)
                self._course_chains[code] = chain
            
            self._is_loaded = True
            
        except Exception as e:
            print(f"❌ 동일대체 정보 로드 실패: {e}")
            self._is_loaded = True
    
    def _build_chain(self, start_code: str, max_depth: int = 10) -> List[str]:
        """특정 코드의 전체 체인 구축 (순환 참조 방지)"""
        chain = [start_code]
        visited = {start_code}
        current = start_code
        
        # 순방향 체인 (old → new)
        depth = 0
        while depth < max_depth:
            if current in self._equivalents_cache:
                next_code = self._equivalents_cache[current]['new_course_code']
                if next_code in visited:
                    break
                chain.append(next_code)
                visited.add(next_code)
                current = next_code
                depth += 1
            else:
                break
        
        # 역방향 체인 (new → old)
        current = start_code
        reverse_chain = []
        depth = 0
        while depth < max_depth:
            if current in self._reverse_cache:
                for old_code in self._reverse_cache[current]:
                    if old_code not in visited:
                        reverse_chain.append(old_code)
                        visited.add(old_code)
                        current = old_code
                        break
                else:
                    break
                depth += 1
            else:
                break
        
        # 역방향 체인을 앞에 추가
        return list(reversed(reverse_chain)) + chain

    # ⭕사용
    # [두 과목 코드가 동일/대체 과목인지 판단]
    # 예) CS0852의 체인: [CS0601, CS0852, CS0856]  (기초설계→모바일프로그래밍→모바일프로그래밍
    # 예) CS0856의 체인: [CS0601, CS0852, CS0856]
    # 예) 결과: CS0852와 CS0856가 같은 체인에 속하기 때문에 동일/대체 교과목이라고 판단
    def is_equivalent(self, code1: str, code2: str) -> bool:
        # 1. 초기 로드 확인
        if not self._is_loaded:
            self.load_all_equivalents()
        
        if code1 == code2:
            return True
        
        # 2. 체인 조회
        chain1 = self._course_chains.get(code1, [code1])
        chain2 = self._course_chains.get(code2, [code2])
        
        # 3. 두 체인에 공통 코드가 있으면 동일/대체
        return bool(set(chain1) & set(chain2))

    # ⭕사용
    def get_equivalent_course(
        self, 
        course_code: str,
        direction: str = "old_to_new"
    ) -> Optional[Dict]:
        """대체 과목 조회 (메모리 기반)"""
        if not self._is_loaded:
            self.load_all_equivalents()
        
        if direction == "old_to_new":
            return self._equivalents_cache.get(course_code)
        else:  # new_to_old
            if course_code in self._reverse_cache:
                old_codes = self._reverse_cache[course_code]
                if old_codes:
                    # 첫 번째 구 코드 반환
                    old_code = old_codes[0]
                    equiv = self._equivalents_cache.get(old_code)
                    if equiv:
                        return {
                            'old_course_code': old_code,
                            'new_course_code': course_code,
                            'mapping_type': equiv['mapping_type']
                        }
            return None
    
    def get_latest_course_code(self, course_code: str) -> str:
        """최신 과목 코드 찾기 (메모리 기반)"""
        if not self._is_loaded:
            self.load_all_equivalents()
        
        chain = self._course_chains.get(course_code, [course_code])
        return chain[-1]  # 체인의 마지막이 최신 코드
    
    def get_all_equivalent_codes(self, course_code: str) -> List[str]:
        """특정 과목의 모든 동일/대체 과목 코드 목록 (메모리 기반)"""
        if not self._is_loaded:
            self.load_all_equivalents()
        
        return self._course_chains.get(course_code, [course_code])
    
    def get_course_history(self, course_code: str, max_depth: int = 10) -> List[Dict]:
        """
        과목 변경 이력 전체 조회 (메모리 기반)
        
        Returns:
            [
                {"code": "CS0116", "name": "컴퓨터그래픽스", "mapping_type": None},
                {"code": "CS0612", "name": "컴퓨터그래픽스", "mapping_type": "동일"},
                {"code": "CS0863", "name": "HCI(AR/VR/XR)", "mapping_type": "대체"}
            ]
        """
        if not self._is_loaded:
            self.load_all_equivalents()
        
        chain = self._course_chains.get(course_code, [course_code])
        history = []
        
        for i, code in enumerate(chain):
            if i == 0:
                # 시작 과목
                course_info = self._get_course_info(code)
                history.append({
                    "code": code,
                    "name": course_info['name'] if course_info else "알 수 없음",
                    "mapping_type": None
                })
            else:
                # 변경된 과목
                prev_code = chain[i-1]
                equiv = self._equivalents_cache.get(prev_code)
                if equiv:
                    history.append({
                        "code": code,
                        "name": equiv['new_course_name'],
                        "mapping_type": equiv['mapping_type']
                    })
        
        return history
    
    def format_course_history(self, course_code: str) -> str:
        """과목 변경 이력을 사용자 친화적으로 표시"""
        history = self.get_course_history(course_code)
        
        if len(history) <= 1:
            return f"{course_code} (변경 이력 없음)"
        
        parts = []
        for i, item in enumerate(history):
            if i == 0:
                parts.append(f"{item['code']} {item['name']}")
            else:
                mapping = f"({item['mapping_type']})" if item['mapping_type'] else ""
                parts.append(f"{item['code']} {item['name']} {mapping}")
        
        return " → ".join(parts)
    
    def _get_course_info(self, course_code: str) -> Optional[Dict]:
        """curriculums 테이블에서 과목 정보 조회 (캐싱 가능)"""
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
    
    def resolve_course_code(self, course_code: str) -> str:
        """과목 코드를 최신 코드로 변환"""
        return self.get_latest_course_code(course_code)

    # ⭕사용
    # [함수] 과목이 바뀐적 있는지 확인
    def get_mapping_info(self, course_code: str) -> Optional[str]:
        """과목이 바뀌었는지 확인하고 정보 반환"""
        history = self.get_course_history(course_code)
        
        if len(history) <= 1:
            return None
        
        return self.format_course_history(course_code)
    
    def get_all_equivalents(self) -> List[Dict]:
        """모든 대체 과목 조회 (메모리에서)"""
        if not self._is_loaded:
            self.load_all_equivalents()
        
        result = []
        for old_code, equiv_info in self._equivalents_cache.items():
            result.append({
                'old_course_code': old_code,
                'new_course_code': equiv_info['new_course_code'],
                'new_course_name': equiv_info['new_course_name'],
                'mapping_type': equiv_info['mapping_type']
            })
        return result


# 전역 서비스 (최적화 버전)
equivalent_course_service = EquivalentCourseServiceOptimized()

# 앱 시작 시 자동 로드
equivalent_course_service.load_all_equivalents()