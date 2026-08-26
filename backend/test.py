# test.py
from app.chat.agent.tools import search_restaurant

result = search_restaurant.invoke({
    "name": "search_restaurant",
    "type": "tool_call",
    "id": "test_id",
    "args": {
        "message": "정문 근처 분식 추천",
        "location_keyword": "정문",
        "food_keyword": ["분식"],
        "state": {
            "messages": [],
            "user_profile": None,
            "last_restaurant_search": None,
            "last_search_sections": None,   # ← 추가
        },
    },
})

print(result)