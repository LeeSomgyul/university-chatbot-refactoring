# ===============================================
# [서비스] SearchGeneral_handler.py에서 사용하는 함수들
# ===============================================

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.database.supabase_client import supabase
from app.models.schemas import VectorSearchResult


class VectorSearchService:    
    # [보조 함수] 임베딩 모델 1회 실행
    # 사용자가 입력한 질문을 -> 벡터 형식(숫자)로 바꿔주는 역할 
    # 매번 꺼내쓸 수 있도록 서버가 구동될 때 1회 실행시켜서 메모리에 올려두는 작업 
    def __init__(self):
        print(f"✔️ 임베딩 모델 로딩중...: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        print("✅ 모델 로딩 완료")


    # [메인 함수] 벡터 검색 
    # - query: 사용자의 질문 텍스트 
    # - k: 검색 결과로 가져올 상위 문서(유사한 것) 개수 
    # - category_filter: 카테고리 필터 
    def search(
        self, 
        query: str, 
        k: int = 3,
        category_filter: Optional[str] = None
    ) -> List[VectorSearchResult]:

        # 1. 사용자 질문(문자열)을 벡터(숫자) 형식으로 변환 
        query_embedding = self.model.encode(query).tolist()
        
        # 2. Supabase RPC 호출
        # supabase에 만들어둔 match_documents SQL문 실행하여, 
        # 사용자 질문에 대해 벡터 유사도 검사 후 DB에서 값 찾아오기 
        filter_json = {}
        if category_filter:
            filter_json = {"category": category_filter}
        
        try:
            # 2-1. 찾아온 결과 1개 
            result = supabase.rpc(
                'match_documents',                      # Supabase에 미리 만들어둔 SQL 함수의 이름
                {
                    'query_embedding': query_embedding, # 벡터 형식의 사용자 질문
                    'match_count': k,                   # 가져올 개수
                    'filter': filter_json               # 카테고리 필터
                }
            ).execute()

            # 2-2. 결과 묶음 
            raw_results = result.data if result.data else []

            # 2-3. 결과를 VectorSearchResult 형식에 주입 
            return [VectorSearchResult(**row) for row in raw_results]
        
        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            return []

    # [메인 함수] 벡터DB 결과를 사용자에게 전달할 텍스트 형식으로 다시 변환 
    def format_search_results(self, results: List[VectorSearchResult]) -> str:
        if not results:
            return "관련 정보를 찾을 수 없습니다."
        
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.metadata.get('title', '제목없음')
            
            formatted.append(
                f"[{i}] {title}\n{result.content}\n"
            )
        
        return "\n".join(formatted)


# [싱글톤] 저장 메모리 공간 (여기서 빼가서 씀)
vector_service = None

# [싱글톤] VectorSearchService 함수를 서버 구동 시 메모리에 1회 올려두고 다른데서 돌려쓰기 
def get_vector_service() -> VectorSearchService:
    global vector_service
    if vector_service is None:
        vector_service = VectorSearchService()
    return vector_service