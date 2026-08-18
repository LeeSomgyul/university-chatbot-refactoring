import React from 'react';

// 메시지 타입 정의
interface Message {
    sender: string;
    text: string | React.ReactNode;
    time: string;
    isError?: boolean;
    type?: 'regular' | 'faq';
    faqOptions?: string[];
}

interface FAQChatResponseProps {
    message: Message;
    onOptionSelect?: (option: string) => void;
}

// 기능1: FAQ 채팅 응답 컴포넌트 - FAQ 답변과 함께 선택 가능한 옵션 버튼들을 표시
const FAQChatResponse: React.FC<FAQChatResponseProps> = ({ message, onOptionSelect }) => {
    return (
        <div className={`message-bubble ${
            message.sender === '나' 
                ? 'my-bubble' 
                : message.isError 
                    ? 'error-bubble' 
                    : 'bot-bubble faq-bubble'
        }`}>
            {/* FAQ 응답 텍스트 */}
            <div className="faq-response-text">
                {message.text}
            </div>

            {/* 기능2: FAQ 옵션 버튼 - 사용자가 선택할 수 있는 후속 질문 버튼들을 표시 */}
            {message.faqOptions && message.faqOptions.length > 0 && (
                <div className="faq-options">
                    {message.faqOptions.map((option, index) => (
                        <button
                            key={index}
                            className="faq-option-button"
                            onClick={() => onOptionSelect && onOptionSelect(option)}
                        >
                            {option}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default FAQChatResponse;
