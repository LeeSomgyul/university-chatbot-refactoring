# ===============================================
# [서비스] documents 테이블의 content에 들어올 문장을 형태소 분석 하여 content_morpheme에 저장
# ===============================================

from app.utils.kiwi_client import get_kiwi

# NNG: 일반 명사
# NNP: 고유 명사
# SL: 영문
# SN: 숫자
_SEARCH_TAGS = {"NNG", "NNP", "SL", "SN"}


# [메인 함수] 원본 content를 형태소 분석하여 공백으로 이어붙인 문자열 반환
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