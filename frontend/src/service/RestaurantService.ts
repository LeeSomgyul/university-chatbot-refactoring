interface CreateReviewRequest {
    restaurant: {name: string, url: string}
    content: string;
}
interface CreateReviewResponse {
    message: string;
    review_id: string;
}


export class RestaurantService {
    private static readonly API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/restaurant`;
    
    /**
     * 리뷰 작성 API 호출
     * @returns 리뷰 성공/실패 메시지
     */
    static async createReview({restaurant, content}:CreateReviewRequest): Promise<string> {
            const response = await fetch(`${this.API_BASE_URL}/review/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    place_url: restaurant.url,
                    place_name: restaurant.name,
                    content: content.trim(),
                }),
            });

            if (!response.ok) {
                throw new Error(`리뷰 등록에 실패했습니다 (status: ${response.status})`);
            }

            const result: CreateReviewResponse  = await response.json();
            return result.message;
    }
}
