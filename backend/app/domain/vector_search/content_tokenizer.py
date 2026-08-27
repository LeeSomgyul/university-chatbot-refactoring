# ===============================================
# [서비스] documents 테이블의 content에 들어올 문장을 형태소 분석 하여 content_morpheme에 저장
# ===============================================

from app.utils.kiwi_client import get_kiwi

# NNG: 일반 명사 / NNP: 고유 명사
# SL: 영문 / SN: 숫자
# W_SERIAL: 전화번호 / W_EMAIL: 이메일 / W_URL: URL 
_SEARCH_TAGS = {"NNG", "NNP", "SL", "SN", "W_SERIAL", "W_EMAIL", "W_URL"}


# [메인 함수] 원본 content에 대한 형태소 분석 
# 입력: "리눅스시스템(CS0857)은 3학년 전공필수 과목으로 운영체제를 실습합니다."
# 출력: "리눅스 시스템 CS0857 3 학년 전공 필수 과목 운영 체제 실습"
def extract_content_morpheme(text: str) -> str:
    if not text or not text.strip():
        return ""

    kiwi = get_kiwi()

    # 1. 형태소 분석
    tokens = kiwi.tokenize(text)

    # 2. 쪼개진 token에서 _SEARCH_TAGS 조건에 맞는 것만 저장
    search_tokens = []

    for token in tokens:
        if token.tag in _SEARCH_TAGS:
            search_tokens.append(token.form)

    # 3. []의 token들 사이에 공백 넣어서 한 문장 만들기 
    return " ".join(search_tokens)

# ------------------------------------------------------

# 식별자와 일반 명사를 나누어 가중치 점수를 다르게 한다.
# 숫자(SN)는 길이에 따라 다르기 때문에 함수에서 따로 처리 
_IDENTIFIER_TAGS = {"SL", "W_SERIAL", "W_EMAIL", "W_URL"}
_NOUN_TAGS = {"NNG", "NNP"}

_MIN_IDENTIFIER_DIGIT_LENGTH = 3 # 숫자 길이가 3 이상이면 식별자로 보기


# [메인 함수] 사용자의 질문에 대한 형태소 분석
# 입력: "부재중 전화가 찍혀있는데 061-750-5067 번호가 학교 어디 부서야?"
# 출력: ("061 750 5067", "부재중 전화 번호 학교 부서")
def extract_content_morpheme_weighted(text: str) -> tuple[str, str]:
    if not text or not text.strip():
        return "", ""

    kiwi = get_kiwi()

    tokens = kiwi.tokenize(text)

    identifier_tokens = []
    for token in tokens:
        if token.tag in _IDENTIFIER_TAGS:
            identifier_tokens.append(token.form)
        elif token.tag == "SN" and len(token.form) >= _MIN_IDENTIFIER_DIGIT_LENGTH:
            identifier_tokens.append(token.form)

    noun_tokens = []
    for token in tokens:
        if token.tag in _NOUN_TAGS:
            noun_tokens.append(token.form)
        elif token.tag == "SN" and len(token.form) < _MIN_IDENTIFIER_DIGIT_LENGTH:
            noun_tokens.append(token.form)

    identifier_text = " ".join(identifier_tokens)
    noun_text = " ".join(noun_tokens)

    return identifier_text, noun_text