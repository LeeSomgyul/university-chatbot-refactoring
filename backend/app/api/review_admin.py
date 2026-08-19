"""
강의평가 승인 관리 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.database.supabase_client import supabase


router = APIRouter(prefix="/admin/reviews", tags=["Admin - Reviews"])


# ===== Schemas =====
class PendingReview(BaseModel):
    """대기 중인 후기"""
    id: str
    professor_name: str
    course_name: str
    course_code: Optional[str]
    semester: str
    teaching_style: str
    assignment_load: str
    exam_difficulty: str
    review_text: str
    status: str
    submitted_at: datetime


class ApproveRequest(BaseModel):
    """승인 요청"""
    reviewed_by: Optional[str] = "admin"


class RejectRequest(BaseModel):
    """거부 요청"""
    reviewed_by: Optional[str] = "admin"
    rejection_reason: str


# ===== 임베딩 모델 (싱글톤) =====
_embedding_model = None

def get_embedding_model():
    """임베딩 모델 싱글톤"""
    global _embedding_model
    if _embedding_model is None:
        print(f"🔧 임베딩 모델 로딩: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
        print("✅ 모델 로딩 완료")
    return _embedding_model


# ===== API Endpoints =====

@router.get("/pending", response_model=List[PendingReview])
async def get_pending_reviews(limit: int = 50):
    """
    승인 대기 중인 후기 조회
    
    Args:
        limit: 조회할 최대 개수 (기본 50개)
    """
    try:
        result = supabase.table('pending_reviews')\
            .select('*')\
            .eq('status', 'pending')\
            .order('submitted_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"후기 조회 실패: {str(e)}"
        )


@router.get("/all")
async def get_all_reviews(
    status: Optional[str] = None,
    limit: int = 100
):
    """
    모든 후기 조회 (필터링 가능)
    
    Args:
        status: 상태 필터 (pending/approved/rejected)
        limit: 조회할 최대 개수
    """
    try:
        query = supabase.table('pending_reviews').select('*')
        
        if status:
            query = query.eq('status', status)
        
        result = query.order('submitted_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "total": len(result.data),
            "reviews": result.data
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"후기 조회 실패: {str(e)}"
        )


@router.post("/{review_id}/approve")
async def approve_review(review_id: str, request: ApproveRequest):
    """
    후기 승인 및 course_reviews에 저장
    
    1. pending_reviews에서 후기 조회
    2. 임베딩 생성
    3. course_reviews에 저장
    4. pending_reviews 상태 업데이트
    """
    try:
        # 1. pending_reviews에서 후기 조회
        result = supabase.table('pending_reviews')\
            .select('*')\
            .eq('id', review_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="후기를 찾을 수 없습니다")
        
        review = result.data[0]
        
        # 이미 승인된 후기인지 체크
        if review['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"이미 처리된 후기입니다 (상태: {review['status']})"
            )
        
        print(f"✅ 후기 승인 시작: {review['course_name']} - {review['professor_name']}")
        
        # 2. 임베딩 생성
        model = get_embedding_model()
        review_text = review['review_text']
        embedding = model.encode(review_text).tolist()
        
        print(f"  ✅ 임베딩 생성 완료 (차원: {len(embedding)})")
        
        # 3. course_reviews에 저장
        approved_review = {
            "professor_name": review['professor_name'],
            "course_name": review['course_name'],
            "course_code": review['course_code'],
            "semester": review['semester'],
            "teaching_style": review['teaching_style'],
            "assignment_load": review['assignment_load'],
            "exam_difficulty": review['exam_difficulty'],
            "review_text": review_text,
            "embedding": embedding,
            "metadata": {
                "approved_by": request.reviewed_by,
                "approved_at": datetime.now().isoformat()
            },
            "pending_review_id": review_id
        }
        
        approved_result = supabase.table('course_reviews')\
            .insert(approved_review)\
            .execute()
        
        print(f"  ✅ course_reviews에 저장 완료")
        
        # 4. pending_reviews 상태 업데이트
        supabase.table('pending_reviews')\
            .update({
                "status": "approved",
                "reviewed_by": request.reviewed_by,
                "reviewed_at": datetime.now().isoformat()
            })\
            .eq('id', review_id)\
            .execute()
        
        print(f"  ✅ pending_reviews 상태 업데이트 완료")
        print(f"🎉 승인 완료!")
        
        return {
            "message": "후기가 승인되었습니다",
            "review_id": review_id,
            "course_review_id": approved_result.data[0]['id']
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 승인 실패: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"승인 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/{review_id}/reject")
async def reject_review(review_id: str, request: RejectRequest):
    """
    후기 거부
    
    Args:
        review_id: 후기 ID
        request: 거부 사유 포함
    """
    try:
        # 1. 후기 존재 확인
        result = supabase.table('pending_reviews')\
            .select('*')\
            .eq('id', review_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="후기를 찾을 수 없습니다")
        
        review = result.data[0]
        
        if review['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"이미 처리된 후기입니다 (상태: {review['status']})"
            )
        
        # 2. 상태 업데이트
        supabase.table('pending_reviews')\
            .update({
                "status": "rejected",
                "reviewed_by": request.reviewed_by,
                "reviewed_at": datetime.now().isoformat(),
                "rejection_reason": request.rejection_reason
            })\
            .eq('id', review_id)\
            .execute()
        
        print(f"❌ 후기 거부: {review['course_name']} - {review['professor_name']}")
        print(f"  사유: {request.rejection_reason}")
        
        return {
            "message": "후기가 거부되었습니다",
            "review_id": review_id,
            "rejection_reason": request.rejection_reason
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 거부 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"거부 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.delete("/{review_id}")
async def delete_review(review_id: str):
    """
    후기 삭제 (영구 삭제)
    
    주의: 승인된 후기는 course_reviews에서도 삭제해야 함
    """
    try:
        # 1. 후기 조회
        result = supabase.table('pending_reviews')\
            .select('*')\
            .eq('id', review_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="후기를 찾을 수 없습니다")
        
        review = result.data[0]
        
        # 2. 승인된 후기라면 course_reviews에서도 삭제
        if review['status'] == 'approved':
            supabase.table('course_reviews')\
                .delete()\
                .eq('pending_review_id', review_id)\
                .execute()
        
        # 3. pending_reviews에서 삭제
        supabase.table('pending_reviews')\
            .delete()\
            .eq('id', review_id)\
            .execute()
        
        print(f"🗑️ 후기 삭제: {review['course_name']} - {review['professor_name']}")
        
        return {
            "message": "후기가 삭제되었습니다",
            "review_id": review_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 삭제 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"삭제 처리 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/stats")
async def get_review_stats():
    """
    후기 통계
    """
    try:
        # pending 개수
        pending = supabase.table('pending_reviews')\
            .select('id', count='exact')\
            .eq('status', 'pending')\
            .execute()
        
        # approved 개수
        approved = supabase.table('pending_reviews')\
            .select('id', count='exact')\
            .eq('status', 'approved')\
            .execute()
        
        # rejected 개수
        rejected = supabase.table('pending_reviews')\
            .select('id', count='exact')\
            .eq('status', 'rejected')\
            .execute()
        
        # course_reviews 총 개수
        total_reviews = supabase.table('course_reviews')\
            .select('id', count='exact')\
            .execute()
        
        return {
            "pending": pending.count,
            "approved": approved.count,
            "rejected": rejected.count,
            "total_in_db": total_reviews.count
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 실패: {str(e)}"
        )