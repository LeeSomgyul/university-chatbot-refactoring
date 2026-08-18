// 🔍 FastAPI 백엔드 연동 자동완성 서비스

// 📝 FAQ 아이템 타입 정의 (JSON 구조와 일치)
export interface FAQItem {
    id: number;
    question: string;
    answer_type: string;
    answer_content: string | null;
    parent_id: number | null;
    autocomplete: boolean;
    card_priority: number | null;
    title: string;
}

// 📝 자동완성 응답 타입 정의
interface AutoCompleteResponse {
    suggestions: FAQItem[];
    total: number;
}

// 🔗 API 응답 타입 정의
interface ApiResponse {
    success: boolean;
    data: AutoCompleteResponse;
    message?: string;
}

/**
 * 🔍 FastAPI 백엔드에서 자동완성 데이터를 가져오는 서비스 클래스
 */
export class AutoCompleteService {
    // 백엔드 API URL
    private static readonly API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/autocomplete`
    
    /**
     * 🔍 검색어를 기반으로 자동완성 제안을 가져옵니다
     * @param query 검색어
     * @param limit 가져올 결과 수 (기본 10개)
     * @returns 자동완성 제안 배열
     */
    static async fetchSuggestions(query: string, limit: number = 10): Promise<FAQItem[]> {
        try {
            // 빈 검색어면 빈 배열 반환
            if (!query || query.trim().length === 0) {
                return [];
            }

            const params = new URLSearchParams({
                q: query.trim(),
                limit: limit.toString()
            });
            
            const response = await fetch(`${this.API_BASE_URL}/search?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result: ApiResponse = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || '자동완성 데이터를 가져오는데 실패했습니다.');
            }

            return result.data.suggestions;
            
        } catch (error) {
            console.error('자동완성 API 호출 중 오류:', error);
            // 에러 발생 시 빈 배열 반환 (기본 동작 유지)
            return [];
        }
    }

    /**
     * 🔍 질문 텍스트만 반환하는 간단한 버전 (기존 호환성)
     * @param query 검색어
     * @param limit 가져올 결과 수 (기본 10개)
     * @returns 질문 텍스트 배열
     */
    static async fetchSuggestionTexts(query: string, limit: number = 10): Promise<string[]> {
        const suggestions = await this.fetchSuggestions(query, limit);
        return suggestions.map(item => item.question);
    }
    
    /**
     * 🔍 parent_id로 자식 질문들 가져오기
     * @param parentId 부모 질문 ID
     * @returns 자식 질문 배열
     */
    static async fetchChildrenByParentId(parentId: number): Promise<FAQItem[]> {
        try {
            const response = await fetch(`${this.API_BASE_URL}/children/${parentId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || '자식 질문 데이터를 가져오는데 실패했습니다.');
            }

            return result.data.children;
            
        } catch (error) {
            console.error('자식 질문 API 호출 중 오류:', error);
            return [];
        }
    }
}

// 🎯 헬퍼 함수: 자동완성 fetcher 생성 (전체 객체 반환)
export const createAutoCompleteFetcher = () => {
    return async (query: string): Promise<FAQItem[]> => {
        return await AutoCompleteService.fetchSuggestions(query);
    };
};

// 🎯 헬퍼 함수: 자동완성 fetcher 생성 (텍스트만 반환 - 기존 호환성)
export const createAutoCompleteTextFetcher = () => {
    return async (query: string): Promise<string[]> => {
        return await AutoCompleteService.fetchSuggestionTexts(query);
    };
};