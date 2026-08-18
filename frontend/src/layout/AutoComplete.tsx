import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react';

// 기본 테스트용 자동완성 단어 목록 (DB 연결 전까지 사용하며 연결 이후에는 사용X.)
// const DEFAULT_AUTOCOMPLETE_SUGGESTIONS = [
//     '안녕하세요',
//     '안녕히가세요',
//     '감사합니다',
//     '죄송합니다',
//     '도움이 필요해요',
//     '문의사항이 있어요',
// ];

interface AutoCompleteProps {
    value: string;
    onChange: (value: string) => void;
    onSelect: (suggestion: string) => void;
    onKeyDown?: (e: React.KeyboardEvent) => void;
    placeholder?: string;
    disabled?: boolean;
    autoInputEnabled: boolean;
    className?: string;
    // DB 연동을 위한 선택적 props
    suggestions?: string[];                                        // 미리 가져온 단어 목록
    fetchSuggestions?: (query: string) => Promise<string[]> | string[];  // 실시간 검색 함수
    autoSend?: boolean;                                           // 클릭 시 바로 전송 여부
    onAutoSend?: (message: string) => void;                       // 바로 전송 콜백
}

export interface AutoCompleteRef {
    focus: () => void;
    blur: () => void;
}

const AutoComplete = forwardRef<AutoCompleteRef, AutoCompleteProps>(({
    value,
    onChange,
    onSelect,
    onKeyDown,
    placeholder,
    disabled = false,
    autoInputEnabled,
    className = '',
    suggestions: externalSuggestions,
    fetchSuggestions,
    autoSend = false,
    onAutoSend
}, ref) => {
    // 자동완성 상태 관리
    const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [isLoading, setIsLoading] = useState(false);
    
    // DOM 참조 - textarea 사용
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const suggestionsRef = useRef<HTMLDivElement>(null);

    // 부모 컴포넌트에서 포커스 제어할 수 있도록 설정
    useImperativeHandle(ref, () => ({
        focus: () => inputRef.current?.focus(),
        blur: () => inputRef.current?.blur()
    }));

    // 자동완성 단어 필터링 및 검색
    const filterSuggestions = async (query: string) => {
        if (!autoInputEnabled || !query.trim()) {
            setFilteredSuggestions([]);
            setShowSuggestions(false);
            setSelectedIndex(-1);
            return;
        }

        setIsLoading(true);

        try {
            let suggestionsToFilter: string[] = [];

            // 우선순위: 실시간 검색 > 외부 제공 목록 > 기본 테스트 목록
            if (fetchSuggestions) {
                const result = await fetchSuggestions(query);
                suggestionsToFilter = result;
            } else if (externalSuggestions) {
                suggestionsToFilter = externalSuggestions;
            }
            //  else {
            //     suggestionsToFilter = DEFAULT_AUTOCOMPLETE_SUGGESTIONS;
            // }

            // 입력값과 매칭되는 단어들 필터링
            const filtered = suggestionsToFilter.filter(suggestion =>
                suggestion.toLowerCase().includes(query.toLowerCase())
            );

            setFilteredSuggestions(filtered);
            setShowSuggestions(filtered.length > 0);
            setSelectedIndex(-1);

        } catch (error) {
            console.error('자동완성 데이터를 가져오는 중 오류가 발생했습니다:', error);
            setFilteredSuggestions([]);
            setShowSuggestions(false);
        } finally {
            setIsLoading(false);
        }
    };

    // 입력값 변경 시 자동완성 업데이트
    useEffect(() => {
        filterSuggestions(value);
    }, [value, autoInputEnabled, externalSuggestions]);

    // 자동완성 토글 변경 시 즉시 반응
    useEffect(() => {
        if (!autoInputEnabled) {
            setShowSuggestions(false);
            setSelectedIndex(-1);
        }
    }, [autoInputEnabled]);

    // 외부 클릭 시 자동완성 드롭다운 숨기기
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node) &&
                inputRef.current && !inputRef.current.contains(event.target as Node)) {
                setShowSuggestions(false);
                setSelectedIndex(-1);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    // 자동완성 항목 선택 처리
    const handleSuggestionSelect = (suggestion: string) => {
        if (autoSend && onAutoSend) {
            // ⚡ 바로 전송 모드: 입력창 초기화 후 즉시 전송
            onChange('');
            setShowSuggestions(false);
            setSelectedIndex(-1);
            onAutoSend(suggestion);
        } else {
            // 일반 모드: 입력창에 텍스트만 입력
            onSelect(suggestion);
            setShowSuggestions(false);
            setSelectedIndex(-1);
            inputRef.current?.focus();
        }
    };

    // 키보드 네비게이션 처리 - textarea용
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (showSuggestions && filteredSuggestions.length > 0) {
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    setSelectedIndex(prev => 
                        prev < filteredSuggestions.length - 1 ? prev + 1 : 0
                    );
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    setSelectedIndex(prev => 
                        prev > 0 ? prev - 1 : filteredSuggestions.length - 1
                    );
                    break;
                case 'Enter':
                    if (selectedIndex >= 0) {
                        e.preventDefault(); // 자동완성 선택 시에는 줄바꿈 방지
                        handleSuggestionSelect(filteredSuggestions[selectedIndex]);
                        return;
                    }
                    // 자동완성이 선택되지 않았으면 부모 컴포넌트에서 처리
                    break;
                case 'Escape':
                    setShowSuggestions(false);
                    setSelectedIndex(-1);
                    break;
                default:
                    break;
            }
        }
        
        // 부모 컴포넌트의 키 이벤트 핸들러 호출
        onKeyDown?.(e);
    };

    // 입력값 변경 처리 - textarea용
    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        onChange(e.target.value);
    };

    // 입력창 포커스 시 자동완성 표시
    const handleFocus = () => {
        if (autoInputEnabled && value.trim() && filteredSuggestions.length > 0) {
            setShowSuggestions(true);
        }
    };

    return (
        <div className={`autocomplete-wrapper ${className}`}>
            {/* 입력창 - textarea로 박스 전체 활용 */}
            <textarea 
                ref={inputRef}
                value={value}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onFocus={handleFocus}
                placeholder={placeholder}
                className="autocomplete-input"
                disabled={disabled}
                rows={1}
                style={{ resize: 'none', overflow: 'hidden' }}
            />
            
            {/* 자동완성 드롭다운 */}
            {showSuggestions && filteredSuggestions.length > 0 && autoInputEnabled && (
                <div ref={suggestionsRef} className="autocomplete-dropdown">
                    {isLoading ? (
                        <div className="autocomplete-loading">검색 중...</div>
                    ) : (
                        filteredSuggestions.map((suggestion, index) => (
                            <div
                                key={index}
                                className={`autocomplete-item ${
                                    index === selectedIndex ? 'autocomplete-item-selected' : ''
                                }`}
                                onClick={() => handleSuggestionSelect(suggestion)}
                                onMouseEnter={() => setSelectedIndex(index)}
                            >
                                {suggestion}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
});

AutoComplete.displayName = 'AutoComplete';

export default AutoComplete;