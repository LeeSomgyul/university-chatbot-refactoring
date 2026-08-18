import React, { useState, useEffect, useRef } from 'react';
import '../style/Guide.css';

interface GuideStep {
    selector: string; // '.target-element', '#login-button' 등
    description: string;
    descriptionPosition?: 'target-element-1' | 'target-element-2' | 'target-element-3' | 'right';
}

const Guide: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [mode, setMode] = useState<'modal' | 'overlay'>('modal');
    const [imageError, setImageError] = useState(false);
    const [isHovered, setIsHovered] = useState(false);  

    // 기능1: 가이드 열기 - 가이드를 모달 모드로 시작
    const openGuide = () => {
        setIsOpen(true);
        setMode('modal'); // 항상 이미지 모달로 시작
        setImageError(false); // 이미지 오류 상태 리셋
    };

    // 기능2: 가이드 닫기 - 가이드를 닫고 기본 모드로 리셋
    const closeGuide = () => {
        setIsOpen(false);
        setMode('modal'); // 닫을 때 기본 모드로 리셋
    };

    // 이미지 로드 에러 처리
    const handleImageError = () => {
        setImageError(true);
    };

    const [spotlights, setSpotlights] = useState<Array<{
        top: number;
        left: number;
        right: number;
        width: number;
        height: number;
        description: string;
        descriptionPosition: 'target-element-1' | 'target-element-2' | 'target-element-3' | 'right';
    }>>([]);

    const targetRef = useRef<HTMLElement | null>(null);

    // 기능3: 가이드 단계 정의 - 각 요소에 대한 설명과 위치 정보
    const guideSteps: GuideStep[] = [
        { selector: '.target-element-1', description: '다른 주제로 대화하고 싶다면, 새로고침을 클릭해주세요',
            descriptionPosition : 'target-element-1'},
        { selector: '.target-element-2', description: '쉽고 빠르게 원하는 언어로 소통해 보세요.(추후개발예정)' 
            ,descriptionPosition : 'target-element-2'
        },
        { selector: '.target-element-3', description: '자동완성을 통해 시간을 절약하세요.'
        ,descriptionPosition : 'target-element-3'}
    ];

    // 기능4: ESC 키로 가이드 닫기 - 사용자가 ESC 키를 눌러 가이드를 종료할 수 있음
    useEffect(() => {
        const handleEscKey = (event: KeyboardEvent) => {
            if (event.key === 'Escape' && isOpen) {
                closeGuide();
            }
        };

        if (isOpen) {
            document.addEventListener('keydown', handleEscKey);
        }

        return () => {
            document.removeEventListener('keydown', handleEscKey);
        };
    }, [isOpen]);

    // 기능5: 스포트라이트 위치 업데이트 - 화면 크기 변경 및 스크롤 시 가이드 위치를 실시간으로 조정
    useEffect(()=> {
        if(!isOpen) return;
        const updatePositions = () => {
            const positions = guideSteps.map(step => {
                const element = document.querySelector(step.selector) as HTMLElement;
                if (element) {
                    const rect = element.getBoundingClientRect();
                    return {
                        top: rect.top - 5,
                        left: rect.left - 5,
                        width: rect.width + 15,
                        height: rect.height + 10,
                        right : window.innerWidth - rect.right -15,
                        description: step.description,
                        descriptionPosition: step.descriptionPosition || 'bottom'
                    };
                }
                return null;
            }).filter(Boolean) as Array<{
                top: number;
                left: number;
                right: number;
                width: number;
                height: number;
                description: string;
                descriptionPosition: 'target-element-1' | 'target-element-2' | 'target-element-3' | 'right';
            }>;

            setSpotlights(positions);
        };

        updatePositions();
        
        window.addEventListener('resize', updatePositions);
        window.addEventListener('scroll', updatePositions);
        
        return () => {
            window.removeEventListener('resize', updatePositions);
            window.removeEventListener('scroll', updatePositions);
        };
    }, [isOpen]);

    // 기능6: 설명 텍스트 위치 계산 - 각 요소에 맞는 설명 텍스트의 위치를 동적으로 계산
    const getDescriptionStyle = (spotlight: typeof spotlights[0]) => {
        const baseStyle = {
            position: 'fixed' as const,
            color: '#ffffff',
            fontSize: '14px',
            fontWeight: 'bold' as const,
            zIndex: 1000,
            padding: '8px 12px',
        };

        switch (spotlight.descriptionPosition) {
            case 'target-element-1':
                return {
                    ...baseStyle,
                    top: `${spotlight.top + spotlight.height / 2}px`,
                    left: `${spotlight.left + spotlight.width + 10}px`,
                    transform: 'translateY(-50%)'
                };
            case 'target-element-2':
                return {
                    ...baseStyle,
                    top: `${spotlight.top + spotlight.height + 5}px`,
                    right: `20px`,

                };
            case 'target-element-3':
                return {
                    ...baseStyle,
                    top: `${spotlight.top + spotlight.height + 5}px`,
                    right: `${spotlight.right}px`,
                };
            case 'right':
                return {
                   ...baseStyle,
                    top: `${spotlight.top}px`,
                    left: `${spotlight.left + spotlight.width}px`,
                };
            default:
                return {
                    ...baseStyle,
                    top: `${spotlight.top + spotlight.height + 10}px`,
                    left: `${spotlight.left + spotlight.width / 2}px`,
                    transform: 'translateX(-50%)'
                };
        }
    };

    // 기능7: 가이드 버튼 - 가이드가 닫혀있을 때 표시되는 버튼
    if (!isOpen) {
        return (
            <button
                onClick={openGuide}
                className="guide-button"
                aria-label="이용안내"
            >
                <img src={isHovered ? "/icons/Guide.svg" : "/icons/Guide_close.svg"} alt="이용안내"
                onMouseEnter={()=> setIsHovered(true)}
                onMouseLeave={()=> setIsHovered(false)}
                />
                    <path 
                        strokeLinecap="round" 
                        strokeLinejoin="round" 
                        strokeWidth={2} 
                        d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
                    />
            </button>
        );
    }

    return (
        <div>
            {/* 기능8: 회색 오버레이 - 가이드 실행 시 배경을 어둡게 처리 */}
            <div 
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    zIndex: 999,
                     mixBlendMode: 'multiply' 
                }}
            />
            
            {/* 기능9: 스포트라이트 및 설명 - 각 요소를 강조하고 설명을 표시 */}
            {spotlights.map((spotlight, index) => (
                <React.Fragment key={index}>
                    {/* 둥근 모서리 직사각형 spotlight */}
                    <div
                        style={{
                            position: 'fixed',
                            top: `${spotlight.top}px`,
                            left: `${spotlight.left}px`,
                            width: `${spotlight.width}px`,
                            height: `${spotlight.height}px`,
                            border: '3px solid #FFFFFF',
                            borderRadius: '10px',
                            zIndex: 1000,
                            pointerEvents: 'none'
                        }}
                    />

                    <div style={getDescriptionStyle(spotlight)}>
                        {spotlight.description}
                    </div>

                    {/* 기능10: 닫기 버튼 - 가이드를 종료하는 버튼 */}
                    <button onClick={closeGuide}
                        style={{position:'fixed',
                            bottom : '20px',
                            right : '20px',
                            width : '80px',
                            height : '40px',
                            border: '3px solid #FFFFFF',
                            borderRadius: '10px',
                            zIndex: 1000,
                            color : '#FFFFFF',
                            fontFamily : 'sans-serif'
                        }}>
                        닫기
                    </button>    
                </React.Fragment>
            ))}
        </div>
    );
};

export default Guide;
