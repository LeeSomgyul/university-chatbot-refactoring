"""
FastAPI 메인 애플리케이션 - 통합 버전
"""
import sys
import traceback

from app.api import graduation, restaurant

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from datetime import datetime
    import asyncio
    from contextlib import asynccontextmanager

    from app.config import settings
    print("✅ config import 성공")
    
    from app.models.schemas import (
        ChatRequest,
        ChatResponse,
        HealthCheck,
        UserProfile
    )
    print("✅ schemas import 성공")
    
    from app.models.session import session_store
    print("✅ session_store import 성공")
    
    from app.chat.dispatcher import chat as chat_dispatcher
    print("✅ chatbot import 성공")
    
    # 모든 라우터 import
    from app.api import review_admin
    print("✅ graduation, review_admin import 성공")
    
    from app.api.autocomplete import router as autocomplete_router
    print("✅ autocomplete import 성공")
    
    from app.api.calendar import router as calendar_router
    print("✅ calendar import 성공")
    
    from app.api.faq import router as faq_router
    print("✅ faq import 성공")

except Exception as e:
    print("=" * 50)
    print("❌ IMPORT 실패!")
    print("=" * 50)
    traceback.print_exc()
    sys.exit(1)

# 앱 시작/종료 이벤트
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 1. 시작 시
    print("🚀 애플리케이션 시작")
    print(f"✔️ 환경: {settings.environment}")
    print(f"✔️ LLM 모델: {settings.model_name}")
    
    # 1-1. 30분마다 1시간 동안 활동 없는 세션을 삭제하는 백그라운드 스케줄러 함수
    async def cleanup_old_sessions():
        while True:
            await asyncio.sleep(1800)
            deleted = session_store.clear_old_sessions(hours=1) 
            if deleted > 0:
                print(f"🗑️ 오래된 세션 {deleted}개 정리됨")
    
    cleanup_task = asyncio.create_task(cleanup_old_sessions())
    
    # 2. 서버 동작 실행중 (여기서 서버가 돌아가는것)
    yield
    
    # 3. 종료 시
    cleanup_task.cancel()
    print("👋 애플리케이션 종료")


# [FastAPI 앱 생성]
# 서버 구동 시 uvicorn app.main:app --reload로 실행 
app = FastAPI(
    title="University Chatbot API",
    description="순천대학교 통합 챗봇 API (챗봇 + FAQ + 자동완성)",
    version="1.0.0",
    lifespan=lifespan # 이 함수가 실행되면서 서버가 실행된다
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
# 챗봇 라우터 (당신 것)
app.include_router(graduation.router)
app.include_router(review_admin.router)

# FAQ/자동완성 라우터 (다른 팀원 것)
app.include_router(autocomplete_router)
app.include_router(calendar_router)
app.include_router(faq_router)

# 식도락 라우터
app.include_router(restaurant.router)


@app.get("/", response_model=HealthCheck)
async def root():
    """헬스체크"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now()
    )


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """헬스체크"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now()
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 대화 엔드포인트"""
    try:
        print(f"\n{'='*50}")
        print(f"📬 새 요청 도착!")
        print(f"{'='*50}")
        
        # 세션 관리
        session_id = request.session_id
        
        print(f"  📨 받은 session_id: {session_id}")
        print(f"  📊 현재 저장된 세션 수: {len(session_store.sessions)}")
        print(f"  📋 저장된 세션 목록: {list(session_store.sessions.keys())}")
        
        if not session_id:
            session_id = session_store.create_session(None)
            print(f"  ✅ 새 세션 생성: {session_id}")
        else:
            session = session_store.get_session(session_id)
            if not session:
                session_id = session_store.create_session(None)
                print(f"  ✅ 세션 만료, 새로 생성: {session_id}")
            elif request.user_profile:
                session_store.update_profile(session_id, request.user_profile)
        
        # 세션에서 사용자 프로필 가져오기
        session = session_store.get_session(session_id)
        session_profile = session.get('user_profile') if session else None
        
        if session_profile:
            is_dummy = (
                session_profile.admission_year == 2020 and
                any(c.course_code.startswith('CSE') for c in session_profile.courses_taken)
            )
            
            if is_dummy:
                print(f"⚠️ 더미 프로필 감지, 무시: {session_profile.admission_year}학번")
                session_profile = None
        
        user_profile = request.user_profile if request.user_profile else session_profile
        
        session_store.add_message(session_id, {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now()
        })
        
        session_messages = session.get('history', []) if session else []
        
        history_for_llm = []
        for msg in session_messages[:-1]:
            history_for_llm.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        MAX_HISTORY = 2
        if len(history_for_llm) > MAX_HISTORY:
            history_for_llm = history_for_llm[-MAX_HISTORY:]
            print(f"  📊 히스토리 제한: {len(session_messages)-1}개 → {len(history_for_llm)}개")
        
        print(f"\n💬 대화 이력 ({len(history_for_llm)}개 메시지):")
        for msg in history_for_llm[-6:]:
            print(f"  {msg['role']}: {msg['content'][:50]}...")
        
        print(f"\n📨 요청 정보:")
        print(f"  session_id: {session_id}")
        print(f"  현재 메시지: {request.message}")
        print(f"  user_profile: {user_profile}")
        
        # 챗봇 호출
        agent_result = ChatRequest(
            message=request.message,
            session_id=session_id,
            user_profile=user_profile,
            history=history_for_llm
        )
        
        response = chat_dispatcher(agent_result)
        
        if response.user_profile:
            session_store.update_profile(session_id, response.user_profile)
            print(f"  ✅ 세션에 프로필 저장: {response.user_profile.admission_year}학번")
        
        # 세션에 메시지 저장
        session_store.add_message(session_id, {
            "role": "assistant",
            "content": response.message,
            "timestamp": datetime.now()
        })

        return response
    
    except Exception as e:
        print(f"❌ 챗봇 오류: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"챗봇 처리 중 오류가 발생했습니다: {str(e)}"
        )


@app.post("/session/create")
async def create_session(user_profile: UserProfile = None):
    """새 세션 생성"""
    session_id = session_store.create_session(user_profile)
    return {"session_id": session_id}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """세션 정보 조회"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    return {
        "session_id": session_id,
        "user_profile": session.get('user_profile'),
        "history_count": len(session.get('history', [])),
        "created_at": session.get('created_at'),
        "last_accessed": session.get('last_accessed')
    }


@app.put("/session/{session_id}/profile")
async def update_profile(session_id: str, user_profile: UserProfile):
    """세션의 사용자 프로필 업데이트"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    session_store.update_profile(session_id, user_profile)
    return {"message": "프로필이 업데이트되었습니다"}


@app.delete("/sessions/cleanup")
async def cleanup_sessions(hours: int = 24):
    """오래된 세션 정리"""
    deleted = session_store.clear_old_sessions(hours)
    return {"deleted_sessions": deleted}


# 개발용 엔드포인트
if settings.debug:
    @app.get("/debug/sessions")
    async def debug_sessions():
        """모든 세션 조회 (디버그용)"""
        return {
            "total_sessions": len(session_store.sessions),
            "sessions": {
                sid: {
                    "has_profile": data.get('user_profile') is not None,
                    "message_count": len(data.get('history', [])),
                    "created_at": data.get('created_at'),
                }
                for sid, data in session_store.sessions.items()
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
