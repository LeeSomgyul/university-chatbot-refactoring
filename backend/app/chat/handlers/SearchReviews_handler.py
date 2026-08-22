# ===============================================
#        [핸들러] 관계형DB: 강의평가 검색
# ===============================================

from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage
from app.config import settings
from app.domain.review.service import get_review_service

_review_service = None


def _get_rs():
    global _review_service
    if _review_service is None:
        _review_service = get_review_service()
    return _review_service


def handle_search_reviews_query(message: str, history: List[BaseMessage] = None) -> Dict[str, Any]:
    """강의평가 질문 처리"""
    if history is None:
        history = []
    review_service = _get_rs()

    # ===== 1. 강의평가 작성 요청 =====
    write_keywords = ['작성', '쓰고', '남기고', '제출', '링크', '폼', '어디']
    if any(kw in message for kw in write_keywords):
        print("  → 강의평가 작성 링크 요청")
        return {
            "message": f"""강의평가를 작성하시려면 아래 링크로 접속해주세요! 📝

{settings.course_review_form_url}

작성하신 후기는 검토 후 챗봇에서 검색 가능하게 됩니다. 😊
솔직한 의견 부탁드려요!""",
            "matched_function": "handle_search_reviews_query",
            "sources": [],
            "needs_profile": False
        }

    # ===== 2. "다른 평 보여줘" 요청 =====
    if '다른' in message and '평' in message:
        print("  → 다른 평 요청 감지")
        if history:
            for msg in reversed(history[-5:]):
                if isinstance(msg, HumanMessage) and '후기' in msg.content:
                    extracted = review_service.extract_professor_and_course(msg.content)
                    professor = extracted.get('professor')
                    course = extracted.get('course')
                    if professor or course:
                        search_results = review_service.search_reviews(
                            query=msg.content, k=10,
                            professor_filter=professor, course_filter=course
                        )
                        if search_results:
                            more_reviews = review_service.format_review_summary(
                                search_results, detail_mode="more", start_index=2
                            )
                            return {
                                "message": more_reviews,
                                "matched_function": "handle_search_reviews_query",
                                "sources": search_results[2:4],
                                "needs_profile": False
                            }
        return {
            "message": "어떤 강의의 다른 후기를 보고 싶으신가요? 교수님 성함과 강의명을 함께 알려주세요! 😊",
            "matched_function": "handle_search_reviews_query",
            "sources": [],
            "needs_profile": False
        }

    # ===== 3. "상세 후기" 요청 =====
    if '상세' in message and '후기' in message:
        print("  → 상세 후기 요청 감지")
        if history:
            for msg in reversed(history[-5:]):
                if isinstance(msg, HumanMessage) and '후기' in msg.content:
                    extracted = review_service.extract_professor_and_course(msg.content)
                    professor = extracted.get('professor')
                    course = extracted.get('course')
                    if professor or course:
                        search_results = review_service.search_reviews(
                            query=msg.content, k=10,
                            professor_filter=professor, course_filter=course
                        )
                        if search_results:
                            detailed = review_service.format_review_summary(
                                search_results, detail_mode="detail"
                            )
                            return {
                                "message": detailed,
                                "matched_function": "handle_search_reviews_query",
                                "sources": search_results[:2],
                                "needs_profile": False
                            }
        return {
            "message": "어떤 강의의 상세 후기를 보고 싶으신가요? 교수님 성함과 강의명을 함께 알려주세요! 😊",
            "matched_function": "handle_search_reviews_query",
            "sources": [],
            "needs_profile": False
        }

    # ===== 4. 강의평가 검색 =====
    print("  → 강의평가 검색")
    extracted = review_service.extract_professor_and_course(message)
    professor = extracted.get('professor')
    course = extracted.get('course')
    print(f"  추출 결과: professor={professor}, course={course}")

    if professor and course:
        search_results = review_service.search_reviews(
            query=message, k=10, professor_filter=professor, course_filter=course
        )
        if not search_results:
            return {
                "message": f"""😥 {professor} 교수님의 {course} 강의 후기를 찾을 수 없어요.

혹시 강의평가를 작성하고 싶으신가요?
"강의평가 작성하고싶어" 라고 말씀해주시면 링크를 안내해드릴게요!""",
                "matched_function": "handle_search_reviews_query", "sources": [], "needs_profile": False
            }
        summary = review_service.format_review_summary(search_results, detail_mode="summary")
        return {"message": summary, "matched_function": "handle_search_reviews_query", "sources": search_results, "needs_profile": False}

    elif course and not professor:
        professors = review_service.get_professors_by_course(course)
        if not professors:
            return {
                "message": f"""😥 {course} 강의에 대한 후기를 찾을 수 없어요.

혹시 강의평가를 작성하고 싶으신가요?
"강의평가 작성하고싶어" 라고 말씀해주시면 링크를 안내해드릴게요!""",
                "matched_function": "handle_search_reviews_query", "sources": [], "needs_profile": False
            }
        prof_list = "\n".join([f"• {p['professor_name']} 교수님 (후기 {p['review_count']}건)" for p in professors])
        return {
            "message": f"""📚 {course} 강의를 가르치시는 교수님들이에요:

{prof_list}

어느 교수님의 강의 후기가 궁금하신가요?
"{professors[0]['professor_name']} 교수님 {course} 후기 알려줘" 처럼 말씀해주세요! 😊""",
            "matched_function": "handle_search_reviews_query", "sources": [], "needs_profile": False
        }

    elif professor and not course:
        search_results = review_service.search_reviews(query=message, k=10, professor_filter=professor)
        if not search_results:
            return {
                "message": f"""😥 {professor} 교수님의 강의 후기를 찾을 수 없어요.

혹시 강의평가를 작성하고 싶으신가요?
"강의평가 작성하고싶어" 라고 말씀해주시면 링크를 안내해드릴게요!""",
                "matched_function": "handle_search_reviews_query", "sources": [], "needs_profile": False
            }
        courses_dict = {}
        for r in search_results:
            course_name = r.get('course_name', '알 수 없음')
            courses_dict.setdefault(course_name, []).append(r)
        course_list = "\n".join([f"• {c} ({len(reviews)}건)" for c, reviews in courses_dict.items()])
        return {
            "message": f"""📚 {professor} 교수님께서 가르치시는 강의들이에요:

{course_list}

어떤 강의의 후기가 궁금하신가요?
"{professor} 교수님 {list(courses_dict.keys())[0]} 후기 알려줘" 처럼 말씀해주세요! 😊""",
            "matched_function": "handle_search_reviews_query", "sources": search_results, "needs_profile": False
        }

    else:
        return {
            "message": """강의 후기를 찾아드릴게요! 😊

어떤 강의의 후기가 궁금하신가요?
교수님 성함과 강의명을 함께 알려주시면 더 정확한 후기를 찾을 수 있어요.

💡 예시:
"김철수 교수님 데이터베이스 강의 후기 알려줘"
"이영희 교수님 자료구조 어때?"

또는 강의평가를 직접 작성하고 싶으시면 "강의평가 작성하고싶어"라고 말씀해주세요!""",
            "matched_function": "handle_search_reviews_query", "sources": [], "needs_profile": False
        }