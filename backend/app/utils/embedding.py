# 텍스트를 벡터로 변경해주는 임베딩 모델 로드/실행 도구
from sentence_transformers import SentenceTransformer
from app.config import settings

_embedding_model = None

def get_embedding_model():
    """임베딩 모델 싱글톤 (강의평가/맛집 리뷰 공용)"""
    global _embedding_model

    # 임베딩 모델 로드 전
    if _embedding_model is None:
        print(f"임베딩 모델 로딩: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
        print("모델 로딩 완료")

    return _embedding_model