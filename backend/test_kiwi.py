"""
Kiwi 형태소 분석기 테스트
- 설치: pip install kiwipiepy
- 실행: python test_kiwi.py
"""
try:
    from kiwipiepy import Kiwi
except ImportError:
    print("❌ kiwipiepy가 설치되어 있지 않습니다. `pip install kiwipiepy` 실행 후 다시 시도하세요.")
    raise SystemExit(1)


TEST_SENTENCES = [
    "정문 근처 떡볶이 맛집 추천해줘",
    "순천대 후문 쪽에 가성비 좋은 국밥집 있어?",
    "학생회관 앞 카페 알려줘",
    "그냥 맛집 아무데나 추천해줘",
    "정문에서 걸어갈 수 있는 중식당 있나요",
]


def main():
    kiwi = Kiwi()

    for sentence in TEST_SENTENCES:
        print(f"\n입력: {sentence}")

        result = kiwi.analyze(sentence)
        tokens = result[0][0]  # 1-best 결과의 토큰 리스트

        print("형태소 분석:")
        for token in tokens:
            print(f"  {token.form}\t{token.tag}")

        nouns = [token.form for token in tokens if token.tag.startswith("NN")]
        print(f"명사 추출: {nouns}")


if __name__ == "__main__":
    main()
