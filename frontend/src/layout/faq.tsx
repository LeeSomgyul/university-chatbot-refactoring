import { createPortal } from 'react-dom';
import { useState, useEffect } from 'react';
import { FAQ_ITEMS, fetchFAQData } from '../service/faqServices';
import type { FAQResponse } from '../service/faqServices';



// 세부 항목 정보 타입 (DB 연동 시 확장 예정)
export interface FAQSubItem {
    id: number;
    title: string;
    answer_type: 'text' | 'url' | 'action' | 'card';
    answer_content: string | null;
    parentId: number;
    // 추후 DB 연동 시 추가 가능할 필드 목록:
    // subItemId?: number;
    // category?: string;
    // priority?: number;
}

// Props 타입 정의
interface FAQProps {
    isOpen: boolean;
    onClose: () => void;
    onSendMessage: (title: string, id: number) => void;
    onSubItemClick: (subItem: FAQSubItem) => void; // 세부 항목 클릭 처리
}

const FAQ: React.FC<FAQProps> = ({ isOpen, onClose, onSendMessage, onSubItemClick }) => {
    const [isMaximized, setIsMaximized] = useState(false);
    const [faqData, setFaqData] = useState<Record<number, FAQResponse>>({});
    const [loadingStates, setLoadingStates] = useState<Record<number, boolean>>({});

    // 기능1 : FAQ 데이터 로드 - 서버에서 FAQ 세부 옵션 데이터를 가져옴
    // FAQ 데이터 로드 함수 (에러 처리 및 로딩 상태 개선)
    const loadFAQData = async (faqId: number) => {
        if (faqData[faqId] || loadingStates[faqId]) return;

        setLoadingStates(prev => ({ ...prev, [faqId]: true }));

        try {
            const data = await fetchFAQData(faqId);
            setFaqData(prev => ({ ...prev, [faqId]: data }));
        } catch (error) {
            console.error(`FAQ ${faqId} 데이터 로드 실패:`, error);
            // 에러 상태도 관리할 수 있도록 추후 확장 가능
        } finally {
            setLoadingStates(prev => ({ ...prev, [faqId]: false }));
        }
    };

    // FAQ 세부 옵션 가져오기
    const getSubItems = (faqId: number): any[] => {
        const data = faqData[faqId];
        return data?.children || [];
    };

    // 기능2 : 전체보기 모드 데이터 미리 로드 - 최대화 시 모든 FAQ 데이터를 미리 로드함(한 번에 불러오기)
    useEffect(() => {
        if (isMaximized) {
            FAQ_ITEMS.forEach(item => {
                loadFAQData(item.id);
            });
        }
    }, [isMaximized]);


    // 기능3 : FAQ 메인 카테고리 클릭 처리 - FAQ 항목을 선택하면 채팅창에 메시지 전송
    const handleFAQClick = (label: string | undefined, id: number) => {
        // label이 undefined일 경우 기본값 사용
        const title = label || `FAQ ${id}`;
        onSendMessage(title, id);
        onClose();
    };

    // 기능4 : 세부 항목 클릭 처리 - FAQ 하위 옵션 클릭 시, DB 연동 대비 구조화된 데이터 전달
    const handleSubItemClick = (child: any, parentId: number) => {
        const subItemData: FAQSubItem = {
            id: child.id,
            title: child.title,
            answer_type: child.answer_type,
            answer_content: child.answer_content ?? null,
            parentId: parentId,
            // 추후 DB 연동 시 추가 가능할 정보:
            // subItemId: calculateSubItemId(parentId, optionIndex),
            // category: getParentCategory(parentId),
            // priority: getOptionPriority(optionText)
        };

        onSubItemClick(subItemData);
        onClose();
    };

  if (!isOpen) return null;

  const faqContent = (
    <div className={isMaximized ? 'faq-fullscreen' : 'faq-container-small'}>
      {/* 헤더 */}
      <div className={`faq-header ${isMaximized ? 'faq-header--max' : ''}`}>
        <h3 className={`faq-title ${isMaximized ? 'faq-title--left' : ''}`}>
          {isMaximized ? '자주 찾는 질문(FAQ)' : '자주 찾는 질문'}
        </h3>
        <div className="faq-controls">
          <button
            className="faq-control-btn"
            onClick={() => setIsMaximized(!isMaximized)}
            title={isMaximized ? "X" : "전체보기"}
            aria-label={isMaximized ? "X" : "전체보기"}
          >
            {isMaximized ? "X" : "전체보기"}
          </button>
        </div>
      </div>

      {/* 내용 */}
      <div className="faq-scroll">
        <div className="faq-scroll-viewport">
          <div className="faq-content">
            {FAQ_ITEMS.map((item, index) => {
              const subItems = getSubItems(item.id);
              const isLoading = loadingStates[item.id];

              return (
                <div key={item.id}>
                  <div className="faq-item">
                    <div
                      className="faq-question"
                      onClick={() => handleFAQClick(item.label, item.id)}
                    >
                      {isMaximized ? (
                        <>
                          <div className="faq-title">{item.title}</div>
                          <div className="faq-description">{item.description}</div>
                        </>
                      ) : (
                        item.title
                      )}
                    </div>
                  </div>

                  {/* 기능5: 세부 옵션 표시 - 전체보기 모드에서만 하위 옵션 버튼들 표시 */}    
                  {isMaximized && (
                    <div className="faq-sub-section">
                      {isLoading ? (
                        <div className="faq-loading">로딩중...</div>
                      ) : subItems.length > 0 ? (
                        <div className="faq-sub-items">
                          {subItems.map((child: any) => (
                            <button
                              key={`${item.id}-${child.id}`}
                              className="faq-sub-item-btn"
                              onClick={() => handleSubItemClick(child, item.id)}
                            >
                              {child.title}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <div className="faq-no-options">세부 옵션이 없습니다.</div>
                      )}
                    </div>
                  )}

                  {isMaximized && index < FAQ_ITEMS.length - 1 && (
                    <hr className="faq-divider" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );    
  
  // 기능6: 포털 렌더링 - 전체보기 모드는 전체 화면으로, 일반 모드는 일반 위치에 렌더링
  return isMaximized
    ? createPortal(faqContent, document.body)
    : faqContent;

};

export default FAQ;