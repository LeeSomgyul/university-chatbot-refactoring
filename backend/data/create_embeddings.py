"""
텍스트 데이터를 읽어서 임베딩 생성 후 Supabase documents 테이블에 업로드
"""
import sys
from pathlib import Path
from typing import List, Dict

# 상위 디렉토리 추가
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.utils.embedding_client import get_embedding_model


class EmbeddingCreator:
    """임베딩 생성 및 업로드 클래스"""
    
    def __init__(self):
        self.model = get_embedding_model()
    
    def load_from_text_file(self, file_path: str) -> List[Dict]:
        documents = []
        current_doc = {}
        content_lines = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"  총 라인 수: {len(lines)}")  # 디버깅
            
            for idx, line in enumerate(lines):
                line = line.rstrip()
                
                if line.startswith('===CATEGORY:'):
                    print(f"  라인 {idx}: CATEGORY 발견")  # 디버깅
                    # 이전 문서 저장
                    if current_doc and content_lines:
                        current_doc['content'] = '\n'.join(content_lines).strip()
                        documents.append(current_doc)
                        print(f"    문서 저장됨: {current_doc['metadata'].get('title', 'NO TITLE')}")  # 디버깅
                    
                    # 새 문서 시작
                    current_doc = {
                        'metadata': {
                            'category': line.replace('===CATEGORY:', '').strip()
                        }
                    }
                    content_lines = []
                
                elif line.startswith('===TITLE:'):
                    current_doc['metadata']['title'] = line.replace('===TITLE:', '').strip()
                
                elif line:
                    content_lines.append(line)
        
        # 마지막 문서 저장
        if current_doc and content_lines:
            current_doc['content'] = '\n'.join(content_lines).strip()
            documents.append(current_doc)
            print(f"  마지막 문서 저장됨: {current_doc['metadata'].get('title', 'NO TITLE')}")
        
        return documents
    
    def load_from_directory(self, directory: Path) -> List[Dict]:
        """
        디렉토리 내의 모든 .txt 파일에서 데이터 로드
        """
        all_documents = []
        
        # .txt 파일들 찾기
        txt_files = sorted(directory.glob("*.txt"))
        
        if not txt_files:
            print(f"⚠️  {directory}에 .txt 파일이 없습니다.")
            return all_documents
        
        for txt_file in txt_files:
            print(f"\n📄 {txt_file.name} 읽는 중...")
            docs = self.load_from_text_file(str(txt_file))
            all_documents.extend(docs)
            print(f"   ✅ {len(docs)}개 문서 로드")
        
        return all_documents
    
    def load_from_db_tables(self) -> List[Dict]:
        """
        Supabase의 다른 테이블에서 데이터 가져와서 문서화
        (실험실, 학사일정, 도서관 정보는 이미 .txt로 관리하므로 제외)
        """
        documents = []
        
        # contact_info 테이블이 있다면 로드
        try:
            contact_result = self.supabase.table('contact_info').select('*').execute()
            for contact in contact_result.data:
                content = f"""
                {contact['department_name']}
                카테고리: {contact['category']}
                위치: {contact.get('location', '')}
                전화: {contact.get('phone', '')}
                이메일: {contact.get('email', '')}
                운영시간: {contact.get('operating_hours', '')}
                비고: {contact.get('notes', '')}
                                """.strip()
                
                documents.append({
                    'content': content,
                    'metadata': {
                        'category': '연락처',
                        'title': contact['department_name'],
                        'department_category': contact['category']
                    }
                })
            print(f"✅ 연락처 {len(contact_result.data)}개 로드")
        except Exception as e:
            print(f"⚠️  contact_info 테이블 없음 또는 로드 실패: {e}")
        
        # 추가로 필요한 테이블이 있으면 여기에 추가
        
        return documents
    
    def create_embeddings(self, documents: List[Dict]) -> List[Dict]:
        """텍스트에서 임베딩 생성"""
        if not documents:
            print("⚠️  임베딩할 문서가 없습니다.")
            return []
        
        print(f"\n🔄 {len(documents)}개 문서의 임베딩 생성 중...")
        
        # 배치로 임베딩 생성 (빠름)
        contents = [doc['content'] for doc in documents]
        embeddings = self.model.encode(
            contents, 
            show_progress_bar=True,
            batch_size=32  # 배치 크기
        )
        
        # 문서에 임베딩 추가
        for i, doc in enumerate(documents):
            doc['embedding'] = embeddings[i].tolist()
        
        print("✅ 임베딩 생성 완료")
        return documents
    
    def upload_to_supabase(self, documents: List[Dict], clear_existing: bool = False):
        """Supabase documents 테이블에 업로드"""
        if not documents:
            print("⚠️  업로드할 문서가 없습니다.")
            return
        
        print(f"\n📤 Supabase에 {len(documents)}개 문서 업로드 중...")
        
        # 기존 데이터 삭제 옵션
        if clear_existing:
            print("🗑️  기존 documents 데이터 삭제 중...")
            try:
                self.supabase.table('documents').delete().neq('id', 0).execute()
                print("✅ 기존 데이터 삭제 완료")
            except Exception as e:
                print(f"⚠️  기존 데이터 삭제 실패 (무시): {e}")
        
        # 배치 업로드 (한 번에 최대 100개)
        batch_size = 100
        total_uploaded = 0
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Supabase 형식에 맞게 변환
            upload_data = []
            for doc in batch:
                upload_data.append({
                    'content': doc['content'],
                    'metadata': doc['metadata'],
                    'embedding': doc['embedding']
                })
            
            try:
                result = self.supabase.table('documents').insert(upload_data).execute()
                uploaded_count = len(result.data) if result.data else len(upload_data)
                total_uploaded += uploaded_count
                print(f"  ✅ {i + 1} ~ {min(i + batch_size, len(documents))} 업로드 완료")
            except Exception as e:
                print(f"  ❌ 배치 {i} 업로드 실패: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"✅ 총 {total_uploaded}개 문서 업로드 완료")
    
    def test_search(self, query: str, k: int = 3):
        """임베딩 검색 테스트"""
        print(f"\n🔍 테스트 검색: '{query}'")
        
        # 쿼리 임베딩 생성
        query_embedding = self.model.encode(query).tolist()
        
        # Supabase에서 검색
        try:
            result = self.supabase.rpc(
                'match_documents_vector',
                {
                    'query_embedding': query_embedding,
                    'match_count': k
                }
            ).execute()
            
            if not result.data:
                print("  ⚠️  검색 결과가 없습니다.")
                return
            
            print(f"\n검색 결과 ({len(result.data)}개):")
            for idx, doc in enumerate(result.data, 1):
                print(f"\n{idx}. [{doc['metadata']['category']}] {doc['metadata']['title']}")
                print(f"   유사도: {doc['similarity']:.4f}")
                # 내용이 길면 100자만 출력
                content_preview = doc['content'][:100].replace('\n', ' ')
                print(f"   내용: {content_preview}...")
        
        except Exception as e:
            print(f"  ❌ 검색 실패: {e}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🎯 벡터 임베딩 생성 및 업로드")
    print("=" * 60)
    
    creator = EmbeddingCreator()
    
    # 데이터 디렉토리
    text_data_dir = Path(__file__).parent / "text_data"
    
    # 사용자에게 선택 옵션 제공
    print("\n업로드 모드를 선택하세요:")
    print("1. 전체 재업로드 (기존 데이터 삭제 후 전체 업로드)")
    print("2. 증분 업로드 (기존 데이터 유지하고 새 데이터만 추가)")
    
    choice = input("\n선택 (1 또는 2): ").strip()
    
    if choice == "1":
        clear_existing = True
        print("\n✅ 전체 재업로드 모드")
    elif choice == "2":
        clear_existing = False
        print("\n✅ 증분 업로드 모드")
    else:
        print("\n❌ 잘못된 선택. 기본값(증분 업로드) 사용")
        clear_existing = False
    
    # 1. text_data 디렉토리의 모든 .txt 파일 로드
    print(f"\n📂 {text_data_dir} 디렉토리에서 텍스트 파일 로드 중...")
    text_documents = creator.load_from_directory(text_data_dir)
    
    if not text_documents:
        print("\n❌ 로드할 문서가 없습니다!")
        print(f"💡 {text_data_dir} 폴더에 .txt 파일을 추가해주세요.")
        return
    
    print(f"\n📚 총 {len(text_documents)}개 문서 로드됨")
    
    # 로드된 문서 요약 출력
    category_count = {}
    for doc in text_documents:
        cat = doc['metadata']['category']
        category_count[cat] = category_count.get(cat, 0) + 1
    
    print("\n📊 카테고리별 문서 수:")
    for cat, count in sorted(category_count.items()):
        print(f"   - {cat}: {count}개")
    
    # 2. DB 테이블에서 추가 데이터 로드 (선택사항)
    print("\n📊 DB 테이블에서 추가 데이터 로드...")
    db_documents = creator.load_from_db_tables()
    
    # 전체 문서 통합
    all_documents = text_documents + db_documents
    print(f"\n📚 최종 총 {len(all_documents)}개 문서")
    
    # 3. 임베딩 생성
    documents_with_embeddings = creator.create_embeddings(all_documents)
    
    if not documents_with_embeddings:
        print("\n❌ 임베딩 생성 실패!")
        return
    
    # 4. Supabase에 업로드
    # clear_existing=True로 설정하면 기존 데이터를 모두 삭제하고 새로 업로드
    # clear_existing=False로 설정하면 기존 데이터에 추가
    creator.upload_to_supabase(
        documents_with_embeddings, 
        clear_existing=True  # 기존 데이터 삭제 후 업로드
    )
    
    # 5. 테스트 검색
    print("\n" + "=" * 60)
    print("🧪 검색 테스트")
    print("=" * 60)
    
    test_queries = [
        "광주에서 학교 가는 통학버스 시간 알려줘",
        "통학버스 예약은 어떻게 해?",
        "순천 통학버스 노선 알려줘"
    ]
    
    for query in test_queries:
        creator.test_search(query, k=2)
        print()
    
    print("=" * 60)
    print("\n✅ 모든 작업 완료!")
    print(f"\n💡 Supabase 대시보드에서 확인: {settings.supabase_url}")


if __name__ == "__main__":
    main()