-- Supabase SQL Editor에서 실행할 전체 스키마

-- ============================================
-- 1. 확장 기능 활성화
-- ============================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. 교육과정 테이블 (기존 수정)
-- ============================================

-- 2-1. curriculums 테이블
DROP TABLE IF EXISTS curriculums CASCADE;
CREATE TABLE curriculums (
    id BIGSERIAL PRIMARY KEY,
    admission_year INTEGER NOT NULL,
    course_area TEXT NOT NULL,
    requirement_type TEXT,
    track TEXT,
    grade INTEGER,
    semester INTEGER,
    course_code TEXT NOT NULL,
    course_name TEXT NOT NULL,
    credit INTEGER NOT NULL,
    is_required_to_graduate BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
);

CREATE INDEX idx_curriculums_year_area ON curriculums(admission_year, course_area);
CREATE INDEX idx_curriculums_course_code ON curriculums(course_code);

-- 2-2. equivalent_courses 테이블
DROP TABLE IF EXISTS equivalent_courses CASCADE;
CREATE TABLE equivalent_courses (
    id BIGSERIAL PRIMARY KEY,
    old_course_code TEXT NOT NULL,
    old_course_name TEXT NOT NULL,
    new_course_code TEXT NOT NULL,
    new_course_name TEXT NOT NULL,
    mapping_type TEXT,
    allow_duplicate BOOLEAN DEFAULT false,
    allow_retake BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_equivalent_old_code ON equivalent_courses(old_course_code);
CREATE INDEX idx_equivalent_new_code ON equivalent_courses(new_course_code);

-- 2-3. graduation_requirements 테이블
-- graduation_requirements 테이블만 재정의
DROP TABLE IF EXISTS graduation_requirements CASCADE;
CREATE TABLE graduation_requirements (
    id BIGSERIAL PRIMARY KEY,
    admission_year INTEGER NOT NULL,
    course_area TEXT NOT NULL,
    requirement_type TEXT,
    track TEXT,
    required_credits INTEGER NOT NULL,
    required_all TEXT[] DEFAULT '{}',
    required_one_of JSONB DEFAULT '[]',
    selectable_course_codes TEXT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
);

CREATE INDEX idx_graduation_year_area ON graduation_requirements(admission_year, course_area);

-- ============================================
-- 3. 벡터 검색 테이블
-- ============================================

DROP TABLE IF EXISTS documents CASCADE;
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);

-- 벡터 검색 함수
CREATE OR REPLACE FUNCTION match_documents (
    query_embedding VECTOR(768),
    match_count INT DEFAULT 5,
    filter JSONB DEFAULT '{}'
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE 
        CASE 
            WHEN filter = '{}' THEN true
            ELSE documents.metadata @> filter
        END
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- 4. 학교 정보 테이블
-- ============================================

-- 4-1. 학사일정
DROP TABLE IF EXISTS academic_calendar CASCADE;
CREATE TABLE academic_calendar (
    id BIGSERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    semester INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_calendar_year_semester ON academic_calendar(year, semester);
CREATE INDEX idx_calendar_dates ON academic_calendar(start_date, end_date);

-- 4-2. 실험실/연구실
DROP TABLE IF EXISTS laboratories CASCADE;
CREATE TABLE laboratories (
    id BIGSERIAL PRIMARY KEY,
    lab_name TEXT NOT NULL,
    professor_name TEXT,
    tel TEXT,
    email TEXT,
    description TEXT,
    project TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_labs_category ON laboratories(category);

-- 4-3. 도서관 정보
-- 1) 층별 공간 간단 소개
DROP TABLE IF EXISTS library_hours CASCADE;
CREATE TABLE IF NOT EXISTS library_hours (
  id BIGSERIAL PRIMARY KEY,
  place TEXT NOT NULL,
  term TEXT NOT NULL,            -- 'regular'(학기중), 'vacation'(방학중)
  day_scope TEXT NOT NULL,       -- 'weekday', 'weekend', 'holiday', 'wed' 등
  open_time TIME,
  close_time TIME,
  is_closed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);


-- ============================================
-- 5. RLS (Row Level Security) 설정
-- ============================================
-- 모든 테이블을 읽기 전용 공개

ALTER TABLE curriculums ENABLE ROW LEVEL SECURITY;
ALTER TABLE equivalent_courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE graduation_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE academic_calendar ENABLE ROW LEVEL SECURITY;
ALTER TABLE laboratories ENABLE ROW LEVEL SECURITY;
ALTER TABLE library_hours ENABLE ROW LEVEL SECURITY;

-- 모든 사용자 읽기 허용
CREATE POLICY "Public read access" ON curriculums FOR SELECT USING (true);
CREATE POLICY "Public read access" ON equivalent_courses FOR SELECT USING (true);
CREATE POLICY "Public read access" ON graduation_requirements FOR SELECT USING (true);
CREATE POLICY "Public read access" ON documents FOR SELECT USING (true);
CREATE POLICY "Public read access" ON academic_calendar FOR SELECT USING (true);
CREATE POLICY "Public read access" ON laboratories FOR SELECT USING (true);
CREATE POLICY "Public read access" ON library_hours FOR SELECT USING (true);