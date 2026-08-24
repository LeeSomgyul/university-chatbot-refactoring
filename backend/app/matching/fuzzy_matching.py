# ===============================================
# [4단계] Fuzzy Matching을 통해 오타, 줄임말 대응
# ===============================================
# - 역할: 형태소 분석에서 해결하지 못한 오타, 줄임말 교과목들을 유사도 점수로 매칭한다.

from typing import NamedTuple, List, Optional
from rapidfuzz import process, fuzz
from app.matching.normalize import normalize
from app.matching.course_caching import get_normalized_course_list

# [find_fuzzy_match 결과 DTO]
class FuzzyMatch(NamedTuple):
    matched_name: str       # 매칭 성공한 과목명 결과
    course_codes: List[str] # 해당 과목명에 해당하는 과목 코드
    score: float            # 유사도 점수

# [메인 함수 1] 4단계 Fuzzy Matching 실행
# - text: 오타 또는 줄임말이 포함(정규화 완료)된 사용자가 입력한 문장
# - threshold: 같은 단어라고 인정할 기준값
def find_fuzzy_match(text: str, threshold: int = 80) -> Optional[FuzzyMatch]:

    normalize_text = normalize(text)             # 혹시 몰라서 한번 더 정규화(공백, 마침표 제거)
    name_to_codes = get_normalized_course_list() # 캐싱되어있는 {"과목명": ["과목코드", "과목코드"], ...}
    
    if not name_to_codes:
        return None
    
    # 1. 캐싱 데이터에서 과목명만 추출
    # 예: ["과목명", "과목명", ...]
    all_course_names = list(name_to_codes.keys())
    
    # 2. Fuzzy Matching로 가장 유사한 단어 추출 (.extractOne = 유사도 검사 메서드)
    result = process.extractOne(
        normalize_text,           # 유사도 검색 대상
        all_course_names,         # 비교할 데이터 (정답)
        scorer=fuzz.partial_ratio # 유사도 점수
    )
    
    if result is None:
        return None
    
    # 3. 결과 변수 저장
    # matched_name: 가장 유사한 정답
    # score: 유사도 점수 
    # _ : 원본의 유사한 정답 인덱스 (필요 없어서 _로 대체)
    matched_name, score, _ = result
    
    # 4. 유사도 점수가 80점 이하면 None 반환
    if score < threshold:
        return None
    
    # 5. 유사도 점수가 80점 이상이면 결과 반환 
    return FuzzyMatch(
        matched_name=matched_name,
        course_codes=name_to_codes[matched_name],
        score=score
    )
    
    
# [find_fuzzy_llm_candidates 결과 DTO]    
class FuzzLLMCandidate(NamedTuple):
    matched_name: str
    course_codes: List[str]
    score: float    
    
# [메인 함수 2] 5단계 LLM 활용에서 사용될 비슷한 과목명 5개 추출 
# - 역할: 최후 방법인 LLM 방식으로 동일/대체 교과목을 찾을 때 전체 캐싱 데이터에서 찾으면 토큰 비용이 
#        많이 들기 때문에 Fuzzy Matching으로 그나마 비슷한 단어 5개를 추출한 뒤, 거기서 비교하도록 한다.
def find_fuzzy_llm_candidates(text: str, num: int = 5) -> List[FuzzLLMCandidate]:
    normalize_text = normalize(text)
    name_to_codes = get_normalized_course_list()
    
    if not name_to_codes:
        return []
    
    all_course_names = list(name_to_codes.keys())
    
    # Fuzzy Matching로 비슷한 단어 5개 추출
    results = process.extract(
        normalize_text,
        all_course_names,
        scorer=fuzz.partial_ratio,
        limit=num
    )
    
    return [
        FuzzLLMCandidate(
            matched_name=matched_name,
            course_codes=name_to_codes[matched_name],
            score=score
        )
        for matched_name, score, _ in results
    ]