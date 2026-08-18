"""
벡터 검색 서비스
"""
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from app.config import settings
from app.database.supabase_client import supabase


class VectorSearchService:
    """벡터 검색 서비스"""
    
    def __init__(self):
        print(f"🔧 임베딩 모델 로딩: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        print("✅ 모델 로딩 완료")
    
    def search(
        self, 
        query: str, 
        k: int = 3,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        벡터 검색 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            category_filter: 카테고리 필터 (예: "도서관", "실험실")
        
        Returns:
            검색 결과 리스트
        """
        # 쿼리 임베딩 생성
        query_embedding = self.model.encode(query).tolist()
        
        # Supabase RPC 호출
        filter_json = {}
        if category_filter:
            filter_json = {"category": category_filter}
        
        try:
            result = supabase.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_count': k,
                    'filter': filter_json
                }
            ).execute()
            
            return result.data if result.data else []
        
        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            return []
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """검색 결과를 텍스트로 포맷팅"""
        if not results:
            return "관련 정보를 찾을 수 없습니다."
        
        formatted = []
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            content = result.get('content', '')
            
            formatted.append(
                f"[{i}] {metadata.get('title', '제목없음')}\n{content}\n"
            )
        
        return "\n".join(formatted)


# 전역 서비스 (앱 시작 시 한 번만 로드)
vector_service = None


def get_vector_service() -> VectorSearchService:
    """벡터 서비스 싱글톤"""
    global vector_service
    if vector_service is None:
        vector_service = VectorSearchService()
    return vector_service