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
        return (
            <div>
                <span>리뷰가 등록되었습니다!</span>
            </div>
        )
    }

    return (
        <div
            onClick={(e)=>e.stopPropagation()} className="w-[30vw] mt-1 mx-2">
            <span className="inline-flex items-center mt-2 text-xs font-bold text-[#004C97] bg-[#BADDFE] rounded-full px-2 py-0.5">
                REVIEW
            </span>
            <h3 className="mb-3 text-lg font-bold text-[#004C97] truncate">{restaurant?.name}</h3>
            <textarea
                value={content}
                onChange={(e)=>setContent(e.target.value)}
                placeholder="맛, 분위기, 서비스 어땠나요?"
                rows={4}
                className="mb-1 w-full resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#BADDFE] focus:border-transparent"
            />
            {error && <div className="text-xs text-red-500">{error}</div>}
            <div className="flex justify-end">
                <button
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                    className="px-4 py-2 mb-2 rounded-xl bg-[#004C97] text-sm font-semibold text-white shadow-sm transition-colors hover:opacity-80 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isSubmitting ? 'Loading...' : '등록'}
                </button>
            </div>
        </div>
    )
}