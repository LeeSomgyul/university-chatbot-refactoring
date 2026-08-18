//챗봇 응답 DB 연동 서비스

interface ChatbotResponse {
    message: string;                // 챗봇 응답 메시지
    sources?: string[];             // 참고 자료
    query_type?: string;            // 쿼리 타입
    session_id: string;             // 세션 ID
}

interface ChatbotRequest {
    message: string;
    session_id?: string | null;
    user_profile?: Record<string, unknown>;
}

interface UserContext {
    userId?: string;
    sessionId: string | undefined;
    previousMessages?: Array<{
        message: string;
        timestamp: Date;
        type: 'user' | 'bot';
    }>;
}

/**
 * 챗봇 응답을 위한 서비스 클래스
 */
export class ChatbotService {
    private static readonly API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    
    /**
     * 사용자 메시지에 대한 챗봇 응답
     * @param message 사용자 메시지
     * @param context 사용자 컨텍스트
     * @returns 챗봇 응답
     */
    static async getChatbotResponse(
        message: string, 
        context?: UserContext
    ): Promise<string> {
        try {
            const requestBody: ChatbotRequest = {
                message: message.trim(),
                session_id: context?.sessionId || undefined
            };

            const response = await fetch(`${this.API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result: ChatbotResponse = await response.json();
            
            // 세션 ID를 컨텍스트에 저장 (다음 요청에 사용)
            if (context && result.session_id) {
                context.sessionId = result.session_id;
            }

            return result.message;
            
        } catch (error) {
            console.error('챗봇 API 호출 중 오류:', error);
            
            // 에러 발생 시 기본 응답 반환
            return this.getFallbackResponse(message);
        }
    }

    /**
     * 챗봇 응답 상세 정보 (sources 포함)
     * @param message 사용자 메시지
     * @param context 사용자 컨텍스트
     * @returns 상세 챗봇 응답
     */
    static async getDetailedChatbotResponse(
        message: string, 
        context?: UserContext
    ): Promise<ChatbotResponse> {
        try {
            const requestBody: ChatbotRequest = {
                message: message.trim(),
                session_id: context?.sessionId || null
            };

            const response = await fetch(`${this.API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result: ChatbotResponse = await response.json();
            
            return result;
            
        } catch (error) {
            console.error('상세 챗봇 API 호출 중 오류:', error);
            
            // 에러 발생 시 기본 응답 반환
            return {
                message: this.getFallbackResponse(message),
                session_id: context?.sessionId || 'error'
            };
        }
    }

    /**
     * 세션 생성
     * @returns 새 세션 ID
     */
    static async createSession(): Promise<string> {
        try {
            const response = await fetch(`${this.API_BASE_URL}/session/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result.session_id;
            
        } catch (error) {
            console.error('세션 생성 중 오류:', error);
            // 임시 세션 ID 생성
            return `temp_${Date.now()}`;
        }
    }

    /**
     * API 호출 실패 시 사용할 기본 응답
     * @param message 사용자 메시지
     * @returns 기본 응답
     */
    private static getFallbackResponse(message: string): string {
        const lowerMessage = message.toLowerCase();
        
        // 대학 관련 키워드 기반 기본 응답
        if (lowerMessage.includes('졸업') || lowerMessage.includes('학점')) {
            return '졸업 요건에 대한 질문이시군요. 현재 서비스 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요.';
        } else if (lowerMessage.includes('교과과정') || lowerMessage.includes('수업')) {
            return '교과과정 관련 질문이시군요. 현재 서비스 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요.';
        } else if (lowerMessage.includes('안녕') || lowerMessage.includes('hello')) {
            return '안녕하세요! 순천대학교 챗봇입니다. 무엇을 도와드릴까요?';
        } else if (lowerMessage.includes('감사') || lowerMessage.includes('고마')) {
            return '천만에요! 또 다른 도움이 필요하시면 언제든 말씀해주세요.';
        } else {
            return '죄송합니다. 현재 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.';
        }
    }

    /**
     * 대화 기록 저장 (선택사항)
     */
    static async saveChatHistory(sessionId: string): Promise<void> {
    console.log('Chat history saved to session:', sessionId);
}
}

export const createChatbotResponseFetcher = (sessionId: string, userId?: string) => {
    return async (message: string): Promise<string> => {
        const context: UserContext = {
            sessionId,
            userId
        };
        
        const response = await ChatbotService.getChatbotResponse(message, context);
        
        // 대화기록은 백엔드에서 자동 저장
        
        return response;
    };
};