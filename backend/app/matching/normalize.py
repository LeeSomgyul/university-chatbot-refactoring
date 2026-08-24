# ===============================================
# [정규화] 사용자의 입력값과 DB에서 공백 및 마침표 제거
# ===============================================
import re

def normalize(text: str) -> str:
    text = re.sub(r'\s+', '', text) # 공백 제거
    text = text.replace('.', '')    # 마침표 제거
    return text.strip()