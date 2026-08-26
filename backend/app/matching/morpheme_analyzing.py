# ===============================================
# [3단계] 형태소분석을 통해 명사만 추출
# ===============================================
# - 역할: 1단계 Aho-Corasick 알고리즘에서 인식되지 못한 단어를 형태소 분석을 통해 명사만 남긴다.

from app.utils.kiwi_client import get_kiwi

_NOUN_TAGS = {"NNG", "NNP"} # 일반명사, 고유명사를 '명사'로 인정 


# [메인 함수] 형태소 분석 실행 
# 입력 텍스트에서 명사만 추출해서 이어붙인 문자열을 반환
# 예: "이산수학을" -> "이산" + "수학" = "이산수학"
def extract_nouns(text: str) -> str:
    kiwi = get_kiwi()

    # 1. 문장을 최소 단위로 쪼갬
    # 예: "이산수학과" -> [Token(form='이산수학', tag='NNG'), Token(form='과', tag='JC')]
    tokens = kiwi.tokenize(text)

    # 2. 일반명사, 고유명사에 해당하는 단어들만 추출 (예: ["이산", "수학"])
    nouns = [token.form for token in tokens if token.tag in _NOUN_TAGS]

    # 3. 명사를 하나도 못 찾은 경우 그대로 반환 (예: "이산수학을")
    if not nouns:
        return text

    # 4. 추출한 명사 합치기 (예: "이산수학")
    return "".join(nouns)

