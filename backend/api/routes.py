# backend/api/routes.py
"""A2A 相亲 REST 与 WebSocket 路由。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.dating.models import AgentRole, DatingProfile, DatingSessionState
from backend.dating.engine import ConversationEngine, create_session
from backend.dating.infra.llm_client import ClaudeLLMClient, MockLLMClient
from backend.dating.adapters import secondme_to_dating_profile
from backend.api.events import get_event_pusher
from backend.auth.session_store import get_session as get_auth_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dating"])

# 全局存储（单进程）；生产可换 Redis/DB
sessions: dict[str, Any] = {}
engine: Optional[ConversationEngine] = None


def _get_engine() -> ConversationEngine:
    global engine
    if engine is None:
        try:
            llm = ClaudeLLMClient()
            if llm.api_key:
                client = llm
            else:
                client = MockLLMClient()
        except Exception as e:
            logger.warning("LLM init fallback to mock: %s", e)
            client = MockLLMClient()
        pusher = get_event_pusher()
        engine = ConversationEngine(
            llm_client=client,
            max_rounds=6,
            on_round_start=lambda s, goal: asyncio.create_task(
                pusher.push(s.session_id, {"type": "round_start", "round": s.current_round, "goal": goal})
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


class CreateSessionRequest(BaseModel):
    male: Optional[ProfileInput] = None
    female: Optional[ProfileInput] = None
    male_parent: Optional[ProfileInput] = None
    female_parent: Optional[ProfileInput] = None
    max_rounds: int = 6
    # 若已用 SecondMe 登录，可传对应 auth session_id，用其档案作为男方/女方
    secondme_male_session_id: Optional[str] = None
    secondme_female_session_id: Optional[str] = None


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
    if body.secondme_female_session_id:
        auth_sess = get_auth_session(body.secondme_female_session_id)
        if auth_sess and auth_sess.get("user_info"):
            profiles[AgentRole.FEMALE] = secondme_to_dating_profile(
                auth_sess["user_info"], AgentRole.FEMALE
            )
    # 表单档案（未用 SecondMe 或补充）
    if body.male:
        profiles[AgentRole.MALE] = _profile_from_input(AgentRole.MALE, body.male)
    if body.female:
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


@router.post("/dating/sessions/{session_id}/start", response_model=dict)
async def start_conversation(session_id: str) -> dict:
    """开始或继续畅聊（后台异步跑完多轮，事件通过 SSE/WS 推送）。"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    session = sessions[session_id]
    if session.state == DatingSessionState.COMPLETED:
        return {"session_id": session_id, "state": session.state.value, "message": "already completed"}
    eng = _get_engine()
    asyncio.create_task(eng.run_session(session))
    return {"session_id": session_id, "state": session.state.value, "message": "started"}


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
                    if event.get("type") == "summary":
                        pusher.unsubscribe(session_id, callback)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
        finally:
            pusher.unsubscribe(session_id, callback)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
