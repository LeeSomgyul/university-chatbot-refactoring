import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database.supabase_client import supabase
from app.domain.vector_search.content_tokenizer import extract_content_morpheme_weighted


PAGE_SIZE = 500


def fetch_all_documents() -> list[dict]:
    """전체 문서를 페이지네이션으로 가져옴"""
    all_rows = []
    start = 0

    while True:
        result = (
            supabase.table("documents")
            .select("id, content")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )

        rows = result.data if result.data else []
        if not rows:
            break

        all_rows.extend(rows)
        print(f"  조회: {start} ~ {start + len(rows) - 1} ({len(rows)}건)")

        if len(rows) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    return all_rows


def run_backfill():
    print("=" * 60)
    print("content_identifiers / content_nouns 백필 시작 (가중치 분리 버전)")
    print("=" * 60)

    # 0. 전체 대상 건수 확인
    count_result = (
        supabase.table("documents")
        .select("id", count="exact")
        .execute()
    )
    total_target = count_result.count
    print(f"\n대상 문서 수 (전체 재처리): {total_target}건")

    if not total_target:
        print("문서가 없습니다. 종료합니다.")
        return

    # 1. 전체 문서 조회
    print("\n문서 조회 중...")
    documents = fetch_all_documents()
    print(f"총 {len(documents)}건 조회 완료")

    # 2. 형태소 분석(가중치 분리) + 개별 UPDATE
    print("\n형태소 분석 및 업데이트 진행...")
    success_count = 0
    fail_count = 0
    empty_result_ids = []  # 식별자/명사 둘 다 하나도 안 뽑힌 문서

    for i, doc in enumerate(documents, 1):
        doc_id = doc["id"]
        content = doc.get("content", "")

        try:
            identifier_text, noun_text = extract_content_morpheme_weighted(content)

            if not identifier_text and not noun_text:
                empty_result_ids.append(doc_id)

            supabase.table("documents").update({
                "content_identifiers": identifier_text,
                "content_nouns": noun_text,
            }).eq("id", doc_id).execute()

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
        print(f"\n⚠️  식별자/명사가 하나도 추출되지 않은 문서 {len(empty_result_ids)}건 (id): {empty_result_ids}")
        print("   -> content가 비어있거나 특이 케이스일 수 있음. 확인 필요.")

    # 4. 최종 검증: content_tsv가 잘 채워졌는지 (NULL인 게 없어야 정상)
    remaining = (
        supabase.table("documents")
        .select("id", count="exact")
        .is_("content_tsv", "null")
        .execute()
    )
    print(f"\n검증: content_tsv가 여전히 NULL인 문서 수 = {remaining.count} (0이어야 정상)")


if __name__ == "__main__":
    run_backfill()