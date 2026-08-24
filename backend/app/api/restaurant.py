"""
식도락 리뷰 관련 API 엔드포인트
"""
from aiohttp.web_exceptions import HTTPException
from app.database.supabase_client import supabase
from app.models.schemas import RestaurantReviewCreate
from app.utils.embedding import get_embedding_model
from fastapi import APIRouter,BackgroundTasks

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

    # 임베딩 백그라운드 실행
    background_tasks.add_task(generate_and_save_embedding, review_id, review.content)

    return {
        "message": "리뷰가 등록되었습니다",
        "review_id": review_id
    }

# 고유 ID, 벡터로 변환할 텍스트
def generate_and_save_embedding(review_id: str, content: str):
    try:
        # (싱글톤)임베딩 모델 로드
        model = get_embedding_model()
        # 텍스트 -> 벡터 변환
        embedding = model.encode(content).tolist()
        # embedding 컬럼 값 : 벡터로 update
        supabase.table('restaurant_reviews').update({
            "embedding": embedding
        }).eq('id',review_id).execute()

        print(f"[EMBEDDING] 리뷰 {review_id} 임베딩 생성 완료 (차원: {len(embedding)})")
    except Exception as e:
        print(f"[EMBEDDING] 리뷰 {review_id} 임베딩 생성 실패 (차원: {e})")

