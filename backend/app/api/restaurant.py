"""
식도락 리뷰 관련 API 엔드포인트
"""
from aiohttp.web_exceptions import HTTPException
from app.database.supabase_client import supabase
from app.models.schemas import RestaurantReviewCreate
from app.utils import embedding_client
from app.utils.embedding_client import get_embedding_model
from app.utils.llm_client import generate_review_summary
from fastapi import APIRouter,BackgroundTasks
from openai.types import embedding

# (싱글톤)임베딩 모델 로드
model = embedding_client.get_embedding_model()

router = APIRouter(
    prefix="/api/restaurant",
    tags=["restaurant"]
)

@router.post("/review/create")
async def create_restaurant_review(review: RestaurantReviewCreate, background_tasks: BackgroundTasks):
    if not review.content.strip():
        raise HTTPException(status_code=400, detail="리뷰 내용을 입력해주세요")

    try:
        saved = supabase.table('restaurant_reviews').insert({
            "place_url": review.place_url,
            "place_name": review.place_name,
            "content": review.content
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리뷰 저장 실패: {str(e)}")

    review_id=saved.data[0]['id']

    # [백그라운드 실행] 임베딩
    background_tasks.add_task(generate_and_save_embedding, review_id, review.content)
    # [백그라운드 실행] 리뷰 요약 갱신
    background_tasks.add_task(update_review_summary, review.place_url)


    return {
        "message": "리뷰가 등록되었습니다",
        "review_id": review_id
    }

# 고유 ID, 벡터로 변환할 텍스트
def generate_and_save_embedding(review_id: str, content: str):
    try:
        # 텍스트 -> 벡터 변환
        embedding = model.encode(content).tolist()
        # embedding 컬럼 값 : 벡터로 update
        supabase.table('restaurant_reviews').update({
            "embedding": embedding
        }).eq('id',review_id).execute()

        print(f"[EMBEDDING] 리뷰 {review_id} 임베딩 생성 완료 (차원: {len(embedding)})")
    except Exception as e:
        print(f"[EMBEDDING] 리뷰 {review_id} 임베딩 생성 실패 (차원: {e})")


# [보조메서드] 검색된 리뷰 원문 요약 갱신 함수
def update_review_summary(place_url:str):
    try:
        # 가게의 모든 리뷰 텍스트 조회
        result = supabase.table('restaurant_reviews') \
            .select('content') \
            .eq('place_url',place_url) \
            .execute()

        # 리뷰 개수 측정용?
        reviews = [r['content'] for r in result.data]
        if not reviews:
            return

        # LLM 리뷰 요약 프롬프트 호출
        summary = generate_review_summary(reviews)

        supabase.table('restaurant_review_summaries') \
            .upsert({
            "place_url": place_url,
            "summary": summary,
            "review_count": len(reviews)
        }).execute()

        print(f"[SUMMARY] {place_url} 요약 갱신 완료 (리뷰 {len(reviews)}개 기반)")
    except Exception as e:
        print(f"[SUMMARY] {place_url} 요약 갱신 실패: {e}")

