"""
DeepEval 평가 스크립트 — 1순위 4개 지표 측정

- general_testset_with_actual.json (question, expected_output, actual_output,
  retrieval_context가 모두 채워진 40개 데이터)을 LLMTestCase로 변환
- ContextualRecallMetric, ContextualPrecisionMetric, FaithfulnessMetric,
  AnswerRelevancyMetric 4개를 각각 측정
- 카테고리별 평균 점수 + 전체 평균 점수를 출력하고, 각 케이스의 reasoning을
  CSV로 저장 (포트폴리오 문서화 시 구체적 근거로 활용)

실행 위치: backend/test/
실행 방법: backend 폴더 기준
    $ python test/run_deepeval.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import csv
import time
from collections import defaultdict

from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    FaithfulnessMetric,
    AnswerRelevancyMetric,
)

from app.config import settings


TESTSET_PATH = "test/general_testset_with_actual.json"
OUTPUT_CSV_PATH = "test/deepeval_results.csv"

# DeepEval 판정 LLM 모델 (프로젝트에서 이미 쓰는 모델과 동일하게)
JUDGE_MODEL = settings.model_name


def load_testset() -> list[dict]:
    with open(TESTSET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_test_cases(testset: list[dict]) -> list[LLMTestCase]:
    test_cases = []
    for item in testset:
        test_case = LLMTestCase(
            input=item["question"],
            actual_output=item["actual_output"],
            expected_output=item["expected_output"],
            retrieval_context=item["retrieval_context"],
        )
        # 카테고리 정보는 LLMTestCase 표준 필드가 아니므로 별도 속성으로 붙여서
        # 나중에 결과 집계할 때 참조 (DeepEval이 막지 않는 방식)
        test_cases.append(test_case)
    return test_cases


def run():
    testset = load_testset()
    all_test_cases = build_test_cases(testset)

    print(f"총 {len(all_test_cases)}개 케이스에 대해 DeepEval 4개 지표 측정 시작...")
    print(f"판정 모델: {JUDGE_MODEL}")

    metrics = [
        ContextualRecallMetric(model=JUDGE_MODEL, include_reason=True),
        ContextualPrecisionMetric(model=JUDGE_MODEL, include_reason=True),
        FaithfulnessMetric(model=JUDGE_MODEL, include_reason=True),
        AnswerRelevancyMetric(model=JUDGE_MODEL, include_reason=True),
    ]

    # 타임아웃/rate limit 방지: 작은 묶음으로 나누고, 배치 사이에 대기시간을 둠
    BATCH_SIZE = 2
    BATCH_DELAY_SECONDS = 15
    all_test_results = []

    for batch_start in range(0, len(all_test_cases), BATCH_SIZE):
        batch = all_test_cases[batch_start: batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(all_test_cases) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n--- 배치 {batch_num}/{total_batches} 실행 중 ({len(batch)}개 케이스) ---")

        try:
            batch_results = evaluate(test_cases=batch, metrics=metrics)
            all_test_results.extend(batch_results.test_results)
        except Exception as e:
            print(f"  ⚠️  배치 {batch_num} 실패: {e}")
            print(f"  이 배치는 건너뛰고 계속 진행합니다.")
            continue

        if batch_start + BATCH_SIZE < len(all_test_cases):
            print(f"  (rate limit 방지를 위해 {BATCH_DELAY_SECONDS}초 대기...)")
            time.sleep(BATCH_DELAY_SECONDS)

    # ---- 결과 집계 ----
    # metric 이름별로 카테고리별 점수 누적
    scores_by_metric_category = defaultdict(lambda: defaultdict(list))
    scores_by_metric_overall = defaultdict(list)

    csv_rows = []

    for test_result in all_test_results:
        category = None
        # test_result.input으로 원본 케이스 역추적해서 category 매핑
        matched_item = next(
            (item for item in testset if item["question"] == test_result.input), None
        )
        category = matched_item["category"] if matched_item else "unknown"
        q_type = matched_item["type"] if matched_item else "unknown"

        row = {
            "category": category,
            "type": q_type,
            "question": test_result.input,
        }

        for metric_data in test_result.metrics_data:
            metric_name = metric_data.name
            score = metric_data.score
            reason = metric_data.reason

            scores_by_metric_category[metric_name][category].append(score)
            scores_by_metric_overall[metric_name].append(score)

            row[f"{metric_name}_score"] = score
            row[f"{metric_name}_reason"] = reason

        csv_rows.append(row)

    # ---- 콘솔 출력 ----
    print("\n" + "=" * 70)
    print("DeepEval 평가 결과")
    print("=" * 70)

    for metric_name, scores in scores_by_metric_overall.items():
        avg = sum(scores) / len(scores)
        print(f"\n--- {metric_name} ---")
        print(f"전체 평균: {avg:.2f}")

        print("카테고리별 평균:")
        for category, cat_scores in scores_by_metric_category[metric_name].items():
            cat_avg = sum(cat_scores) / len(cat_scores)
            print(f"  {category:10s}: {cat_avg:.2f} (n={len(cat_scores)})")

    # ---- CSV 저장 (reasoning 포함, 문서화용) ----
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        print(f"\n상세 결과(reasoning 포함)가 {OUTPUT_CSV_PATH} 에 저장되었습니다.")


if __name__ == "__main__":
    run()