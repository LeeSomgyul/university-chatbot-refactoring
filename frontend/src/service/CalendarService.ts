// frontend/src/service/calendarService.ts

interface CalendarEvent {
    title: string;
    start_date: string;
    end_date: string;
    category?: string;
    description?: string;
}

interface CalendarResponse {
    year: number;
    month: number;
    events: CalendarEvent[];
    total: number;
}

interface CalendarApiResponse {
    success: boolean;
    data: CalendarResponse;
    message?: string;
}

/**
 * 📅 학사일정 서비스
 */
export class CalendarService {
    private static readonly API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/calendar`;

    /**
     * 이번 달 학사일정 가져오기
     */
    static async getCurrentMonthCalendar(): Promise<CalendarResponse> {
        try {
            const response = await fetch(`${this.API_BASE_URL}/current-month`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result: CalendarApiResponse = await response.json();

            if (!result.success) {
                throw new Error(result.message || '학사일정 데이터를 가져오는데 실패했습니다.');
            }

            return result.data;

        } catch (error) {
            console.error('학사일정 API 호출 중 오류:', error);
            throw error;
        }
    }

    /**
     * 특정 연도/월 학사일정 가져오기
     */
    static async getMonthCalendar(year: number, month: number): Promise<CalendarResponse> {
        try {
            const response = await fetch(`${this.API_BASE_URL}/month/${year}/${month}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result: CalendarApiResponse = await response.json();

            if (!result.success) {
                throw new Error(result.message || '학사일정 데이터를 가져오는데 실패했습니다.');
            }

            return result.data;

        } catch (error) {
            console.error('학사일정 API 호출 중 오류:', error);
            throw error;
        }
    }

    /**
     * 학사일정을 텍스트로 포맷팅
     */
    static formatCalendarToText(data: CalendarResponse): string {
        const { year, month, events } = data;

        if (events.length === 0) {
            return `${year}년 ${month}월에는 등록된 학사일정이 없습니다.`;
        }

        let text = `📅 ${year}년 ${month}월 학사일정\n\n`;

        events.forEach((event, index) => {
            text += `${event.title}\n`;
            
            // 날짜 형식 변환: "2024-12-28" → "2024.12.28"
            const formattedStartDate = event.start_date.replace(/-/g, '.');
            text += `${formattedStartDate}`;
            
            if (event.end_date && event.end_date !== event.start_date) {
                const formattedEndDate = event.end_date.replace(/-/g, '.');
                text += ` ~ ${formattedEndDate}`;
            }
            
            // 마지막 항목이 아니면 줄바꿈 2번
            if (index < events.length - 1) {
                text += '\n\n';
            }
        });

        return text;
    }
}