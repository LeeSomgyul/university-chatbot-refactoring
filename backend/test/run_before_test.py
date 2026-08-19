# 테스트 전용 코드
# [DB 분류 정확도 저하 (관계형 vs 벡터 혼동)] 개선 전

"""
Before 측정 스크립트
- routing_test_set.csv의 질문 29개를 순서대로 /chat에 보낸다
- 실제 query_type(curriculum/general/review)을 기록
- 정답_함수 라벨을 '이상적인 옛 카테고리'로 변환해서 일치 여부 채점
- 결과를 before_results.csv로 저장 + 요약 출력

사용법 (backend 폴더에서, 가상환경 활성화 상태로):
    python run_before_test.py

사전 조건: uvicorn app.main:app --reload 로 서버가 이미 떠 있어야 함
"""
import csv
import time
import requests

API_URL = "http://localhost:8000/chat"
INPUT_CSV = "routing_test_set.csv"   # 아까 받은 CSV를 이 스크립트와 같은 폴더에 두세요
OUTPUT_CSV = "before_results.csv"

# 정답_함수 -> 이상적인 옛 카테고리(curriculum/general/review) 매핑
FUNCTION_TO_IDEAL_OLD_CATEGORY = {
    "check_graduation_status": "curriculum",
    "get_curriculum_requirements": "curriculum",
    "get_equivalent_course_info": "curriculum",  # 관계형 DB 성격 (지금은 버그로 general로 감)
    "search_general_info": "general",
    "search_reviews": "review",
}


def call_chat(message: str) -> dict:
    """서버에 질문 하나를 보내고 응답을 받는다"""
    payload = {"message": message}
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e), "query_type": None, "message": ""}


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
        ideal_old_category = FUNCTION_TO_IDEAL_OLD_CATEGORY.get(expected_func, "unknown")

        response = call_chat(question)
        actual_category = response.get("query_type")
        answer_preview = (response.get("message") or "")[:60]

        is_match = (actual_category == ideal_old_category)
        if is_match:
            correct_count += 1

        key = (ideal_old_category, actual_category)
        confusion[key] = confusion.get(key, 0) + 1

        results.append({
            "no": row["no"],
            "질문": question,
            "카테고리": row["카테고리"],
            "정답_함수": expected_func,
            "이상적_옛카테고리": ideal_old_category,
            "실제_query_type": actual_category,
            "일치여부": "O" if is_match else "X",
            "홀드아웃": row["홀드아웃"],
            "응답_미리보기": answer_preview,
        })

        mark = "✅" if is_match else "❌"
        print(f"{mark} [{row['no']}] {question[:30]:<32} 기대:{ideal_old_category:<11} 실제:{actual_category}")

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

    # D그룹(동일대체)만 따로 - 오늘 핵심 버그 확인용
    d_rows = [r for r in results if r["카테고리"] == "D_equivalent"]
    if d_rows:
        d_correct = sum(1 for r in d_rows if r["일치여부"] == "O")
        print(f"동일대체(D그룹) 정확도: {d_correct}/{len(d_rows)} "
              f"({d_correct/len(d_rows)*100:.1f}%)")

    print(f"\n혼동행렬 (기대 카테고리 -> 실제 카테고리별 개수):")
    for (expected, actual), count in sorted(confusion.items()):
        print(f"  {expected} -> {actual}: {count}건")

    print(f"\n상세 결과는 {OUTPUT_CSV} 에 저장되었습니다.")


if __name__ == "__main__":
    main()