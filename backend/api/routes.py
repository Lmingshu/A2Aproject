# backend/api/routes.py
"""A2A 相亲 REST 与 WebSocket 路由。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.dating.models import AgentRole, DatingProfile, DatingSessionState
from backend.dating.engine import ConversationEngine, create_session
from backend.dating.infra.llm_client import ClaudeLLMClient, KimiLLMClient, MockLLMClient
from backend.dating.adapters import secondme_to_dating_profile
from backend.api.events import get_event_pusher
from backend.auth.session_store import get_session as get_auth_session, set_session_gender, get_session_gender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dating"])

# 全局存储（单进程）；生产可换 Redis/DB
sessions: dict[str, Any] = {}
engine: Optional[ConversationEngine] = None


def _get_engine() -> ConversationEngine:
    global engine
    if engine is None:
        client = None
        # 优先级：Kimi > Claude > Mock
        try:
            kimi = KimiLLMClient()
            if kimi.api_key:
                # 验证 API Key 格式
                if not kimi.api_key.startswith("sk-"):
                    logger.warning("Kimi API Key 格式可能不正确（应以 'sk-' 开头）")
                client = kimi
                logger.info("✅ 使用 Kimi (Moonshot AI) 作为 LLM 引擎")
            else:
                logger.warning("⚠️  Kimi API Key 未配置，检查环境变量 MOONSHOT_API_KEY")
        except Exception as e:
            logger.warning("Kimi init failed: %s", e)
        if not client:
            try:
                claude = ClaudeLLMClient()
                if claude.api_key:
                    client = claude
                    logger.info("使用 Claude 作为 LLM 引擎")
            except Exception as e:
                logger.warning("Claude init failed: %s", e)
        if not client:
            client = MockLLMClient()
            logger.warning("未配置 API Key，使用 Mock 回复")
        pusher = get_event_pusher()
        engine = ConversationEngine(
            llm_client=client,
            max_rounds=6,
            on_round_start=lambda s, goal: asyncio.create_task(
                pusher.push(s.session_id, {"type": "round_start", "round": s.current_round, "max_rounds": s.max_rounds, "goal": goal})
            ),
            on_message=lambda s, m: asyncio.create_task(
                pusher.push(s.session_id, {
                    "type": "message",
                    "message_id": m.message_id,
                    "role": m.role.value,
                    "display_name": m.display_name,
                    "content": m.content,
                    "round_index": m.round_index,
                })
            ),
            on_summary=lambda s, text: asyncio.create_task(
                pusher.push(s.session_id, {"type": "summary", "summary_text": text})
            ),
        )
    return engine


# -------- Pydantic 请求/响应 --------
class ProfileInput(BaseModel):
    display_name: str = Field("", description="称呼，如 小明、小红的妈妈")
    age: Optional[int] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
    hobbies: str = ""
    family_view: str = ""
    expectation: str = ""
    extra: str = ""
    avatar_url: str = ""  # 新增头像支持

class CreateSessionRequest(BaseModel):
    male: Optional[ProfileInput] = None
    female: Optional[ProfileInput] = None
    male_parent: Optional[ProfileInput] = None
    female_parent: Optional[ProfileInput] = None
    max_rounds: int = 6
    secondme_male_session_id: Optional[str] = None
    secondme_female_session_id: Optional[str] = None
    # 新增：指定对手 ID (来自大厅)
    target_user_id: Optional[str] = None
    my_user_id: Optional[str] = None  # 当前用户 ID (用于加入大厅)
    user_gender: Optional[str] = None  # 用户选择的性别 (male/female)

# ... (保留 create_dating_session 但需修改逻辑) ...

from backend.dating.lobby import get_lobby_users, add_user_to_lobby, get_user_from_lobby, get_npc_meta, init_lobby, random_match

# 初始化大厅
init_lobby()

@router.get("/dating/lobby")
async def get_lobby():
    """获取大厅用户列表"""
    return {"users": get_lobby_users()}


@router.post("/dating/lobby/update-gender")
async def update_lobby_gender(request: Request) -> dict:
    """用户在档案页选择性别后，更新大厅中自己的角色。"""
    data = await request.json()
    session_id = data.get("session_id") or request.cookies.get("a2a_session")
    gender = data.get("gender", "male")

    if not session_id:
        return {"ok": False, "error": "未登录"}

    auth_sess = get_auth_session(session_id)
    if not auth_sess or not auth_sess.get("user_info"):
        return {"ok": False, "error": "未找到用户信息"}

    user_info = auth_sess["user_info"]
    new_role = AgentRole.FEMALE if gender == "female" else AgentRole.MALE
    user_id = f"user_{user_info.get('userId', session_id)}"

    # 保存性别到 session
    set_session_gender(session_id, gender)

    # 重新构建 profile 并更新大厅
    new_profile = secondme_to_dating_profile(user_info, new_role)
    add_user_to_lobby(user_id, new_profile)
    logger.info("用户 %s 更新性别为 %s", user_info.get("name"), gender)
    return {"ok": True, "user_id": user_id, "gender": gender}


@router.post("/dating/auto-match", response_model=dict)
async def auto_match(body: CreateSessionRequest) -> dict:
    """全自动匹配：根据用户性别随机选一个异性 NPC，自动创建会话并开始对话。"""
    profiles = {}

    # 1. 确定用户自己的档案（支持男女双方）
    my_profile = None
    my_role = None
    
    # 优先使用 SecondMe 登录档案
    if body.secondme_male_session_id:
        auth_sess = get_auth_session(body.secondme_male_session_id)
        if auth_sess and auth_sess.get("user_info"):
            my_profile = secondme_to_dating_profile(auth_sess["user_info"], AgentRole.MALE)
            profiles[AgentRole.MALE] = my_profile
            my_role = AgentRole.MALE
            # 如果用户在前端输入了相亲要求，优先使用用户输入的
            if body.male and body.male.expectation:
                my_profile.expectation = body.male.expectation
    elif body.secondme_female_session_id:
        auth_sess = get_auth_session(body.secondme_female_session_id)
        if auth_sess and auth_sess.get("user_info"):
            my_profile = secondme_to_dating_profile(auth_sess["user_info"], AgentRole.FEMALE)
            profiles[AgentRole.FEMALE] = my_profile
            my_role = AgentRole.FEMALE
            # 如果用户在前端输入了相亲要求，优先使用用户输入的
            if body.female and body.female.expectation:
                my_profile.expectation = body.female.expectation
    
    # 如果没有 SecondMe 登录，使用表单数据
    if not my_profile:
        if body.male and body.male.display_name and body.male.display_name != '我':
            my_profile = _profile_from_input(AgentRole.MALE, body.male)
            profiles[AgentRole.MALE] = my_profile
            my_role = AgentRole.MALE
        elif body.female and body.female.display_name and body.female.display_name != '女方':
            my_profile = _profile_from_input(AgentRole.FEMALE, body.female)
            profiles[AgentRole.FEMALE] = my_profile
            my_role = AgentRole.FEMALE
    
    # 如果仍然无法确定，使用用户选择的性别或默认 male
    if not my_role:
        my_role = AgentRole.FEMALE if body.user_gender == "female" else AgentRole.MALE
        if not my_profile:
            input_data = body.female if my_role == AgentRole.FEMALE else body.male
            my_profile = _profile_from_input(my_role, input_data) if input_data else DatingProfile(role=my_role, display_name="我")
            profiles[my_role] = my_profile

    # 2. 随机选一个异性 NPC
    target_role = AgentRole.FEMALE if my_role == AgentRole.MALE else AgentRole.MALE
    match_result = random_match(prefer_role=target_role)
    if not match_result:
        raise HTTPException(status_code=404, detail="大厅暂无合适的匹配对象")

    npc_id, npc_profile = match_result
    profiles[target_role] = npc_profile

    # 3. 自动生成对应家长 NPC
    npc_meta = get_npc_meta(npc_id) or {}
    parent_role = AgentRole.FEMALE_PARENT if target_role == AgentRole.FEMALE else AgentRole.MALE_PARENT
    my_parent_role = AgentRole.MALE_PARENT if my_role == AgentRole.MALE else AgentRole.FEMALE_PARENT

    profiles[parent_role] = DatingProfile(
        role=parent_role,
        display_name=npc_meta.get("parent_name", f"{npc_profile.display_name}的家长"),
        occupation="",
        hobbies="",
        family_view=npc_profile.family_view,
        extra=npc_meta.get("parent_style", ""),
    )
    if my_parent_role not in profiles:
        # 根据用户性别选择正确的家长输入
        my_parent_input = body.male_parent if my_role == AgentRole.MALE else body.female_parent
        if my_parent_input:
            profiles[my_parent_role] = _profile_from_input(my_parent_role, my_parent_input)
        else:
            # 自动生成默认家长角色
            profiles[my_parent_role] = DatingProfile(
                role=my_parent_role,
                display_name="我的家长",
            )

    session = create_session(profiles, max_rounds=body.max_rounds)
    sessions[session.session_id] = session

    # 自动开始对话（通过 _running_sessions 防重复）
    eng = _get_engine()

    async def run_with_cleanup():
        try:
            _running_sessions.add(session.session_id)
            # 延迟 2 秒再开始对话，给前端 SSE 连接建立留出时间
            await asyncio.sleep(2.0)
            await eng.run_session(session)
        finally:
            _running_sessions.discard(session.session_id)

    asyncio.create_task(run_with_cleanup())

    return {
        "session_id": session.session_id,
        "state": session.state.value,
        "matched_npc": {
            "id": npc_id,
            "display_name": npc_profile.display_name,
            "age": npc_profile.age,
            "occupation": npc_profile.occupation,
            "hobbies": npc_profile.hobbies,
            "avatar_url": npc_profile.avatar_url,
            "extra": npc_profile.extra,
        },
        "message": "auto_started",
    }


def _profile_from_input(role: AgentRole, p: Optional[ProfileInput]) -> DatingProfile:
    if p is None:
        return DatingProfile(role=role, display_name={"male": "男方", "female": "女方", "male_parent": "男方家长", "female_parent": "女方家长"}[role.value])
    return DatingProfile(
        role=role,
        display_name=(p.display_name or {"male": "男方", "female": "女方", "male_parent": "男方家长", "female_parent": "女方家长"}[role.value]),
        age=p.age,
        occupation=p.occupation,
        education=p.education,
        location=p.location,
        hobbies=p.hobbies or "",
        family_view=p.family_view or "",
        expectation=p.expectation or "",
        extra=p.extra or "",
        avatar_url=p.avatar_url or "", # 传递头像
    )


@router.post("/dating/sessions", response_model=dict)
async def create_dating_session(body: CreateSessionRequest) -> dict:
    """创建相亲会话并返回 session_id。支持 SecondMe 登录档案作为男方/女方。"""
    profiles = {}
    # SecondMe 登录档案优先
    if body.secondme_male_session_id:
        auth_sess = get_auth_session(body.secondme_male_session_id)
        if auth_sess and auth_sess.get("user_info"):
            profiles[AgentRole.MALE] = secondme_to_dating_profile(
                auth_sess["user_info"], AgentRole.MALE
            )
            # 如果用户在前端输入了相亲要求，优先使用用户输入的
            if body.male and body.male.expectation:
                profiles[AgentRole.MALE].expectation = body.male.expectation
    if body.secondme_female_session_id:
        auth_sess = get_auth_session(body.secondme_female_session_id)
        if auth_sess and auth_sess.get("user_info"):
            profiles[AgentRole.FEMALE] = secondme_to_dating_profile(
                auth_sess["user_info"], AgentRole.FEMALE
            )
            # 如果用户在前端输入了相亲要求，优先使用用户输入的
            if body.female and body.female.expectation:
                profiles[AgentRole.FEMALE].expectation = body.female.expectation
    # 表单档案（未用 SecondMe 或补充）
    if body.male:
        if AgentRole.MALE in profiles:
            # SecondMe 档案已有，只选择性更新 expectation（不覆盖整个档案）
            if body.male.expectation:
                profiles[AgentRole.MALE].expectation = body.male.expectation
        else:
            profiles[AgentRole.MALE] = _profile_from_input(AgentRole.MALE, body.male)
    if body.female:
        if AgentRole.FEMALE in profiles:
            # SecondMe 档案已有，只选择性更新 expectation（不覆盖整个档案）
            if body.female.expectation:
                profiles[AgentRole.FEMALE].expectation = body.female.expectation
        else:
            profiles[AgentRole.FEMALE] = _profile_from_input(AgentRole.FEMALE, body.female)
    if body.male_parent:
        profiles[AgentRole.MALE_PARENT] = _profile_from_input(AgentRole.MALE_PARENT, body.male_parent)
    if body.female_parent:
        profiles[AgentRole.FEMALE_PARENT] = _profile_from_input(AgentRole.FEMALE_PARENT, body.female_parent)
    session = create_session(profiles, max_rounds=body.max_rounds)
    sessions[session.session_id] = session
    return {"session_id": session.session_id, "state": session.state.value}


@router.get("/dating/sessions/{session_id}", response_model=dict)
async def get_session(session_id: str) -> dict:
    """获取会话详情（含消息列表与总结）。"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    s = sessions[session_id]
    return {
        "session_id": s.session_id,
        "state": s.state.value,
        "current_round": s.current_round,
        "max_rounds": s.max_rounds,
        "summary": s.summary,
        "messages": [
            {
                "message_id": m.message_id,
                "role": m.role.value,
                "display_name": m.display_name,
                "content": m.content,
                "round_index": m.round_index,
            }
            for m in s.messages
        ],
        "profiles": {
            r.value: {"display_name": p.display_name, "age": p.age, "occupation": p.occupation}
            for r, p in s.profiles.items()
        },
    }


# 跟踪正在运行的会话任务，避免重复启动
_running_sessions: set[str] = set()


@router.post("/dating/sessions/{session_id}/start", response_model=dict)
async def start_conversation(session_id: str) -> dict:
    """开始或继续畅聊（后台异步异步跑完多轮，事件通过 SSE/WS 推送）。"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    session = sessions[session_id]
    
    if session.state == DatingSessionState.COMPLETED:
        return {"session_id": session_id, "state": session.state.value, "message": "already completed"}
    
    # 检查是否已经在运行
    if session_id in _running_sessions:
        logger.info("会话 %s 已在运行中，跳过重复启动", session_id)
        return {"session_id": session_id, "state": session.state.value, "message": "already running"}
    
    eng = _get_engine()
    
    async def run_with_cleanup():
        try:
            _running_sessions.add(session_id)
            await eng.run_session(session)
        finally:
            _running_sessions.discard(session_id)
    
    asyncio.create_task(run_with_cleanup())
    return {"session_id": session_id, "state": session.state.value, "message": "started"}


@router.get("/dating/debug/llm-status")
async def debug_llm_status() -> dict:
    """调试端点：检查 LLM 配置状态（不暴露完整 API Key）。"""
    status = {
        "kimi": {"configured": False, "key_length": 0, "key_prefix": ""},
        "claude": {"configured": False, "key_length": 0, "key_prefix": ""},
        "active": "unknown",
    }
    
    # 检查 Kimi
    try:
        kimi = KimiLLMClient()
        if kimi.api_key:
            status["kimi"]["configured"] = True
            status["kimi"]["key_length"] = len(kimi.api_key)
            status["kimi"]["key_prefix"] = kimi.api_key[:8] + "..." if len(kimi.api_key) > 8 else "***"
            status["kimi"]["key_format_valid"] = kimi.api_key.startswith("sk-")
            status["active"] = "kimi"
    except Exception as e:
        status["kimi"]["error"] = str(e)
    
    # 检查 Claude
    try:
        claude = ClaudeLLMClient()
        if claude.api_key:
            status["claude"]["configured"] = True
            status["claude"]["key_length"] = len(claude.api_key)
            status["claude"]["key_prefix"] = claude.api_key[:8] + "..." if len(claude.api_key) > 8 else "***"
            if status["active"] == "unknown":
                status["active"] = "claude"
    except Exception as e:
        status["claude"]["error"] = str(e)
    
    if status["active"] == "unknown":
        status["active"] = "mock"
    
    return status


@router.get("/dating/sessions/{session_id}/events")
async def stream_events(session_id: str) -> StreamingResponse:
    """SSE 流：推送 round_start / message / summary 事件。"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    pusher = get_event_pusher()
    queue: asyncio.Queue = asyncio.Queue()

    def put(q: asyncio.Queue):
        def cb(payload: dict):
            q.put_nowait(payload)
        return cb

    callback = put(queue)
    pusher.subscribe(session_id, callback)

    async def gen():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    # summary 事件后结束 SSE 连接，避免资源泄漏
                    if event.get("type") == "summary":
                        return
                except asyncio.TimeoutError:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
        finally:
            pusher.unsubscribe(session_id, callback)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
