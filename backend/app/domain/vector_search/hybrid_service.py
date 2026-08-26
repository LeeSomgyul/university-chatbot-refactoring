# ===============================================
# [서비스] SearchGeneral_handler.py에서 사용하는 함수들
# ===============================================
# 벡터 검색(vector_service.py)과 키워드 검색(keyword_service.py)에서 
# 각각 Top10을 뽑아서 RRF가 이 둘을 합산하여, 최종 Top3을 반환.

from typing import List, Optional
from collections import defaultdict
from app.domain.vector_search.vector_service import get_vector_service
from app.domain.vector_search.keyword_service import get_keyword_service
from app.models.schemas import HybridSearchResult, VectorSearchResult, KeywordSearchResult

RRF_K = 60
TOP_TEN = 10
TOP_THREE = 3

# [보조 함수] 벡터 or 키워드 순위를 RRF 공식으로 융합
def _reciprocal_rank_fusion(
    vector_results: List[VectorSearchResult],
    keyword_results: List[KeywordSearchResult],
) -> List[HybridSearchResult]:
    
    # 1. 벡터 검색, 키워드 검색에서 각각 TOP10로 뽑힌 데이터의 id, 점수
    scores: dict[int, float] = defaultdict(float)
    
    # 2. 각 검색 결과의 id, content, metadata 보관 (중복 데이터 제외)
    save_data: dict[int, tuple[str, dict]] = {}
    
    # 3. 각 데이터가 벡터 or 키워드 or 벡터+키워드 중 어디서 왔는지 (id, 벡터+키워드일 수 있어서 list)
    matched_by: dict[int, list[str]] = defaultdict(list)
    
    # 4. 벡터 Top10 검색 결과 등수 매기기
    for rank, result in enumerate(vector_results, start=1):
        # RRF 공식: 1 / (기본값 60 + 내 등수)
        scores[result.id] += 1 / (RRF_K + rank)
        
        # 문서 내용 저장
        save_data.setdefault(result.id, (result.content, result.metadata))
        
        # 벡터 검색에서 찾은 문서라고 저장 
        matched_by[result.id].append("vector")
        
    # 5. 키워드 Top10 검색 결과 등수 매기기
    for rank, result in enumerate(keyword_results, start=1):
        scores[result.id] += 1 / (RRF_K + rank)
        save_data.setdefault(result.id, (result.content, result.metadata))
        matched_by[result.id].append("keyword")
        
    # 6. 둘 합쳐서 반환
    merged = [
        HybridSearchResult(
            id=doc_id,
            content=save_data[doc_id][0],
            metadata=save_data[doc_id][1],
            rrf_score=score,
            matched_by=matched_by[doc_id],
        )
        for doc_id, score in scores.items()
    ]
    
    # 7. 문서에 대한 점수만 추출
    merged.sort(key=lambda r:r.rrf_score, reverse=True)
    return merged


# [메인 함수] 벡터 + 키워드 검색 RRF 융합
def get_hybrid_service(
    query: str, 
    k: int = TOP_THREE,
    category_filter: Optional[str] = None,
) -> List[HybridSearchResult]:

    # 1. 벡터 서비스 결과값 가져오기
    vector_service = get_vector_service()
    
    vector_result = vector_service.search(
        query=query,
        k=TOP_TEN,
        category_filter=category_filter
    )
    
    # 2. 키워드 서비스 결과값 가져오기
    keyword_result = get_keyword_service(
        query=query,
        k=TOP_TEN,
        category_filter=category_filter
    )
    
    # 3. 합치기 결과
    combine_result = _reciprocal_rank_fusion(vector_result, keyword_result)
    
    # 4. RRF 점수로 합쳐진것 중 Top3만 추출
    return combine_result[:k]