// utils/crawler.ts
export type Notice = {
    title: string;
    link: string;
};

type StoredData = {
    notices: Notice[];
    last_update: string;
};

const getStoredNotices = (): Notice[] => {
    try {
        const stored = localStorage.getItem('scnu_notices');
        if (stored) {
            const data: StoredData = JSON.parse(stored);
            return data.notices || [];
        }
    } catch (error) {
        // console.error('저장된 데이터 로드 실패:', error);
    }
    return [];
};

export const getScnuNotices = async (): Promise<Notice[]> => {
    try {
        const proxyUrl = 'https://api.allorigins.win/raw?url=';
        const targetUrl = 'https://www.scnu.ac.kr/SCNU/na/ntt/selectNttList.do?mi=1131&bbsId=1040';
        
        // 타임아웃 20초로 증가
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 20000); // 20초
        
        const response = await fetch(proxyUrl + encodeURIComponent(targetUrl), {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId); // 응답 받으면 타임아웃 취소
        
        if (response.ok) {
            const html = await response.text();
            
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            const rows = doc.querySelectorAll('tr');
            
            const noticeRows: HTMLTableRowElement[] = [];
            rows.forEach(row => {
                const cells = row.querySelectorAll('td, th');
                if (cells.length > 0) {
                    const firstCell = cells[0].textContent?.trim() || '';
                    if (/^\d+$/.test(firstCell)) {
                        noticeRows.push(row as HTMLTableRowElement);
                    }
                }
            });
            
            const notices: Notice[] = [];
            for (let i = 0; i < Math.min(noticeRows.length, 5); i++) {
                const row = noticeRows[i];
                const cells = row.querySelectorAll('td');
                
                if (cells.length >= 2) {
                    const title = cells[1].textContent?.trim() || '';
                    const linkElement = cells[1].querySelector('a');
                    
                    let link = "#";
                    if (linkElement && linkElement.getAttribute('href')) {
                        const href = linkElement.getAttribute('href')!;
                        link = href.startsWith('http') ? href : `https://www.scnu.ac.kr${href}`;
                    }
                    
                    notices.push({ title, link });
                }
            }
            
            if (notices.length > 0) {
                const data: StoredData = {
                    notices,
                    last_update: new Date().toISOString()
                };
                localStorage.setItem('scnu_notices', JSON.stringify(data));
                // console.log(`✅ 공지사항 ${notices.length}개 업데이트 완료`);
                return notices;
            } else {
                // console.warn("⚠️ 크롤링은 성공했지만 공지사항이 없음");
                return getStoredNotices();
            }
            
        } else {
            // console.error(`❌ HTTP 오류: ${response.status}`);
            return getStoredNotices();
        }
        
    } catch (error) {
        // AbortError는 따로 처리
        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                // console.warn('⚠️ 요청 시간 초과 (20초)');
            } else if (error.message.includes('fetch')) {
                // console.warn('⚠️ 네트워크 오류 발생');
            } else {
                // console.error('❌ 크롤링 오류:', error);
            }
        }
        return getStoredNotices();
    }
};