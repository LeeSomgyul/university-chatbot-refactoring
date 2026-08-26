"""
[1회성 백필 스크립트] 기존 documents 데이터에 content_morphemes 채워넣기

- 이미 DB에 있는 문서들(content_morphemes가 NULL인 것들)을 대상으로
  content_tokenizer.extract_content_morpheme()를 돌려서 결과를 UPDATE
- 앞으로 새로 업로드되는 문서는 create_embeddings.py 수정을 통해
  자동으로 채워질 예정이므로, 이 스크립트는 "지금 있는 데이터"에 대해
  딱 한 번만 실행하고 이후엔 재사용하지 않음
- 페이지네이션 처리: Supabase 기본 응답 제한(보통 1000건)에 안전하도록
  PAGE_SIZE 단위로 나눠서 가져옴 -> 데이터가 늘어나도 안전하게 동작

실행 위치: backend/data/backfill_content_morphemes.py
실행 방법: backend 폴더 기준으로
    $ python data/backfill_content_morphemes.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database.supabase_client import supabase
from app.domain.vector_search.content_tokenizer import extract_content_morpheme


PAGE_SIZE = 500


def fetch_documents_without_morphemes() -> list[dict]:
    """content_morphemes가 아직 채워지지 않은 문서를 전부 가져옴 (페이지네이션)"""
    all_rows = []
    start = 0

    while True:
        result = (
            supabase.table("documents")
            .select("id, content")
            .is_("content_morphemes", "null")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )

        rows = result.data if result.data else []
        if not rows:
            break

        all_rows.extend(rows)
        print(f"  조회: {start} ~ {start + len(rows) - 1} ({len(rows)}건)")

        if len(rows) < PAGE_SIZE:
            break  # 마지막 페이지
        start += PAGE_SIZE

    return all_rows


def run_backfill():
    print("=" * 60)
    print("content_morphemes 백필 시작")
    print("=" * 60)

    # 0. 전체 대상 건수 확인
    count_result = (
        supabase.table("documents")
        .select("id", count="exact")
        .is_("content_morphemes", "null")
        .execute()
    )
    total_target = count_result.count
    print(f"\n대상 문서 수 (content_morphemes IS NULL): {total_target}건")

    if not total_target:
        print("채울 데이터가 없습니다. 종료합니다.")
        return

    # 1. 대상 문서 전체 조회
    print("\n문서 조회 중...")
    documents = fetch_documents_without_morphemes()
    print(f"총 {len(documents)}건 조회 완료")

    # 2. 형태소 분석 + 개별 UPDATE
    print("\n형태소 분석 및 업데이트 진행...")
    success_count = 0
    fail_count = 0
    empty_result_ids = []  # 형태소가 하나도 안 뽑힌 문서 (원인 파악용으로 기록)

    for i, doc in enumerate(documents, 1):
        doc_id = doc["id"]
        content = doc.get("content", "")

        try:
            morphemes = extract_content_morpheme(content)

            if not morphemes:
                empty_result_ids.append(doc_id)

            supabase.table("documents").update(
                {"content_morphemes": morphemes}
            ).eq("id", doc_id).execute()

            success_count += 1

        except Exception as e:
            fail_count += 1
            print(f"  ❌ id={doc_id} 처리 실패: {e}")

        if i % 50 == 0 or i == len(documents):
            print(f"  진행: {i}/{len(documents)}")

    # 3. 결과 요약
    print("\n" + "=" * 60)
    print("백필 완료")
    print("=" * 60)
    print(f"성공: {success_count}건")
    print(f"실패: {fail_count}건")

    if empty_result_ids:
        print(f"\n⚠️  형태소가 하나도 추출되지 않은 문서 {len(empty_result_ids)}건 (id): {empty_result_ids}")
        print("   -> content가 비어있거나, 명사/영문/숫자가 전혀 없는 특이 케이스일 수 있음. 확인 필요.")

    # 4. 최종 검증: 여전히 NULL로 남은 게 있는지 확인
    remaining = (
        supabase.table("documents")
        .select("id", count="exact")
        .is_("content_morphemes", "null")
        .execute()
    )
    print(f"\n검증: 여전히 NULL인 문서 수 = {remaining.count} (0이어야 정상)")


if __name__ == "__main__":
    run_backfill()