# ===============================================
#   Embedding Model 싱글톤 초기화(메모리 등록)
# ===============================================

from sentence_transformers import SentenceTransformer
from app.config import settings

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    
    if _embedding_model is None:
        print(f"✔️ 임베딩 모델 로딩중...: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
        print("✅ 임베딩 모델 로딩 완료")
        
    return _embedding_model