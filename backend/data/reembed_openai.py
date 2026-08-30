"""
sentence-transformers(jhgan/ko-sroberta-multitask) -> OpenAI(text-embedding-3-small)
전환에 따른 재임베딩 스크립트.

대상 테이블 (전부 같은 임베딩 공간으로 통일해야 코사인 유사도가 의미를 가짐):
  - documents          (content 컬럼)      -> match_documents_vector RPC
  - course_reviews     (review_text 컬럼)  -> match_course_reviews RPC
  - restaurant_reviews (content 컬럼)      -> match_reviews_by_place RPC

동작 순서 (테이블별):
  1. 전체 행(id, 텍스트, 기존 embedding)을 페이지네이션으로 조회
  2. 기존 embedding 값을 data/embedding_backups/ 에 JSON으로 백업
  3. (dry-run이 아니면) 텍스트를 OpenAI로 재임베딩 후 id 기준으로 embedding 컬럼만 업데이트

사용법:
  # 1) 먼저 백업 + 임베딩 생성만 확인 (DB 변경 없음)
  python data/reembed_openai.py --table documents --dry-run

  # 2) 실제 반영 (실수 방지를 위해 --yes 필수)
  python data/reembed_openai.py --table documents --yes

  # 3) 전체 테이블 순차 처리
  python data/reembed_openai.py --table all --yes

주의: 이 스크립트는 작성만 된 상태입니다. 실제 실행은 사용자 확인 후 진행하세요.
"""
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from app.database.supabase_client import supabase
from app.utils.embedding_client import get_embedding_model


TABLES = {
    "documents": {"id_col": "id", "text_col": "content"},
    "course_reviews": {"id_col": "id", "text_col": "review_text"},
    "restaurant_reviews": {"id_col": "id", "text_col": "content"},
}

PAGE_SIZE = 500          # Supabase 조회 페이지 크기
ENCODE_BATCH_SIZE = 100  # OpenAI 임베딩 API 호출당 텍스트 개수
UPDATE_SLEEP_SEC = 0.0   # 필요 시 update 사이 딜레이(레이트리밋 안전마진용, 기본 비활성)

BACKUP_DIR = Path(__file__).parent / "embedding_backups"


def fetch_all_rows(table: str, id_col: str, text_col: str, embedding_col: str = "embedding"):
    """페이지네이션으로 테이블 전체 행(id, 텍스트, 기존 embedding)을 가져온다."""
    rows = []
    start = 0
    while True:
        end = start + PAGE_SIZE - 1
        result = (
            supabase.table(table)
            .select(f"{id_col}, {text_col}, {embedding_col}")
            .order(id_col)
            .range(start, end)
            .execute()
        )
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return rows


def backup_table(table: str, rows: list, id_col: str) -> Path:
    """재임베딩 전 기존 embedding 값을 로컬 JSON으로 백업 (id -> 기존 벡터)."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{table}_embedding_backup_{timestamp}.json"

    backup_data = [
        {"id": row[id_col], "embedding": row.get("embedding")}
        for row in rows
    ]

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f)

    print(f"  \U0001f4be 백업 완료: {backup_path} ({len(backup_data)}행)")
    return backup_path


def reembed_table(table: str, dry_run: bool):
    config = TABLES[table]
    id_col = config["id_col"]
    text_col = config["text_col"]

    print(f"\n{'=' * 60}")
    print(f"[{table}] 재임베딩 시작 (dry_run={dry_run})")
    print(f"{'=' * 60}")

    rows = fetch_all_rows(table, id_col, text_col)
    print(f"  조회된 행: {len(rows)}개")

    if not rows:
        print("  ⚠️ 처리할 행이 없습니다.")
        return

    # 1. 백업 (텍스트가 비어 손대지 않는 행까지 포함해 전체를 그대로 백업)
    backup_table(table, rows, id_col)

    # 2. 텍스트가 있는 행만 재임베딩 대상으로 선정
    targets = [r for r in rows if r.get(text_col)]
    skipped = len(rows) - len(targets)
    if skipped:
        print(f"  ⚠️ {text_col} 비어있어 스킵된 행: {skipped}개")

    if dry_run:
        print("  ℹ️ --dry-run 모드: 임베딩만 생성하고 실제 DB 업데이트는 하지 않습니다.")

    model = get_embedding_model()

    success, failed = 0, []
    for i in range(0, len(targets), ENCODE_BATCH_SIZE):
        chunk = targets[i:i + ENCODE_BATCH_SIZE]
        texts = [r[text_col] for r in chunk]

        try:
            vectors = model.encode(texts, batch_size=ENCODE_BATCH_SIZE)
        except Exception as e:
            print(f"  ❌ 임베딩 생성 실패 (행 {i}~{i + len(chunk)}): {e}")
            failed.extend(r[id_col] for r in chunk)
            continue

        for row, vector in zip(chunk, vectors):
            if dry_run:
                success += 1
                continue
            try:
                supabase.table(table).update(
                    {"embedding": vector.tolist()}
                ).eq(id_col, row[id_col]).execute()
                success += 1
            except Exception as e:
                print(f"  ❌ 업데이트 실패 (id={row[id_col]}): {e}")
                failed.append(row[id_col])

            if UPDATE_SLEEP_SEC:
                time.sleep(UPDATE_SLEEP_SEC)

        print(f"  진행: {min(i + ENCODE_BATCH_SIZE, len(targets))}/{len(targets)}")

    print(f"\n  ✅ 완료: 성공 {success}개 / 실패 {len(failed)}개 / 스킵 {skipped}개")
    if failed:
        print(f"  ⚠️ 실패한 id 목록: {failed}")


def main():
    parser = argparse.ArgumentParser(description="OpenAI 임베딩으로 재임베딩")
    parser.add_argument(
        "--table",
        choices=list(TABLES.keys()) + ["all"],
        required=True,
        help="재임베딩할 테이블 (all이면 documents/course_reviews/restaurant_reviews 순차 처리)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="백업 및 임베딩 생성만 하고 실제 DB 업데이트는 하지 않음",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="실제 DB 업데이트를 수행하려면 반드시 지정 (실수 방지용 안전장치)",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        print("❌ 실제 DB를 변경하려면 --yes 를 함께 지정하세요. (확인 없이는 --dry-run 으로만 실행됩니다)")
        print("   예: python data/reembed_openai.py --table documents --yes")
        sys.exit(1)

    targets = list(TABLES.keys()) if args.table == "all" else [args.table]
    for table in targets:
        reembed_table(table, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
