import type { ReactNode } from "react";
import React from "react";


export interface FAQResponse {
    id: number;
    title: string;
    response: React.ReactNode;
    options?: string[];
    children?: FAQChild[];
}

export interface FAQChild {
    id: number;
    title: string;
    question: string;
    answer_type: string;
    answer_content: string | null;
    show_in_chat?: boolean;
    card_priority?: number | null;
    action_type?: string | null;
}

// FAQ 데이터 타입
export interface FAQItem {
    id: number;
    title: ReactNode;
    description: ReactNode;
    label?: string;
}

// 임시 FAQ 목록 (실제로는 서버에서 관리)
// 🔥 메인 FAQ 목록 (6개만)
export const FAQ_ITEMS: FAQItem[] = [
    {
        id: 1,
        label: "학사일정",
        title: (
            <span className="faq-title-inline">
                <img src="/icons/schedule.svg" alt="학사일정" className="faq-icon" />
                <span className="faq-title-text">학사일정</span>
            </span>
        ),
        description: (
            <div>
                학사일정이 궁금하신가요?<br />
                학사일정 페이지에서 등록, 수강, 시험, 휴복학, 졸업 등 연간 학사 일정을 확인할 수 있어요
            </div>
        )
    },
    {
        id: 4,
        label: "도서관",
        title: (
            <span className="faq-title-inline">
                <img src="/icons/library.svg" alt="도서관" className="faq-icon" />
                <span className="faq-title-text">도서관</span>
            </span>
        ),
        description: (
            <div>
                도서관 이용 시간, 예약 방법, 자료 검색 등 도서관 이용에 필요한 정보를 확인할 수 있어요.
            </div>
        )
    },
    {
        id: 32,
        label: "실험실",
        title: (
            <span className="faq-title-inline">
                <img src="/icons/lab.svg" alt="실험실" className="faq-icon" />
                <span className="faq-title-text">실험실</span>
            </span>
        ),
        description: (
            <div>
                실험실 안내 페이지에서 이용 시간, 예약 방법, 안전 수칙 등 실험실 이용에 필요한 정보를 확인할 수 있어요.
            </div>
        )
    },
    {
        id: 37,
        label: "장학정보",
        title: (
            <span className="faq-title-inline">
                <img src="/icons/scholarship.svg" alt="장학정보" className="faq-icon" />
                <span className="faq-title-text">장학정보</span>
            </span>
        ),
        description: (
            <div>
                장학금 신청 방법, 지급 일정 등 장학 정보를 확인할 수 있어요.
            </div>
        )
    },
    {
        id: 42,
        label: "교내시설",
        title: (
            <span className="faq-title-inline">
                <img src="/icons/amenities.svg" alt="교내시설" className="faq-icon" />
                <span className="faq-title-text">교내시설</span>
            </span>
        ),
        description: (
            <div>
                교내 편의시설 위치와 이용 방법을 확인할 수 있어요.
            </div>
        )
    },
    {
        id: 48,
        label: "학사정보",
        title: (
            <span className="faq-title-inline">
                <img src="/icons/curriculum.svg" alt="학사정보" className="faq-icon" />
                <span className="faq-title-text">학사정보</span>
            </span>
        ),
        description: (
            <div>
                교육과정, 학점 인정, 졸업 요건 등 학사 정보를 확인할 수 있어요.
            </div>
        )
    }
];


// 🔥 백슬래시 n을 실제 줄바꿈으로 변환하는 함수
const normalizeMessage = (text: string): React.ReactNode => {
    if (!text) return '';
    
    // \\n을 실제 줄바꿈으로 변환
    const normalized = text
        .replace(/\\\\n/g, '\n')
        .replace(/\\n/g, '\n');
    
    // 줄바꿈을 기준으로 split하고 <br />로 연결
    const lines = normalized.split('\n');
    
    return lines.map((line, index) => (
        <React.Fragment key={index}>
            {line}
            {index < lines.length - 1 && <br />}
        </React.Fragment>
    ));
};

// 🔥 FAQ 데이터를 백엔드에서 가져오는 API 함수
export const fetchFAQData = async (faqId: number): Promise<FAQResponse> => {
    // console.log('🔍 fetchFAQData 호출됨 - faqId:', faqId);

    try {
        // 🔥 실제 백엔드 API 호출
        // console.log('📡 API 호출 시도:', `http://localhost:8000/api/faq/${faqId}`);
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/faq/${faqId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        // console.log('✅ API 응답 성공:', result);

        if (!result.success) {
            throw new Error(result.message || 'FAQ 데이터를 가져올 수 없습니다.');
        }

        // 백엔드 응답을 FAQResponse 형식으로 변환
        const faqData = result.data;

        // 🔥 show_in_chat이 true인 자식 질문만 필터링
        const filteredChildren = faqData.children?.filter((child: FAQChild) => child.show_in_chat === true) || [];

        // children에서 title을 options로 변환 (하위 호환성)
        const options = filteredChildren.map((child: FAQChild) => child.title || child.question);



        return {
            id: faqData.id,
            title: faqData.title || faqData.question,
            response: normalizeMessage(faqData.answer_content || ''),
            options: options,
            children: filteredChildren // 🔥 자식 질문 전체 포함
        };

    } catch (error) {
        console.error('❌ FAQ API Error:', error);
        throw error; // 에러를 그대로 throw
    }
};



// ========== 추가 유틸리티 함수들 ==========

// FAQ 항목 존재 여부 확인
export const isFAQExists = (faqId: number): boolean => {
    return FAQ_ITEMS.some(item => item.id === faqId);
};

// 모든 FAQ 제목 가져오기
export const getAllFAQTitles = (): string[] => {
    return FAQ_ITEMS.map(item => item.label || '').filter(Boolean);
};

// FAQ ID로 기본 정보 가져오기 (API 호출 없이)
export const getFAQBasicInfo = (faqId: number): FAQItem | null => {
    return FAQ_ITEMS.find(item => item.id === faqId) || null;
};