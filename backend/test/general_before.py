import json
import csv
from collections import defaultdict

from app.domain.vector_search.service import get_vector_service


K_VALUES = [3, 10]  # 3 = 현재 search_general 운영값, 10 = 대조군
TESTSET_PATH = "test/general_testset.json"
OUTPUT_CSV_PATH = "test/general_results_before.csv"


def load_testset(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_hit(returned_ids: list[int], answer_ids: list[int]) -> bool:
    """정답 id 중 하나라도 반환 결과에 포함되면 성공(보조 정답 포함 처리)"""
    return any(a_id in returned_ids for a_id in answer_ids)


def run_evaluation():
    vector_service = get_vector_service()
    testset = load_testset(TESTSET_PATH)

    rows = []
    stats_by_k = {k: defaultdict(lambda: {"hit": 0, "total": 0}) for k in K_VALUES}
    stats_by_k_type = {k: defaultdict(lambda: {"hit": 0, "total": 0}) for k in K_VALUES}
    overall_by_k = {k: {"hit": 0, "total": 0} for k in K_VALUES}

    for item in testset:
        category = item["category"]
        q_type = item["type"]
        question = item["question"]
        answer_ids = item["answer_ids"]

        row = {
            "category": category,
            "type": q_type,
            "question": question,
            "answer_ids": answer_ids,
        }

        for k in K_VALUES:
            results = vector_service.search(question, k=k)  # List[VectorSearchResult]
            returned_ids = [r.id for r in results]           # dict.get('id') -> r.id (타입 적용)
            hit = is_hit(returned_ids, answer_ids)

            row[f"returned_ids_k{k}"] = returned_ids
            row[f"hit_k{k}"] = hit

            stats_by_k[k][category]["total"] += 1
            stats_by_k[k][category]["hit"] += int(hit)

            stats_by_k_type[k][q_type]["total"] += 1
            stats_by_k_type[k][q_type]["hit"] += int(hit)

            overall_by_k[k]["total"] += 1
            overall_by_k[k]["hit"] += int(hit)

        rows.append(row)

    # ---- 콘솔 출력 ----
    print("=" * 70)
    print("Before 측정 결과 — 순수 벡터 검색 (search_general)")
    print("=" * 70)

    for k in K_VALUES:
        label = " (현재 운영값)" if k == 3 else " (대조군)"
        print(f"\n--- k={k}{label} ---")

        print("\n[카테고리별 Recall]")
        for category, s in stats_by_k[k].items():
            recall = s["hit"] / s["total"] * 100
            print(f"  {category:10s}: {s['hit']}/{s['total']}  ({recall:.0f}%)")

        print("\n[질문 유형별 Recall]")
        for q_type, s in stats_by_k_type[k].items():
            recall = s["hit"] / s["total"] * 100
            print(f"  {q_type:10s}: {s['hit']}/{s['total']}  ({recall:.0f}%)")

        overall = overall_by_k[k]
        overall_recall = overall["hit"] / overall["total"] * 100
        print(f"\n[전체] {overall['hit']}/{overall['total']}  ({overall_recall:.0f}%)")

    # ---- CSV 저장 (After 측정과 비교할 때 재사용) ----
    fieldnames = ["category", "type", "question", "answer_ids"]
    for k in K_VALUES:
        fieldnames += [f"returned_ids_k{k}", f"hit_k{k}"]

    with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = {k_: (json.dumps(v_, ensure_ascii=False) if isinstance(v_, list) else v_)
                       for k_, v_ in row.items()}
            writer.writerow(csv_row)

    print(f"\n상세 결과가 {OUTPUT_CSV_PATH} 에 저장됐습니다.")


if __name__ == "__main__":
    run_evaluation()