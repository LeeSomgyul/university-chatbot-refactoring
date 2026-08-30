# ===============================================
#   Embedding Client 싱글톤 초기화 (OpenAI API)
# ===============================================

from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential
from app.config import settings


class _EmbeddingArray(list):
    """numpy ndarray의 .tolist() 동작만 흉내내는 래퍼.
    기존 호출부가 encode(...).tolist() 또는 encode(...)[i].tolist() 형태로
    쓰고 있어서, numpy 의존성 없이 동일한 인터페이스를 유지하기 위함."""
    def tolist(self):
        return list(self)


class _EmbeddingClient:
    def __init__(self):
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError, APIConnectionError)),
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(5),
    )
    def _create(self, batch):
        return self._client.embeddings.create(
            model=self._model,
            input=batch,
            dimensions=self._dimensions,
        )

    def encode(self, texts, batch_size: int = 100, show_progress_bar: bool = False, **_):
        """SentenceTransformer.encode()와 동일한 인터페이스 유지.
        texts: 문자열 하나 또는 문자열 리스트 모두 허용."""
        is_single = isinstance(texts, str)
        items = [texts] if is_single else list(texts)

        chunk_starts = range(0, len(items), batch_size)
        if show_progress_bar:
            from tqdm import tqdm
            chunk_starts = tqdm(chunk_starts, desc="임베딩 생성중")

        vectors = []
        for i in chunk_starts:
            batch = items[i:i + batch_size]
            resp = self._create(batch)
            vectors.extend(_EmbeddingArray(d.embedding) for d in resp.data)

        return vectors[0] if is_single else _EmbeddingArray(vectors)


_embedding_model = None

def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        print(f"✔️ 임베딩 클라이언트 초기화중...: {settings.embedding_model}")
        _embedding_model = _EmbeddingClient()
        print("✅ 임베딩 클라이언트 초기화 완료")

    return _embedding_model