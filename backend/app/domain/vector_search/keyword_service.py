# ===============================================
# [서비스] SearchGeneral_handler.py에서 사용하는 함수들
# ===============================================
# documents 테이블에서 content_tsv을 보고 키워드 검색

from typing import List, Optional
from app.database.supabase_client import supabase
from app.models.schemas import KeywordSearchResult
from app.domain.vector_search.content_tokenizer import extract_content_morpheme

# [보조 함수] 사용자의 질문을 documents 테이블의 content_tsv가 이해할 수 있는 형식으로 변경
# - text: 사용자 입력 (예: CS0857 몇 학년에 들어?)
def _build_tsquery(text: str) -> str:
    # 1. 형태소 분석 (예: CS 0857 학년)
    morphemes = extract_content_morpheme(text)
    tokens = morphemes.split()
    
    if not tokens:
        return ""
    
    # 2. 출력 (예: CS | 0857 | 학년)
    return " | ".join(tokens)


# [메인 함수] 키워드 검색
# - query: 사용자의 질문 텍스트 
# - k: 검색 결과로 가져올 상위 문서(유사한 것) 개수 
# - category_filter: 카테고리 필터 
def search(
    query: str, 
    k: int = 10,
    category_filter: Optional[str] = None
) -> List[KeywordSearchResult]:
    
    # 1. 사용자의 질문을 documents 테이블의 content_tsv가 이해할 수 있는 형식으로 변경
    tsquery_str = _build_tsquery(query)
    
    if not tsquery_str:
        return []
    
    # 2. Supabase RPC 호출
    # supabase에 만들어둔 match_documents_keyword SQL문 실행하여, 
    # 사용자 질문에 대해 키워드 매칭 검사 후 DB에서 값 찾아오기 
    filter_json = {}
    if category_filter:
        filter_json = {"category": category_filter}
        
    try:
        # 2-1. 찾아온 결과 1개 
        result = supabase.rpc(
            'match_documents_keyword',
            {
                'query_tsquery': tsquery_str,
                'match_count': k,
                'filter': filter_json
            }
        ).execute()
        
        # 2-2. 결과 묶음 
        raw_results = result.data if result.data else []
        return [KeywordSearchResult(**row) for row in raw_results]
    except Exception as e:
        print(f"❌ 키워드 검색 실패: {e}")
        return []