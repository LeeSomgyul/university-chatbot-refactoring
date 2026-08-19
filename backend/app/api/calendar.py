# backend/app/routers/calendar.py

from fastapi import APIRouter, HTTPException
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

router = APIRouter(
    prefix="/api/calendar",
    tags=["calendar"]
)

# JSON 파일 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent
JSON_FILE_PATH = BASE_DIR / "data" / "calendar.json"


def load_calendar_data() -> List[Dict[Any, Any]]:
    """
    calendar.json 파일 로드
    """
    print(f"📂 Calendar JSON 파일 로드: {JSON_FILE_PATH}")
    
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 전체 학사일정 데이터: {len(data)}개")
        return data
        
    except FileNotFoundError:
        print(f"❌ Calendar JSON 파일을 찾을 수 없습니다: {JSON_FILE_PATH}")
        raise HTTPException(status_code=500, detail="Calendar JSON 파일을 찾을 수 없습니다.")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파싱 오류: {str(e)}")
    except Exception as e:
        print(f"❌ JSON 파일 로드 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파일 로드 중 오류: {str(e)}")


def parse_date(date_str: str) -> datetime:
    """
    날짜 문자열을 datetime 객체로 변환
    형식: "2024-12-28" (하이픈 형식)
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        print(f"⚠️ 날짜 파싱 실패: {date_str} - {e}")
        raise ValueError(f"날짜 형식을 파싱할 수 없습니다: {date_str}")


@router.get("/current-month")
async def get_current_month_calendar():
    """
    이번 달 학사일정 반환
    """
    try:
        data = load_calendar_data()
        
        # 현재 연도와 월
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        print(f"📅 현재: {current_year}년 {current_month}월")
        
        # 이번 달 일정 필터링
        current_month_events = []
        
        for event in data:
            try:
                # start_date 파싱
                start_date_str = event.get('start_date', '')
                if not start_date_str:
                    continue
                
                start_date = parse_date(start_date_str)
                
                # 이번 달인지 확인
                if start_date.year == current_year and start_date.month == current_month:
                    current_month_events.append(event)
                    
            except Exception as e:
                print(f"⚠️ 일정 처리 중 오류 (건너뜀): {event.get('title', 'Unknown')} - {e}")
                continue
        
        print(f"✅ {current_year}년 {current_month}월 학사일정: {len(current_month_events)}개")
        
        # 날짜순 정렬
        current_month_events.sort(key=lambda x: parse_date(x['start_date']))
        
        return {
            "success": True,
            "data": {
                "year": current_year,
                "month": current_month,
                "events": current_month_events,
                "total": len(current_month_events)
            }
        }
        
    except Exception as e:
        print(f"❌ 이번 달 학사일정 조회 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": {
                "year": None,
                "month": None,
                "events": [],
                "total": 0
            }
        }


@router.get("/month/{year}/{month}")
async def get_month_calendar(year: int, month: int):
    """
    특정 연도/월의 학사일정 반환
    """
    try:
        data = load_calendar_data()
        
        print(f"📅 조회: {year}년 {month}월")
        
        # 해당 월 일정 필터링
        month_events = []
        
        for event in data:
            try:
                start_date_str = event.get('start_date', '')
                if not start_date_str:
                    continue
                
                start_date = parse_date(start_date_str)
                
                if start_date.year == year and start_date.month == month:
                    month_events.append(event)
                    
            except Exception as e:
                print(f"⚠️ 일정 처리 중 오류 (건너뜀): {event.get('title', 'Unknown')} - {e}")
                continue
        
        print(f"✅ {year}년 {month}월 학사일정: {len(month_events)}개")
        
        # 날짜순 정렬
        month_events.sort(key=lambda x: parse_date(x['start_date']))
        
        return {
            "success": True,
            "data": {
                "year": year,
                "month": month,
                "events": month_events,
                "total": len(month_events)
            }
        }
        
    except Exception as e:
        print(f"❌ {year}년 {month}월 학사일정 조회 중 오류: {e}")
        return {
            "success": False,
            "message": str(e),
            "data": {
                "year": year,
                "month": month,
                "events": [],
                "total": 0
            }
        }