"""
구글시트 → pending_reviews 자동 동기화
구글폼에 맞춤 설정됨!
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime
from app.database.supabase_client import supabase
from app.config import settings


# ===== 구글시트 설정 =====
SHEET_ID = settings.google_sheet_id


def read_google_sheet():
    """
    구글시트 읽기 (Google Sheets API 사용)
    """
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        import json
        
        print("🔑 구글 인증 중...")
        
        # 인증
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        credentials_json = os.getenv('GOOGLE_CREDENTIALS')
        
        if credentials_json:
            # 배포 환경: 환경변수 사용
            print("  📌 환경변수에서 인증 정보 로드")
            credentials_dict = json.loads(credentials_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                credentials_dict,
                scope
            )
        else:
            # 로컬 환경: 파일 사용
            print("  📌 credentials.json 파일에서 인증 정보 로드")
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                'credentials.json', 
                scope
            )
            
        client = gspread.authorize(creds)
        
        print("📊 구글시트 읽기 중...")
        
        # 시트 열기
        sheet = client.open_by_key(SHEET_ID).sheet1
        
        # 모든 레코드 읽기 (dict 형태)
        records = sheet.get_all_records()
        
        print(f"✅ 구글시트 읽기 완료: {len(records)}개 행\n")
        return records
    
    except FileNotFoundError:
        print("❌ credentials.json 파일을 찾을 수 없습니다!")
        print("\n📖 해결 방법:")
        print("1. Google Cloud Console에서 서비스 계정 키를 다운로드하세요")
        print("2. credentials.json으로 이름 변경")
        print("3. 이 스크립트와 같은 폴더(backend/)에 저장하세요")
        return []
    
    except Exception as e:
        print(f"❌ 구글시트 읽기 실패: {e}")
        print("\n📖 설정이 필요합니다:")
        print("1. https://console.cloud.google.com/ 접속")
        print("2. 프로젝트 생성 & Google Sheets API 활성화")
        print("3. 서비스 계정 만들고 credentials.json 다운로드")
        print("4. 구글시트를 서비스 계정과 공유")
        print("5. pip install gspread oauth2client")
        return []


def sync_to_pending_reviews(records):
    """
    구글시트 데이터를 pending_reviews에 동기화
    
    너의 구글폼 컬럼명에 맞춤:
    - 타임스탬프
    - 교수님 이름
    - 과목명
    - 과목 코드
    - 수강 학기
    - 강의 방식
    - 과제량
    - 시험 난이도
    - 자유 후기
    """
    
    if not records:
        print("⚠️ 읽을 데이터가 없습니다")
        return
    
    print(f"📝 동기화 시작: {len(records)}개 후기\n")
    
    new_count = 0
    skip_count = 0
    error_count = 0
    
    for i, record in enumerate(records, 1):
        try:
            # 구글폼 컬럼명 매칭 (정확히 일치해야 함!)
            professor = record.get('교수님 이름', '').strip()
            course = record.get('과목명', '').strip()
            course_code = record.get('과목 코드', '').strip()
            semester = record.get('수강 학기', '').strip()
            teaching_style = record.get('강의 방식', '').strip()
            assignment_load = record.get('과제량', '').strip()
            exam_difficulty = record.get('시험 난이도', '').strip()
            review_text = record.get('자유 후기', '').strip()
            
            # 필수 필드 체크
            if not professor or not course or not semester or not review_text:
                print(f"  ⏭️  [{i}] 필수 정보 누락 (교수: {professor}, 과목: {course}), 스킵")
                skip_count += 1
                continue
            
            # 중복 체크 (교수 + 과목 + 후기 내용의 첫 100자)
            review_snippet = review_text[:100]
            
            existing = supabase.table('pending_reviews')\
                .select('id')\
                .eq('professor_name', professor)\
                .eq('course_name', course)\
                .ilike('review_text', f'{review_snippet}%')\
                .execute()
            
            if existing.data:
                print(f"  ⏭️  [{i}] {professor} - {course} (이미 있음, 스킵)")
                skip_count += 1
                continue
            
            # 삽입
            new_review = {
                "professor_name": professor,
                "course_name": course,
                "course_code": course_code if course_code else None,
                "semester": semester,
                "teaching_style": teaching_style,
                "assignment_load": assignment_load,
                "exam_difficulty": exam_difficulty,
                "review_text": review_text,
                "status": "pending",
                "submitted_at": datetime.now().isoformat()
            }
            
            result = supabase.table('pending_reviews').insert(new_review).execute()
            
            print(f"  ✅ [{i}] {professor} - {course} ({semester})")
            new_count += 1
        
        except Exception as e:
            print(f"  ❌ [{i}] 실패: {e}")
            error_count += 1
            continue
    
    print(f"\n{'='*50}")
    print(f"🎉 동기화 완료!")
    print(f"  ✅ 새로 추가: {new_count}개")
    print(f"  ⏭️  중복 스킵: {skip_count}개")
    if error_count > 0:
        print(f"  ❌ 에러: {error_count}개")
    print(f"  📊 총 처리: {len(records)}개")


def main():
    """메인 실행"""
    print("="*50)
    print("🔄 구글시트 → pending_reviews 동기화")
    print("="*50)
    print()
    
    # 1. 라이브러리 체크
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
    except ImportError:
        print("❌ 필요한 라이브러리가 설치되지 않았습니다!")
        print("\n실행:")
        print("  pip install gspread oauth2client")
        return
    
    # 2. 구글시트 읽기
    records = read_google_sheet()
    
    if not records:
        print("\n❌ 동기화 중단")
        print("\n💡 Tip: 구글폼에 테스트 응답이 있는지 확인하세요!")
        return
    
    # 3. pending_reviews에 동기화
    sync_to_pending_reviews(records)
    
    print("\n✅ 완료! 이제 승인 API로 후기를 승인하세요.")
    print("👉 GET  http://localhost:8000/admin/reviews/pending")
    print("👉 POST http://localhost:8000/admin/reviews/{id}/approve")


if __name__ == "__main__":
    main()
