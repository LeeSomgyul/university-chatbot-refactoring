// hooks/useNotices.ts
import { useState, useEffect, useRef } from 'react';
import { getScnuNotices, Notice } from '../utils/crawler';

const MAX_RETRY_ATTEMPTS = 3; // 최대 즉시 재시도 횟수
const RETRY_DELAY = 2000; // 재시도 간격 (2초)
const NORMAL_INTERVAL = 30 * 60 * 1000; // 정상 크롤링 간격 (30분)

export const useNotices = () => {
    const [notices, setNotices] = useState<Notice[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    
    const retryCountRef = useRef(0);
    const timeoutIdRef = useRef<number | null>(null); // ✅ number로 변경

    useEffect(() => {
        const loadNotices = async () => {
            const newNotices = await getScnuNotices();
            
            if (newNotices.length > 0) {
                // ✅ 성공
                setNotices(newNotices);
                retryCountRef.current = 0; // 재시도 카운터 리셋
                // console.log(`✅ 다음 업데이트: 30분 후`);
                
                // 30분 후 다음 크롤링
                scheduleNextCrawl(NORMAL_INTERVAL);
                
            } else {
                // ❌ 실패
                if (retryCountRef.current < MAX_RETRY_ATTEMPTS) {
                    // 즉시 재시도 (최대 3회)
                    retryCountRef.current += 1;
                    // console.warn(`⚠️ 재시도 ${retryCountRef.current}/${MAX_RETRY_ATTEMPTS} - ${RETRY_DELAY / 1000}초 후`);
                    
                    scheduleNextCrawl(RETRY_DELAY);
                    
                } else {
                    // 3회 실패 후에는 30분 후 재시도
                    // console.error(`❌ ${MAX_RETRY_ATTEMPTS}회 연속 실패 - 30분 후 재시도`);
                    retryCountRef.current = 0; // 리셋
                    
                    scheduleNextCrawl(NORMAL_INTERVAL);
                }
            }
            
            setIsLoading(false);
        };

        const scheduleNextCrawl = (delay: number) => {
            if (timeoutIdRef.current !== null) {
                clearTimeout(timeoutIdRef.current);
            }
            
            timeoutIdRef.current = window.setTimeout(() => { // ✅ window.setTimeout 명시
                loadNotices();
            }, delay);
        };

        // 초기 로드
        loadNotices();
        
        return () => {
            if (timeoutIdRef.current !== null) {
                clearTimeout(timeoutIdRef.current);
            }
        };
    }, []);

    // 공지사항 순환 표시
    useEffect(() => {
        if (notices.length > 1) {
            const interval = setInterval(() => {
                setCurrentIndex(prev => (prev + 1) % notices.length);
            }, 3000);
            return () => clearInterval(interval);
        }
    }, [notices.length]);

    if (isLoading && notices.length === 0) {
        return { title: "공지사항 로딩 중...", link: "#" };
    }
    
    if (notices.length === 0) {
        return { title: "공지사항을 불러올 수 없습니다", link: "#" };
    }

    return notices[currentIndex];
};