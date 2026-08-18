import { useState } from 'react';

interface HeaderProps {
  onResetChat: () => void;
}

const Header = ({ onResetChat }: HeaderProps) => {
  const [showLanguageMenu, setShowLanguageMenu] = useState(false);
  const [currentLanguage, setCurrentLanguage] = useState<'한국어' | 'English'>('한국어');

  // 기능1: 언어 변경 처리 - 사용자가 선택한 언어로 변경하고 메뉴를 닫음
  const handleLanguageChange = (language: '한국어' | 'English') => {
    setCurrentLanguage(language);
    setShowLanguageMenu(false);
    console.log(`언어가 ${language}로 변경되었습니다.`);
  };

  return (
    <header
      className="
        w-full h-13
        bg-[#BADDFE] backdrop-blur
        border-b border-slate-200
        flex items-center justify-between
        px-4 relative
      "
    >
      {/* 기능2: 새채팅 버튼 - 채팅 내역을 초기화하고 새로운 대화를 시작 */}
      <button
        onClick={onResetChat}
        className="
         active:scale-[0.98] transition target-element-1
        "
      >
        <img src="/icons/NewChat.svg" alt="" className='h-8'/>
      </button>

      {/* 기능3: 로고 - 순천대학교 홈페이지로 연결되는 로고 */}
      <a
        href="https://www.scnu.ac.kr/SCNU/main.do" target='_blank'
        className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2 hover:opacity-90"
      >
        <img src="/icons/Logo.svg" alt="순천대학교 로고" className="h-8" />
      </a>

      {/* 기능4: 언어 선택 메뉴 - 한국어/영어 선택 기능 (추후 개발 예정) */}
      <div
        className="relative target-element-2"
        onMouseEnter={() => setShowLanguageMenu(true)}
        onMouseLeave={() => setShowLanguageMenu(false)}
      >
        <div className="inline-flex items-center gap-1 cursor-pointer ">
          <span className="font-bold text-[#6C6B6B] bg-[#BADDFE] px-2 py-0.5 rounded">
            {currentLanguage === '한국어' ? '한국어' : 'ENGLISH'}
          </span>
          <svg
            className="w-3.5 h-3.5 opacity-70 text-[#6C6B6B]"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M5.23 7.21a.75.75 0 011.06.02L10 11.173l3.71-3.94a.75.75 0 111.08 1.04l-4.24 4.5a.75.75 0 01-1.08 0l-4.24-4.5a.75.75 0 01.02-1.06z" />
          </svg>
        </div>

        {/* 기능5: 언어 선택 드롭다운 - 마우스 호버 시 언어 선택 옵션 표시 */}
        {showLanguageMenu && (
          <div
            className="
              absolute right-0 z-50 mt-1 w-28
              rounded-md border border-slate-200 bg-white shadow-lg
            "
            role="menu"
          >
            <button
              onClick={() => handleLanguageChange('한국어')}
              className="w-full text-left px-3 py-2 text-sm hover:bg-[#E9F4FF]"
              role="menuitem"
            >
              한국어 
            </button>
            <button
              onClick={() => handleLanguageChange('English')}
              className="w-full text-left px-3 py-2 text-sm hover:bg-[#E9F4FF]"
              role="menuitem"
            >
              English
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
