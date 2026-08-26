# ===============================================
#        [핸들러] 벡터DB: 일반 정보 검색
# ===============================================

from typing import Dict, Any, List

from app.utils.llm_client import get_llm
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.config import settings
from app.domain.vector_search.service import get_vector_service
from app.models.schemas import HandlerResponse

_llm = None
_vector_service = None


def _get_vs():
    global _vector_service
    if _vector_service is None:
        _vector_service = get_vector_service()
    return _vector_service

# [일반 정보 질문 처리 (벡터 검색)]
def handle_search_general_query(message: str, history: List[BaseMessage] = None) -> HandlerResponse:
    if history is None:
        history = []

    search_query = message

    if history:
        try:
            history_text = ""
            for msg in history[-4:]:
                role = "학생" if isinstance(msg, HumanMessage) else "챗봇"
                history_text += f"{role}: {msg.content}\n"

            rewrite_prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 검색 쿼리를 개선하는 전문가입니다.
이전 대화를 보고, 사용자의 현재 질문을 벡터 검색에 적합한 명확한 쿼리로 재구성하세요.

규칙:
1. "그거", "그 과목", "그것" 같은 대명사를 이전 대화의 구체적인 명사로 바꾸세요
2. 이전에 언급된 과목명, 주제를 포함하세요
3. 검색에 유용한 핵심 키워드만 남기세요
4. 한 줄로 간결하게 작성하세요
5. 재구성된 쿼리만 출력하세요 (설명 없이)

예시 1 (과목):
이전 대화:
학생: 그림 관련 교양 추천해줘
챗봇: 미술의 이해를 추천합니다

현재 질문: 과목코드 어떻게 돼?
출력: 미술의 이해 과목코드

예시 2 (시설):
이전 대화:
학생: 도서관 위치 어디야?
챗봇: 중앙도서관은 본관 옆에 있어요

현재 질문: 거기 운영시간은?
출력: 중앙도서관 운영시간"""),
                ("user", f"""이전 대화:
{history_text}

현재 질문: {message}

재구성된 검색 쿼리:""")
            ])

            llm = get_llm()
            rewrite_chain = rewrite_prompt | llm
            rewrite_response = rewrite_chain.invoke({})
            search_query = rewrite_response.content.strip()

            print("\n🔍 쿼리 재구성:")
            print(f"  원본: {message}")
            print(f"  재구성: {search_query}")

        except Exception as e:
            print(f"⚠️ 쿼리 재구성 실패, 원본 사용: {e}")
            search_query = message

    vector_service = _get_vs()
    search_results = vector_service.search(search_query, k=5)

    if not search_results:
        return HandlerResponse(
            message="죄송해요, 관련 정보를 찾을 수 없어요. 다른 질문을 해주시겠어요? 🤔",
            matched_function="handle_search_general_query"
        )

    context = vector_service.format_search_results(search_results)

    messages = [
        ("system", f"""당신은 순천대학교 컴퓨터공학과 안내 챗봇입니다.
주어진 정보를 바탕으로 학생의 질문에 친절하고 정확하게 답변해주세요.

답변 규칙:
1. 존댓말을 사용하고 친근하게 답변하세요
2. 주어진 정보에 없는 내용은 "검색된 정보에서 찾을 수 없어요"라고 솔직히 말하세요
3. 답변은 간결하게 핵심만 전달하세요
4. 필요시 이모지를 활용해 친근함을 더하세요
5. 마크다운 문법(**, ##, - 등)을 사용하지 마세요. 순수 텍스트와 이모지만 사용하세요
6. 검색된 정보를 그대로 나열하지 말고, 질문에 맞춰 재구성하세요
7. 이전 대화 맥락을 고려하여 답변하세요.

검색된 정보:
{context}
""")
    ]
    for msg in history:
        if isinstance(msg, HumanMessage):
            messages.append(("user", msg.content))
        elif isinstance(msg, AIMessage):
            messages.append(("assistant", msg.content))
    messages.append(("user", message))

    prompt = ChatPromptTemplate.from_messages(messages)
    llm = get_llm()
    chain = prompt | llm

    try:
        response = chain.invoke({})
        answer = response.content
    except Exception as e:
        print(f"❌ LLM 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        if search_results:
            answer = f"검색 결과를 찾았지만 답변 생성 중 오류가 발생했어요.\n\n검색된 정보:\n{context[:200]}..."
        else:
            answer = "죄송해요, 답변 생성 중 오류가 발생했어요. 다시 시도해주세요. 😅"

    return HandlerResponse(
        message=answer,
        matched_function="handle_search_general_query",
        sources=search_results
    )