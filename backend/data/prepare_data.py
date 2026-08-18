"""
엑셀 데이터를 읽어서 Supabase에 업로드하는 스크립트
"""
import pandas as pd
import sys
import os
from pathlib import Path
import json

# 상위 디렉토리를 path에 추가 (app 모듈 import 위해)
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Supabase 클라이언트 생성"""
    return create_client(settings.supabase_url, settings.supabase_service_key)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    데이터프레임 정리
    - NaN을 None으로 변환
    - 빈 문자열 제거
    """
    df = df.replace({pd.NA: None, pd.NaT: None, float('nan'): None})
    
    # 문자열 컬럼의 공백 제거
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) and x.strip() else None)
    
    return df


def parse_array_column(value):
    """
    쉼표로 구분된 문자열을 배열로 변환
    예: "CSE101,CSE102,CSE103" -> ["CSE101", "CSE102", "CSE103"]
    """
    if pd.isna(value) or value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    return [item.strip() for item in str(value).split(',') if item.strip()]


def parse_json_column(value):
    """
    JSON 문자열을 파싱
    예: '["CSE201","CSE202"]' -> ["CSE201", "CSE202"]
    """
    if pd.isna(value) or value is None or value == '':
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except:
        # JSON 파싱 실패시 배열로 시도
        return parse_array_column(value)


def upload_curriculums(supabase: Client, file_path: str):
    """curriculums 테이블 업로드"""
    print(f"\n📚 Uploading curriculums from {file_path}...")
    
    df = pd.read_excel(file_path)
    df = clean_dataframe(df)
    
    # 컬럼명 매핑
    df.columns = [
        'admission_year', 'course_area', 'requirement_type', 'track',
        'grade', 'semester', 'course_code', 'course_name', 'credit',
        'is_required_to_graduate'
    ]
    
    # 데이터 타입 변환
    df['admission_year'] = df['admission_year'].astype(int)
    df['credit'] = df['credit'].astype(int)
    df['is_required_to_graduate'] = df['is_required_to_graduate'].fillna(False).astype(bool)
    
    # grade, semester를 int로 변환 (None이 아닌 경우만)
    df['grade'] = df['grade'].apply(lambda x: int(x) if pd.notna(x) else None)
    df['semester'] = df['semester'].apply(lambda x: int(x) if pd.notna(x) else None)
    
    # Supabase에 업로드
    data = df.to_dict('records')
    result = supabase.table('curriculums').insert(data).execute()
    
    print(f"✅ Uploaded {len(data)} rows to curriculums")
    return result


def upload_equivalent_courses(supabase: Client, file_path: str):
    """equivalent_courses 테이블 업로드"""
    print(f"\n🔄 Uploading equivalent_courses from {file_path}...")
    
    df = pd.read_excel(file_path)
    df = clean_dataframe(df)
    
    df.columns = [
        'old_course_code', 'old_course_name', 'new_course_code', 
        'new_course_name', 'mapping_type', 'allow_duplicate', 'allow_retake'
    ]
    
    df['allow_duplicate'] = df['allow_duplicate'].fillna(False).astype(bool)
    df['allow_retake'] = df['allow_retake'].fillna(False).astype(bool)
    
    data = df.to_dict('records')
    result = supabase.table('equivalent_courses').insert(data).execute()
    
    print(f"✅ Uploaded {len(data)} rows to equivalent_courses")
    return result


def upload_graduation_requirements(supabase: Client, file_path: str):
    """graduation_requirements 테이블 업로드"""
    print(f"\n🎓 Uploading graduation_requirements from {file_path}...")
    
    df = pd.read_excel(file_path)
    df = clean_dataframe(df)
    
    df.columns = [
        'admission_year', 'course_area', 'requirement_type', 'track',
        'required_credits', 'required_all', 'required_one_of', 'selectable_course_codes'
    ]
    
    # 데이터 타입 변환
    df['admission_year'] = df['admission_year'].astype(int)
    df['required_credits'] = df['required_credits'].astype(int)
    
    # 배열 컬럼 파싱
    df['required_all'] = df['required_all'].apply(parse_array_column)
    df['required_one_of'] = df['required_one_of'].apply(parse_json_column)
    df['selectable_course_codes'] = df['selectable_course_codes'].apply(parse_array_column)
    
    data = df.to_dict('records')
    result = supabase.table('graduation_requirements').insert(data).execute()
    
    print(f"✅ Uploaded {len(data)} rows to graduation_requirements")
    return result


def upload_academic_calendar(supabase: Client, file_path: str):
    """academic_calendar 테이블 업로드"""
    print(f"\n📅 Uploading academic_calendar from {file_path}...")
    
    df = pd.read_excel(file_path, dtype=str)
    df = clean_dataframe(df)
    
    df.columns = [
        'year', 'semester', 'event_name', 'start_date', 'end_date'
    ]
    
    # 데이터 타입 변환
    df['year'] = df['year'].astype(int)
    df['semester'] = df['semester'].astype(int)
    
    # 날짜 형식 변환
    df['start_date'] = pd.to_datetime(df['start_date'].astype(str).str.strip(), errors='coerce')
    df['end_date']   = pd.to_datetime(df['end_date'].astype(str).str.strip(), format='%Y-%m-%d', errors='coerce')
    
    df['start_date'] = df['start_date'].dt.strftime('%Y-%m-%d')
    df['end_date']   = df['end_date'].dt.strftime('%Y-%m-%d')
    
    df = df.where(pd.notnull(df), None)
    
    data = df.to_dict('records')
    result = supabase.table('academic_calendar').insert(data).execute()
    
    print(f"✅ Uploaded {len(data)} rows to academic_calendar")
    return result


def upload_laboratories(supabase: Client, file_path: str):
    """laboratories 테이블 업로드"""
    print(f"\n🔬 Uploading laboratories from {file_path}...")
    
    df = pd.read_excel(file_path)
    df = clean_dataframe(df)
    
    df.columns = [
        'lab_name', 'professor_name',
        'tel', 'email', 'description', 'project'
    ]
    
    # 배열 컬럼 파싱
    df['project'] = df['project'].apply(parse_array_column)
    
    data = df.to_dict('records')
    result = supabase.table('laboratories').insert(data).execute()
    
    print(f"✅ Uploaded {len(data)} rows to laboratories")
    return result


def upload_library_hours(supabase: Client, file_path: str):
    """library_hours 테이블 업로드"""
    print(f"\n⏰ Uploading library_hours from {file_path}...")

    # 엑셀 읽기
    df = pd.read_excel(file_path)
    df = clean_dataframe(df)

    # 엑셀 컬럼명 -> DB 컬럼명 매핑
    df.columns = ['place', 'term', 'day_scope', 'open_time', 'close_time', 'is_closed']

    # 데이터 타입 변환
    df['term'] = df['term'].fillna('').astype(str)
    df['day_scope'] = df['day_scope'].fillna('').astype(str)

    # 시간 컬럼: 문자열 -> HH:MM:SS 변환
    def normalize_time(value):
        if pd.isna(value) or value == '' or value is None:
            return None
        # "9:00" → "09:00:00"
        try:
            return pd.to_datetime(str(value)).strftime("%H:%M:%S")
        except Exception:
            return None

    df['open_time'] = df['open_time'].apply(normalize_time)
    df['close_time'] = df['close_time'].apply(normalize_time)

    # 불리언 처리
    df['is_closed'] = df['is_closed'].fillna(False).astype(bool)

    # 딕셔너리 변환 후 업로드
    data = df.to_dict('records')
    result = supabase.table('library_hours').insert(data).execute()

    print(f"✅ Uploaded {len(data)} rows to library_hours")
    return result


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("📊 Supabase 데이터 업로드 스크립트")
    print("=" * 60)
    
    # Supabase 클라이언트 생성
    try:
        supabase = get_supabase_client()
        print("✅ Supabase 연결 성공")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return
    
    # 데이터 디렉토리
    data_dir = Path(__file__).parent / "raw_data"
    
    # 업로드할 파일 목록
    uploads = [
        ('curriculums.xlsx', upload_curriculums),
        ('equivalent_courses.xlsx', upload_equivalent_courses),
        ('graduation_requirements.xlsx', upload_graduation_requirements),
        ('academic_calendar.xlsx', upload_academic_calendar),
        ('laboratories.xlsx', upload_laboratories),
        ('library_hours.xlsx', upload_library_hours),
    ]
    
    # 각 파일 업로드
    for filename, upload_func in uploads:
        file_path = data_dir / filename
        
        if not file_path.exists():
            print(f"\n⚠️  {filename} 파일이 없습니다. 건너뜁니다.")
            continue
        
        try:
            upload_func(supabase, str(file_path))
        except Exception as e:
            print(f"❌ {filename} 업로드 실패: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 모든 업로드 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()