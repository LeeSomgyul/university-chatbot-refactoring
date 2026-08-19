# 테스트 전용 코드
# [DB 분류 정확도 저하 (관계형 vs 벡터 혼동)] 개선 후
import csv
import time
import requests

API_URL = "http://localhost:8000/chat"
INPUT_CSV = "routing_test_set_v2.csv"   # Before와 동일한 파일 (비교 가능하도록 재사용)
OUTPUT_CSV = "after_results.csv"


def call_chat(message: str) -> dict:
    """서버에 질문 하나를 보내고 응답을 받는다"""
    payload = {"message": message}
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e), "matched_function": None, "message": ""}


def main():
    with open(INPUT_CSV, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    results = []
    correct_count = 0
    confusion = {}  # (기대, 실제) -> 개수

    print(f"총 {len(rows)}개 질문 테스트 시작...\n")

    for row in rows:
        question = row["질문"]
        expected_func = row["정답_함수"]

        response = call_chat(question)
        actual_func = response.get("matched_function")
        answer_preview = (response.get("message") or "")[:80]

        # 직접 비교 (우회 로직 불필요)
        is_match = (actual_func == expected_func)
        if is_match:
            correct_count += 1

        key = (expected_func, actual_func)
        confusion[key] = confusion.get(key, 0) + 1

        results.append({
            "no": row["no"],
            "질문": question,
            "카테고리": row["카테고리"],
            "정답_함수": expected_func,
            "실제_query_type": actual_func,
            "일치여부": "O" if is_match else "X",
            "홀드아웃": row["홀드아웃"],
            "응답_미리보기": answer_preview,
        })

        mark = "✅" if is_match else "❌"
        print(f"{mark} [{row['no']}] {question[:30]:<32} 기대:{expected_func:<28} 실제:{actual_func}")

        time.sleep(0.5)  # OpenAI API 과호출 방지용 살짝 딜레이

    # 결과 저장
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # 요약 출력
    total = len(rows)
    accuracy = correct_count / total * 100
    print(f"\n{'='*50}")
    print(f"전체 정확도: {correct_count}/{total} ({accuracy:.1f}%)")
    print(f"{'='*50}")

    # 홀드아웃만 따로
    holdout_rows = [r for r in results if r["홀드아웃"] == "예"]
    if holdout_rows:
        holdout_correct = sum(1 for r in holdout_rows if r["일치여부"] == "O")
        print(f"홀드아웃 정확도: {holdout_correct}/{len(holdout_rows)} "
              f"({holdout_correct/len(holdout_rows)*100:.1f}%)")

    # D그룹(동일대체)만 따로 - Before 0%였던 그 그룹
    d_rows = [r for r in results if r["카테고리"] == "D_equivalent"]
    if d_rows:
        d_correct = sum(1 for r in d_rows if r["일치여부"] == "O")
        print(f"동일대체(D그룹) 정확도: {d_correct}/{len(d_rows)} "
              f"({d_correct/len(d_rows)*100:.1f}%)  ← Before는 0/8 (0.0%) 였음")

    # A/B/C그룹(기존 기능) 정확도 - 회귀(안 깨졌는지) 확인용
    for group_name, label in [("A_curriculum", "A(졸업사정/커리큘럼)"),
                                ("B_general", "B(일반정보)"),
                                ("C_review", "C(강의평가)")]:
        group_rows = [r for r in results if r["카테고리"] == group_name]
        if group_rows:
            g_correct = sum(1 for r in group_rows if r["일치여부"] == "O")
            print(f"{label} 정확도: {g_correct}/{len(group_rows)} ({g_correct/len(group_rows)*100:.1f}%)")

    print("\n혼동행렬 (기대 함수 -> 실제 함수별 개수):")
    for (expected, actual), count in sorted(confusion.items(), key=lambda x: str(x[0])):
        print(f"  {expected} -> {actual}: {count}건")

    print(f"\n상세 결과는 {OUTPUT_CSV} 에 저장되었습니다.")


if __name__ == "__main__":
    main()