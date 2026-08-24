import { useState } from "react";
import { RestaurantService } from "../service/RestaurantService";

interface RestaurantReviewFormProps {
    restaurant: {name: string, url: string} | null;
    onSubmitted: ()=> void;
}

export const RestaurantReviewForm = ({restaurant, onSubmitted}: RestaurantReviewFormProps) => {
    const [content, setContent] = useState<string>('');
    const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState<boolean>(false);

    if(!restaurant) return null

    const handleSubmit = async () => {
        if (!content.trim()) {
            setError('리뷰 내용을 입력해주세요');
            return;
        }
        setIsSubmitting(true);
        setError(null);

        try{
            await RestaurantService.createReview({
                restaurant,
                content: content.trim()
            })
            setContent('');
            onSubmitted();
            setSubmitted(true);
        }catch (err) {
            setError(err instanceof Error ? err.message : '오류가 발생했습니다');
        } finally {
            setIsSubmitting(false);
        }
    }

    if(submitted){
        return <div>리뷰가 등록되었습니다 !</div>
    }

    return (
        <div>
            <div onClick={(e)=>e.stopPropagation()}>
                <h3>{restaurant?.name} 리뷰 작성</h3>
                <textarea 
                    value={content}
                    onChange={(e)=>setContent(e.target.value)}
                    placeholder="이 가게에 대한 리뷰를 남겨주세요"
                    rows={4}
                />
                {error && <div className="text-red-500 font-sm">{error}</div>}
                <div>
                    <button onClick={handleSubmit} disabled={isSubmitting}>
                        {isSubmitting ? 'Loading...' : '등록'}
                    </button>
                </div>
            </div>
        </div>
    )
}