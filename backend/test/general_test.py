"""
DeepEval 평가용 actual_output / retrieval_context 수집 스크립트

- general_testset_with_expected.json의 40개 질문을 실제 핸들러 로직
  (handle_search_general_query와 동일한 흐름: hybrid_service.search() -> LLM 답변 생성)
  으로 그대로 통과시켜서 진짜 검색 결과와 진짜 LLM 답변을 수집
- 핸들러 함수 자체를 고치지 않고, 동일한 로직을 여기서 재현
  (핸들러가 retrieval_context를 반환하지 않는 구조라, 평가 스크립트에서
   별도로 같은 흐름을 그대로 따라가며 중간값도 함께 확보)
- 결과를 general_testset_with_actual.json으로 저장

실행 위치: backend/test/
실행 방법: backend 폴더 기준
    $ python test/collect_actual_output.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.domain.vector_search import hybrid_service


TESTSET_PATH = "test/general_testset_with_expected.json"
OUTPUT_PATH = "test/general_testset_with_actual.json"

_llm = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key
        )
    return _llm


# general_handler.py의 시스템 프롬프트와 동일하게 맞춤
# (핸들러가 실제로 답변을 만드는 방식 그대로 재현하기 위함)
_ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 순천대학교 컴퓨터공학과 안내 챗봇입니다.
주어진 정보를 바탕으로 학생의 질문에 친절하고 정확하게 답변해주세요.

답변 규칙:
1. 존댓말을 사용하고 친근하게 답변하세요
2. 주어진 정보에 없는 내용은 "검색된 정보에서 찾을 수 없어요"라고 솔직히 말하세요
3. 답변은 간결하게 핵심만 전달하세요
4. 필요시 이모지를 활용해 친근함을 더하세요
5. 마크다운 문법(**, ##, - 등)을 사용하지 마세요. 순수 텍스트와 이모지만 사용하세요
6. 검색된 정보를 그대로 나열하지 말고, 질문에 맞춰 재구성하세요

검색된 정보:
{context}
"""),
    ("user", "{question}")
])


def format_context(search_results) -> tuple[str, list[str]]:
    """
    hybrid_service.search() 결과를 LLM 프롬프트용 문자열과
    DeepEval retrieval_context용 리스트 두 가지 형태로 만듦
    """
    formatted_list = []
    for i, r in enumerate(search_results, 1):
        title = r.metadata.get("title", "제목없음")
        formatted_list.append(f"[{i}] {title}\n{r.content}")

    context_str = "\n\n".join(formatted_list)
    # retrieval_context는 DeepEval 관례상 문서 단위 리스트로 넣음
    return context_str, formatted_list


def run():
    with open(TESTSET_PATH, "r", encoding="utf-8") as f:
        testset = json.load(f)

    llm = _get_llm()
    print(f"총 {len(testset)}개 질문에 대해 actual_output / retrieval_context 수집 시작...")

    for i, item in enumerate(testset, 1):
        question = item["question"]

        # 1. 실제 핸들러와 동일하게 하이브리드 검색 수행 (k=5, 운영값과 동일)
        search_results = hybrid_service.search(question, k=5)

        if not search_results:
            item["actual_output"] = "죄송해요, 관련 정보를 찾을 수 없어요. 다른 질문을 해주시겠어요? 🤔"
            item["retrieval_context"] = []
            print(f"  [{i}/{len(testset)}] {question[:30]}... (검색 결과 없음)")
            continue

        context_str, context_list = format_context(search_results)

        # 2. 실제 핸들러와 동일한 프롬프트로 LLM 답변 생성
        chain = _ANSWER_PROMPT | llm
        response = chain.invoke({"context": context_str, "question": question})

        item["actual_output"] = response.content.strip()
        item["retrieval_context"] = context_list

        print(f"  [{i}/{len(testset)}] {question[:30]}...")
        print(f"      → {item['actual_output'][:60]}...")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(testset, f, ensure_ascii=False, indent=2)

    print(f"\n완료. 결과가 {OUTPUT_PATH} 에 저장되었습니다.")


if __name__ == "__main__":
    run()