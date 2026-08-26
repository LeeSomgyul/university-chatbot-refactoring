# ===============================================
#   Kiwi 형태소 분석기 싱글톤 초기화(메모리 등록)
# ===============================================
# 서버 실행될 때 1회 실행되어서 메모리에 kiwi 형태소 분석기 올라옴. 
# 이후 다른 파일에서는 따로 초기화하지 않고 싱글톤 형식으로 공유해서 사용.

from kiwipiepy import Kiwi

_kiwi = None

def get_kiwi() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        _kiwi = Kiwi()
    return _kiwi