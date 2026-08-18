import { useNotices } from '../hooks/useNotices';

// 기능1: 공지사항 컴포넌트 - 현재 공지사항을 헤더 하단에 표시
const Notice = () => {
  const currentNotice = useNotices();

  return (
    <nav className="w-full bg-white border-b border-black">
      <div className="px-6 py-2 flex items-center gap-3 text-sm text-slate-800">
        {/* 기능2: 공지사항 라벨 - 공지사항임을 표시하는 태그 */}
        <span className="whitespace-nowrap border border-black px-2 py-0.5 notice-label">
          공지사항
        </span>

        {/* 기능3: 공지사항 링크 - 클릭 시 공지사항 상세 페이지로 이동 */}
        <a
          href={currentNotice.link}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline hover:text-slate-900 transition-colors font-semibold
          notice-text line-clamp-1"
        >
          {currentNotice.title}
        </a>
      </div>
    </nav>
  );
};

export default Notice;
