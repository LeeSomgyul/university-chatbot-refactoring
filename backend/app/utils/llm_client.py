from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from app.config import settings

_llm = None

# [싱글톤] ChatOpenAI 인스턴스 생성
def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key
        )
    return _llm


# [보조메서드] 리뷰 목록을 받아서 LLM으로 한두 문장 요약 생성
def generate_review_summary(reviews: list[str]) -> str:
    llm = get_llm()

    review_list = chr(10).join(f'- {r}' for r in reviews)
    prompt = (
        f"다음은 한 가게에 대한 학생들의 리뷰입니다:\n"
        f"{review_list}\n\n"
        f"이 리뷰들을 종합해서, 이 가게의 특징을 한두 문장으로 자연스럽게 요약해주세요. "
        f"과장하지 말고 리뷰에 실제로 언급된 내용만 반영하세요."
    )

    response = llm.invoke([HumanMessage(content=prompt)])

    return response.content

