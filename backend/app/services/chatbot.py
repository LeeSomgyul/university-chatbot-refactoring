"""
챗봇 메인 로직 - 모든 서비스 통합
"""
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.config import settings
from app.models.schemas import UserProfile, ChatMessage
from app.services.query_router import query_router
from app.domain.vector_search.service import get_vector_service
from app.domain.curriculum.service import curriculum_service_optimized as curriculum_service
from app.services.entity_extractor import entity_extractor
from app.domain.review.service import get_review_service

class SchoolChatbot:
    """학교 챗봇 메인 클래스"""
    
    # ===== 초기화 =====
    def __init__(self):
        self.llm = None
        self.vector_service = get_vector_service()
        self.review_service = get_review_service()
    
    def _get_llm(self) -> ChatOpenAI:
        """LLM 인스턴스 가져오기 (싱글톤)"""
        if self.llm is None:
            self.llm = ChatOpenAI(
                model=settings.model_name,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
                openai_api_key=settings.openai_api_key
            )
        return self.llm
    
    # ===== 메인 로직 =====
    def chat(
        self,
        message: str,
        user_profile: Optional[UserProfile] = None,
        history: List[ChatMessage] = None
    ) -> Dict[str, Any]:
        """메인 챗봇 로직"""
        
        if history is None:
            history = []
        
        # 1. 질문 분류
        query_type = query_router.classify(message)
        needs_profile = query_router.needs_user_profile(message)
        
        # 2. general 질문 처리 (벡터 DB)
        if query_type == "general":
            return self._handle_general_query(message, history)
        
        # 2-1. 강의평가 처리
        if query_type == "review":
            return self._handle_review_query(message, history)
        
        # 3. curriculum 질문 처리 (관계형 DB)
        if query_type == "curriculum":
            
            # 메시지에서 정보 추출
            extracted = entity_extractor.extract_course_info(message)
            
            # 3-1. 학번 + 과목 정보 충분하면 → UserProfile 생성
            if extracted['has_enough_info']:
                user_profile = UserProfile(
                    admission_year=extracted['admission_year'],
                    courses_taken=extracted['courses']
                )
                print(f"✅ UserProfile 자동 생성: {extracted['admission_year']}학번, {len(extracted['courses'])}과목")
                
                result = self._handle_curriculum_query(message, user_profile, history)
                result['user_profile'] = user_profile
                return result
            
            # 3-2. 학번만 있음 → 교육과정 조회 or 동일대체 가능
            elif extracted['admission_year']:
                print(f"✅ 입학년도만 있음: {extracted['admission_year']}학번")
                
                user_profile = UserProfile(
                    admission_year=extracted['admission_year'],
                    courses_taken=[]
                )
                
                return self._handle_curriculum_query(message, user_profile, history)
            
            # 3-3. 기존 user_profile 있음 → 그대로 사용
            elif user_profile:
                print(f"✅ 기존 UserProfile 사용: {user_profile.admission_year}학번")
                return self._handle_curriculum_query(message, user_profile, history)
            
            # 3-4. 정보 부족 → 안내 메시지
            else:
                print("❌ 정보 부족: 안내 메시지 반환")
                
                # === 동일대체 질문인지 체크 (추가!) ===
                is_equivalent_query = any(kw in message for kw in [
                    '대신', '대체', '동일대체', '바뀐', '변경', '바꿔'
                ])
                
                if is_equivalent_query:
                    # 동일대체 질문 → general(벡터 DB)로 우회
                    print("  → 동일대체 질문 감지, general로 우회")
                    return self._handle_general_query(message, history)
                
                curriculum_intent = any(kw in message for kw in [
                    '전공필수', '전공선택', '교양필수', '교양선택',
                    '전필', '전선', '교필', '교선',
                    '뭐야', '알려줘', '리스트', '목록'
                ])
                
                if curriculum_intent:
                    return {
            "message": """교육과정 정보를 알려드리려면 입학년도가 필요해요! 😊

몇 학번이신가요?

💡 예시:
"2024학번 전공필수 뭐야?"
"25학번 교양 필수 알려줘"
"2024학번인데 전공선택 과목 리스트 보여줘"
""",
            "query_type": query_type,
            "sources": [],
            "needs_profile": True
        }
                
                return {
                "message": """개인 맞춤 답변을 위해 다음 정보가 필요해요! 😊

📅 입학년도: 몇 학번이신가요?
📚 이수한 과목: 학번과 과목명 또는 과목코드를 알려주세요.
   (과목명, 과목코드는 콤마로 구분해 주세요.)

💡 예시:
"2024학번이고 컴퓨터과학, 이산수학, 데이터베이스 들었어. 졸업사정 해줘."
또는
"24학번, CS0614, XG0800 들었어"
""",
                "query_type": query_type,
                "sources": [],
                "needs_profile": True
            }
    
        # 4. 기본값 (혹시 모를 경우)
        else:
            return self._handle_general_query(message, history)
              
    # 1-1. 개인 졸업사정 → 폼 반환
    def _handle_curriculum_query(
        self, 
        message: str, 
        user_profile: UserProfile,
        history: List = None
    ) -> Dict[str, Any]:
        """교육과정 질문 처리"""
        
        if history is None:
            history = []
        
        # ===== 1. 동일대체 질문 → general로 우회 =====
        if any(kw in message for kw in ['대신', '대체', '바뀐', '과목명', '같은', '동일대체', '변경']):
            print("  → 동일대체 질문 감지, general(벡터 DB)로 우회")
            return self._handle_general_query(message, history)
        
        # ===== 2. 졸업사정 키워드 체크 =====
        if self._is_graduation_check_intent(message):
            
            # 2-1. 과목 정보 있으면 → 졸업사정 진행
            if user_profile.courses_taken:
                print("  → 과목 정보 있음, 졸업사정 처리")
                
                # 남은 학점 계산
                calculation = curriculum_service.calculate_remaining_credits(user_profile)
                
                if 'error' in calculation:
                    return {
                        "message": calculation['error'],
                        "query_type": "curriculum",
                        "sources": [],
                        "needs_profile": False
                    }
                
                # 포맷팅된 결과
                formatted_info = curriculum_service.format_curriculum_info(calculation)
                
                # 미이수 전공필수 과목 추가 (선택적)
                additional_info = ""
                if any(kw in message for kw in ['과목', '뭐', '어떤', '필수', '남은', '남았']):
                    not_taken = curriculum_service.get_required_courses_not_taken(
                        user_profile,
                        course_area="전공",
                        requirement_type="전공필수"
                    )
                    
                    if not_taken:
                        formatted_not_taken = curriculum_service.format_not_taken_courses(not_taken)
                        additional_info = "\n\n" + formatted_not_taken
                
                return {
                    "message": formatted_info + additional_info,
                    "query_type": "curriculum",
                    "sources": [],
                    "needs_profile": False
                }
            
            # 2-2. 과목 정보 없으면 → 개인정보 요청
            else:
                print("  → 과목 정보 없음, 개인정보 요청")
                return {
                    "message": """개인 맞춤 답변을 위해 다음 정보가 필요해요! 😊

    📅 입학년도: 몇 학번이신가요?
    📚 이수한 과목: 학번과 과목명 또는 과목코드를 알려주세요.
    (과목명, 과목코드는 콤마로 구분해 주세요.)

    💡 예시:
    "2024학번이고 컴퓨터과학, 이산수학, 데이터베이스 들었어. 졸업사정 해줘."
    또는 "24학번, CS0614, XG0800 들었어"
    """,
                    "query_type": "curriculum",
                    "sources": [],
                    "needs_profile": True
                }
        
        # ===== 3. 교육과정 조회 (과목 정보 없음) =====
        if not user_profile.courses_taken:
            print("  → 과목 정보 없음, 교육과정 조회 모드")
            
            # 요건 타입 추출
            req_info = self._extract_requirement_type(message)
            
            if req_info['type']:
                # 해당 요건의 전체 과목 리스트 반환
                return self._handle_requirement_list_query(
                    user_profile.admission_year,
                    req_info['area'],
                    req_info['type']
                )
            else:
                # 키워드 없음 → 재질문
                return {
                    "message": f"""{user_profile.admission_year}학번 어떤 과목 정보를 알려드릴까요? 😊

    1️⃣ 전공필수 - 꼭 들어야 하는 전공 과목
    2️⃣ 전공선택 - 선택할 수 있는 전공 과목  
    3️⃣ 교양 - 교양 필수 과목

    💡 예시:
    "{user_profile.admission_year}학번 전공필수 뭐야?"
    "{user_profile.admission_year}학번 교양 필수 알려줘"
    """,
                    "query_type": "curriculum",
                    "sources": [],
                    "needs_profile": False
                }
        
        # ===== 3. 개인 졸업사정 (과목 정보 있음) =====
        print("  → 개인 졸업사정 처리")
        
        # 3-1. 남은 학점 계산
        calculation = curriculum_service.calculate_remaining_credits(user_profile)
        
        if 'error' in calculation:
            return {
                "message": calculation['error'],
                "query_type": "curriculum",
                "sources": [],
                "needs_profile": False
            }
        
        # 3-2. 포맷팅된 결과
        formatted_info = curriculum_service.format_curriculum_info(calculation)
        
        # 3-3. 미이수 전공필수 과목 추가 (선택적)
        additional_info = ""
        if any(kw in message for kw in ['과목', '뭐', '어떤', '필수', '남은', '남았']):
            not_taken = curriculum_service.get_required_courses_not_taken(
                user_profile,
                course_area="전공",
                requirement_type="전공필수"
            )
            
            if not_taken:
                formatted_not_taken = curriculum_service.format_not_taken_courses(not_taken)
                additional_info = "\n\n" + formatted_not_taken
        
        # 3-4. 폼 반환
        return {
            "message": formatted_info + additional_info,
            "query_type": "curriculum",
            "sources": [],
            "needs_profile": False
        }
    
    # 1-2. 개인 졸업사정 → llm 파악
    def _is_graduation_check_intent(self, message: str) -> bool:
        """졸업사정 의도 파악 (LLM)"""
        
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 사용자 의도 분석 전문가입니다.
    사용자가 "개인 졸업사정"을 요청하는지 판단하세요.

    개인 졸업사정 = 내가 졸업 요건을 충족했는지, 남은 학점이 뭔지 확인하는 것

    예시 (졸업사정 O):
    - "졸업사정해줘"
    - "나 졸업할 수 있어?"
    - "졸업 요건 충족했나?"
    - "남은 학점 확인해줘"
    - "내가 뭐 더 들어야 해?"
    - "졸업 가능한지 봐줘"
    - "학점 체크해줘"

    예시 (졸업사정 X):
    - "전공필수 뭐야?" → 과목 리스트 조회
    - "교양 필수 알려줘" → 과목 리스트 조회
    - "졸업 요건이 뭐야?" → 일반 설명 (general)

    응답 형식 (단어 하나만):
    yes / no"""),
            ("user", f"질문: {message}\n\n졸업사정 의도인가요?")
        ])
        
        try:
            llm = self._get_llm()
            chain = intent_prompt | llm
            response = chain.invoke({})
            
            result = response.content.strip().lower()
            is_graduation = 'yes' in result
            
            print(f"  🤖 LLM 의도 분석: {message} → 졸업사정={is_graduation}")
            return is_graduation
        
        except Exception as e:
            print(f"⚠️ LLM 의도 분석 실패, 키워드 폴백: {e}")
            
            # 폴백: 키워드
            graduation_keywords = [
                '졸업사정', '졸업', '남은학점', '남은', '학점체크',
                '요건충족', '충족', '이수확인', '확인'
            ]
            return any(kw in message.replace(' ', '') for kw in graduation_keywords)
    
    # 2. 교육과정 조회    
    def _handle_requirement_list_query(
        self,
        admission_year: int,
        course_area: str,
        requirement_type: str
    ) -> Dict[str, Any]:
        """요건별 전체 과목 리스트 반환"""
        
        try:
            from app.database.supabase_client import supabase
            
            # DB에서 해당 요건의 모든 과목 조회
            result = supabase.table('curriculums')\
                .select('*')\
                .eq('admission_year', admission_year)\
                .eq('course_area', course_area)\
                .eq('requirement_type', requirement_type)\
                .order('grade')\
                .order('semester')\
                .order('course_code')\
                .execute()
            
            # 과목이 없으면 = 해당 학번에 이 요건이 없음
            if not result.data:
                # 해당 학번의 사용 가능한 요건 조회
                available_result = supabase.table('curriculums')\
                    .select('requirement_type')\
                    .eq('admission_year', admission_year)\
                    .eq('course_area', course_area)\
                    .execute()
                
                available_types = list(set([r['requirement_type'] for r in available_result.data]))
                
                message = f"{admission_year}학번에는 '{requirement_type}' 요건이 없어요. 😥\n\n"
                
                if available_types:
                    message += f"💡 {admission_year}학번 {course_area} 요건:\n"
                    for req_type in sorted(available_types):
                        message += f"  • {req_type}\n"
                    message += f"\n위 요건 중 하나를 선택해서 질문해주세요!"
                else:
                    message += f"{admission_year}학번 {course_area} 정보를 찾을 수 없어요."
                
                return {
                    "message": message,
                    "query_type": "curriculum",
                    "sources": [],
                    "needs_profile": False
                }
            
            # 중복 제거
            seen = set()
            unique_courses = []
            
            for course in result.data:
                code = course['course_code']
                if code not in seen:
                    seen.add(code)
                    unique_courses.append(course)
            
            print(f"  총 {len(result.data)}개 → 중복 제거 후 {len(unique_courses)}개")
            
            # 포맷팅
            answer = f"{admission_year}학번 {requirement_type} 과목 목록이에요!\n\n"
            
            current_grade = None
            for course in unique_courses:  # ← unique_courses 사용!
                grade = course.get('grade')
                semester = course.get('semester')
                
                # 학년별 그룹화
                if grade != current_grade:
                    current_grade = grade
                    answer += f"\n🧑‍🎓 {grade}학년\n"
                
                # 과목 정보
                answer += f"  • {course['course_code']} {course['course_name']} ({course['credit']}학점)"
                
                if semester:
                    answer += f" - {semester}학기 권장"
                
                answer += "\n"
            
            # 총 과목 수와 학점
            total_courses = len(unique_courses)
            total_credits = sum(c['credit'] for c in unique_courses)
            
            # 필요 학점 정보 추가
            # 필요 학점 정보 추가
            if '선택' in requirement_type:
                required_credits = self._get_required_credits(admission_year, requirement_type)
                
                if required_credits:
                    answer += f"\n💡 총 {total_courses}개 과목 ({total_credits}학점) 중 선택하여 {required_credits}학점을 채우면 돼요!"
                else:
                    answer += f"\n💡 총 {total_courses}개 과목 ({total_credits}학점) 중 선택하여 이수하면 돼요!"
            else:
                # 전공필수, 교양필수 등 - 모두 이수
                answer += f"\n💡 총 {total_courses}개 과목, {total_credits}학점 모두 이수해야 해요!"
            
            return {
                "message": answer,
                "query_type": "curriculum",
                "sources": [],
                "needs_profile": False
            }
        
        except Exception as e:
            print(f"❌ 요건 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "message": "죄송해요, 과목 정보를 가져오는 중 오류가 발생했어요. 😥",
                "query_type": "curriculum",
                "sources": [],
                "needs_profile": False
            }    
        
    # ===== 일반 정보 =====
    def _handle_general_query(self, message: str, history: List = None) -> Dict[str, Any]:
        """일반 정보 질문 처리 (벡터 검색)"""
        
        #이전 질문 저장
        if history is None:
            history = []
        
        # 이전 대화 있다면 쿼리 재구성    
        search_query = message
        
        # 이전 대화가 있을 때만
        if history:  
            try:
                # 대화 이력 텍스트로 변환
                history_text = ""
                for msg in history[-4:]:  # 최근 4개만
                    role = "학생" if msg["role"] == "user" else "챗봇"
                    history_text += f"{role}: {msg['content']}\n"
                
                # 쿼리 재구성 프롬프트
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
    출력: 중앙도서관 운영시간

    예시 3 (연락처):
    이전 대화:
    학생: 학생지원팀 연락처 알려줘
    챗봇: 학생지원팀은 061-750-3114입니다

    현재 질문: 거기 위치는?
    출력: 학생지원팀 위치

    예시 4 (일반):
    이전 대화:
    학생: 철학 교양 추천해줘
    챗봇: 철학으로 문화읽기 추천해요

    현재 질문: 다른거 없어?
    출력: 철학 교양과목 추천"""),
        ("user", f"""이전 대화:
    {history_text}

    현재 질문: {message}

    재구성된 검색 쿼리:""")
                ])
                
                llm = self._get_llm()
                rewrite_chain = rewrite_prompt | llm
                rewrite_response = rewrite_chain.invoke({})
                search_query = rewrite_response.content.strip()
                
                print(f"\n🔍 쿼리 재구성:")
                print(f"  원본: {message}")
                print(f"  재구성: {search_query}")
                
            except Exception as e:
                print(f"⚠️ 쿼리 재구성 실패, 원본 사용: {e}")
                search_query = message
        
        # 벡터 검색
        search_results = self.vector_service.search(search_query, k=5)
        
        if not search_results:
            return {
                "message": "죄송해요, 관련 정보를 찾을 수 없어요. 다른 질문을 해주시겠어요? 🤔",
                "query_type": "general",
                "sources": [],
                "needs_profile": False
            }
        
        # 검색 결과를 컨텍스트로 사용
        context = self.vector_service.format_search_results(search_results)
        
        # LLM 프롬프트
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
7. 이전 대화 맥락을 고려하여 답변하세요. "그거", "그 과목" 같은 표현이 나오면 이전 대화에서 언급된 내용을 참조하세요

검색된 정보:
{context}
""")
    ]
        # 이전 대화 이력
        for msg in history:
            if msg["role"] == "user":
                messages.append(("user", msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(("assistant", msg["content"]))
                
        # 현재 질문        
        messages.append(("user", message))
        
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # LLM 호출
        llm = self._get_llm()
        chain = prompt | llm
        
        try:
            response = chain.invoke({})
            answer = response.content
        except Exception as e:
            print(f"❌ LLM 호출 실패: {e}")
            import traceback
            traceback.print_exc()
            
            # 검색 결과가 있으면 최소한의 정보라도 제공
            if search_results:
                answer = f"검색 결과를 찾았지만 답변 생성 중 오류가 발생했어요.\n\n검색된 정보:\n{context[:200]}..."
            else:
                answer = "죄송해요, 답변 생성 중 오류가 발생했어요. 다시 시도해주세요. 😅"
        
        return {
            "message": answer,
            "query_type": "general",
            "sources": search_results,
            "needs_profile": False
        }

    # ===== 강의평가 핸들러 =====
    def _handle_review_query(self, message: str, history: List = None) -> Dict[str, Any]:
        """
        강의평가 질문 처리 - 개선 버전
        
        1. 작성 요청 → 구글폼 링크
        2. 후기 검색 → 교수+강의 필터링, 요약형 출력
        3. 상세 후기 → 2개씩 보여주기
        4. 다른 평 → 추가 2개 보여주기
        """
        
        if history is None:
            history = []
        
        # ===== 1. 강의평가 작성 요청 =====
        write_keywords = ['작성', '쓰고', '남기고', '제출', '링크', '폼', '어디']
        if any(kw in message for kw in write_keywords):
            print("  → 강의평가 작성 링크 요청")
            
            return {
                "message": f"""강의평가를 작성하시려면 아래 링크로 접속해주세요! 📝

{settings.course_review_form_url}

작성하신 후기는 검토 후 챗봇에서 검색 가능하게 됩니다. 😊
솔직한 의견 부탁드려요!""",
                "query_type": "review",
                "sources": [],
                "needs_profile": False
            }
        
        # ===== 2. "다른 평 보여줘" 요청 =====
        if '다른' in message and '평' in message:
            print("  → 다른 평 요청 감지")
            
            # 이전 대화에서 강의명/교수명 추출
            if history:
                for msg in reversed(history[-5:]):  # 최근 5개 메시지
                    if msg['role'] == 'user' and '후기' in msg['content']:
                        # 이전 질문 재활용
                        extracted = self.review_service.extract_professor_and_course(msg['content'])
                        professor = extracted.get('professor')
                        course = extracted.get('course')
                        
                        if professor or course:
                            print(f"  이전 질문에서 추출: professor={professor}, course={course}")
                            
                            search_results = self.review_service.search_reviews(
                                query=msg['content'],
                                k=10,  # 더 많이 가져오기
                                professor_filter=professor,
                                course_filter=course
                            )
                            
                            if search_results:
                                # 다른 평 = 2-3번 후기 (인덱스 2부터)
                                more_reviews = self.review_service.format_review_summary(
                                    search_results, 
                                    detail_mode="more",
                                    start_index=2
                                )
                                
                                return {
                                    "message": more_reviews,
                                    "query_type": "review",
                                    "sources": search_results[2:4],
                                    "needs_profile": False
                                }
            
            # 이전 대화 없으면 안내
            return {
                "message": "어떤 강의의 다른 후기를 보고 싶으신가요? 교수님 성함과 강의명을 함께 알려주세요! 😊",
                "query_type": "review",
                "sources": [],
                "needs_profile": False
            }
        
        # ===== 3. "상세 후기" 요청 =====
        if '상세' in message and '후기' in message:
            print("  → 상세 후기 요청 감지")
            
            # 이전 대화에서 강의명/교수명 추출
            if history:
                for msg in reversed(history[-5:]):  # 최근 5개 메시지
                    if msg['role'] == 'user' and '후기' in msg['content']:
                        # 이전 질문 재활용
                        extracted = self.review_service.extract_professor_and_course(msg['content'])
                        professor = extracted.get('professor')
                        course = extracted.get('course')
                        
                        if professor or course:
                            print(f"  이전 질문에서 추출: professor={professor}, course={course}")
                            
                            search_results = self.review_service.search_reviews(
                                query=msg['content'],
                                k=10,
                                professor_filter=professor,
                                course_filter=course
                            )
                            
                            if search_results:
                                detailed = self.review_service.format_review_summary(
                                    search_results, 
                                    detail_mode="detail"
                                )
                                
                                return {
                                    "message": detailed,
                                    "query_type": "review",
                                    "sources": search_results[:2],
                                    "needs_profile": False
                                }
            
            # 이전 대화 없으면 안내
            return {
                "message": "어떤 강의의 상세 후기를 보고 싶으신가요? 교수님 성함과 강의명을 함께 알려주세요! 😊",
                "query_type": "review",
                "sources": [],
                "needs_profile": False
            }
        
        # ===== 4. 강의평가 검색 =====
        print("  → 강의평가 검색")
        
        # 교수명/강의명 추출
        extracted = self.review_service.extract_professor_and_course(message)
        professor = extracted.get('professor')
        course = extracted.get('course')
        
        print(f"  추출 결과: professor={professor}, course={course}")
        
        # ===== 케이스 1: 교수 + 강의 모두 있음 → 바로 검색 =====
        if professor and course:
            print("  → 교수 + 강의 모두 있음, 검색 진행")
            
            search_results = self.review_service.search_reviews(
                query=message,
                k=10,
                professor_filter=professor,
                course_filter=course
            )
            
            if not search_results:
                return {
                    "message": f"""😥 {professor} 교수님의 {course} 강의 후기를 찾을 수 없어요.

혹시 강의평가를 작성하고 싶으신가요?
"강의평가 작성하고싶어" 라고 말씀해주시면 링크를 안내해드릴게요!""",
                    "query_type": "review",
                    "sources": [],
                    "needs_profile": False
                }
            
            # 요약형 출력
            summary = self.review_service.format_review_summary(
                search_results, 
                detail_mode="summary"
            )
            
            return {
                "message": summary,
                "query_type": "review",
                "sources": search_results,
                "needs_profile": False
            }
        
        # ===== 케이스 2: 강의명만 있음 → 교수 목록 보여주고 재질문 =====
        elif course and not professor:
            print("  → 강의명만 있음, 교수 목록 조회")
            
            professors = self.review_service.get_professors_by_course(course)
            
            if not professors:
                return {
                    "message": f"""😥 {course} 강의에 대한 후기를 찾을 수 없어요.

혹시 강의평가를 작성하고 싶으신가요?
"강의평가 작성하고싶어" 라고 말씀해주시면 링크를 안내해드릴게요!""",
                    "query_type": "review",
                    "sources": [],
                    "needs_profile": False
                }
            
            # 교수 목록 포맷팅
            prof_list = "\n".join([
                f"• {p['professor_name']} 교수님 (후기 {p['review_count']}건)"
                for p in professors
            ])
            
            return {
                "message": f"""📚 {course} 강의를 가르치시는 교수님들이에요:

{prof_list}

어느 교수님의 강의 후기가 궁금하신가요?
"{professors[0]['professor_name']} 교수님 {course} 후기 알려줘" 처럼 말씀해주세요! 😊""",
                "query_type": "review",
                "sources": [],
                "needs_profile": False
            }
        
        # ===== 케이스 3: 교수명만 있음 → 해당 교수님 모든 강의 검색 =====
        elif professor and not course:
            print("  → 교수명만 있음, 해당 교수님 강의 검색")
            
            search_results = self.review_service.search_reviews(
                query=message,
                k=10,
                professor_filter=professor
            )
            
            if not search_results:
                return {
                    "message": f"""😥 {professor} 교수님의 강의 후기를 찾을 수 없어요.

혹시 강의평가를 작성하고 싶으신가요?
"강의평가 작성하고싶어" 라고 말씀해주시면 링크를 안내해드릴게요!""",
                    "query_type": "review",
                    "sources": [],
                    "needs_profile": False
                }
            
            # 교수님의 여러 강의 - 강의별로 그룹화
            courses_dict = {}
            for r in search_results:
                course_name = r.get('course_name', '알 수 없음')
                if course_name not in courses_dict:
                    courses_dict[course_name] = []
                courses_dict[course_name].append(r)
            
            # 강의 목록
            course_list = "\n".join([
                f"• {c} ({len(reviews)}건)"
                for c, reviews in courses_dict.items()
            ])
            
            return {
                "message": f"""📚 {professor} 교수님께서 가르치시는 강의들이에요:

{course_list}

어떤 강의의 후기가 궁금하신가요?
"{professor} 교수님 {list(courses_dict.keys())[0]} 후기 알려줘" 처럼 말씀해주세요! 😊""",
                "query_type": "review",
                "sources": search_results,
                "needs_profile": False
            }
        
        # ===== 케이스 4: 둘 다 없음 → 재질문 =====
        else:
            print("  → 교수명/강의명 없음, 재질문")
            
            return {
                "message": """강의 후기를 찾아드릴게요! 😊

어떤 강의의 후기가 궁금하신가요?
교수님 성함과 강의명을 함께 알려주시면 더 정확한 후기를 찾을 수 있어요.

💡 예시:
"김철수 교수님 데이터베이스 강의 후기 알려줘"
"이영희 교수님 자료구조 어때?"

또는 강의평가를 직접 작성하고 싶으시면 "강의평가 작성하고싶어"라고 말씀해주세요!""",
                "query_type": "review",
                "sources": [],
                "needs_profile": False
            }

    # ===== 유틸리티 =====
    def _extract_requirement_type(self, message: str) -> Dict[str, str]:
        """메시지에서 요건 타입 추출"""
        
        req_type = None
        course_area = None
        
        # 전공
        if '전필' in message or '전공필수' in message:
            req_type = '전공필수'
            course_area = '전공'
        elif '전선' in message or '전공선택' in message:
            req_type = '전공선택'
            course_area = '전공'
        
        # 교양
        elif '교필' in message or '교양필수' in message:
            req_type = '공통교양'
            course_area = '교양'
        elif '교선' in message or '교양선택' in message:
            req_type = '교양선택'
            course_area = '교양'
        elif '기초교양' in message or '기초' in message:
            req_type = '기초교양'
            course_area = '교양'
        elif '심화교양' in message or '심화' in message:
            req_type = '심화교양'
            course_area = '교양'
        elif '창의교양' in message or '창의' in message:
            req_type = '창의교양'
            course_area = '교양'
        elif '교양' in message:
            # "교양"만 있으면 공통교양으로 간주 (일반적)
            req_type = '공통교양'
            course_area = '교양'
        
        return {
            'type': req_type,
            'area': course_area
        }
        
    def _get_required_credits(self, admission_year: int, requirement_type: str) -> int:
        """요건별 필요 학점 반환 - DB에서 조회"""
        
        from app.database.supabase_client import supabase
        
        try:
            # DB에서 학번별 요건 정보 조회
            result = supabase.table('graduation_requirements')\
                .select('required_credits')\
                .eq('admission_year', admission_year)\
                .eq('requirement_type', requirement_type)\
                .execute()
            
            if result.data:
                return result.data[0]['required_credits']
            
            # DB에 없으면 None 반환 (기본값 사용 안 함!)
            print(f"⚠️ {admission_year}학번에는 {requirement_type} 정보가 없음")
            return None
            
        except Exception as e:
            print(f"❌ 필요 학점 조회 실패: {e}")
            return None
        

chatbot = SchoolChatbot()