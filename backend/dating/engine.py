# backend/dating/engine.py
"""
相亲畅聊对话引擎：固定 4 方、多轮发言、Center 协调与总结。
基于 Towow 的「轮次制 + Center 协调」思路，不做共振，只做多轮对话。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .models import (
    AgentRole,
    DatingMessage,
    DatingProfile,
    DatingSession,
    DatingSessionState,
    ROLE_DISPLAY_NAMES,
    generate_id,
)
from .skills import run_dating_chat, run_dating_center

logger = logging.getLogger(__name__)

ALL_ROLES = [AgentRole.MALE, AgentRole.FEMALE, AgentRole.MALE_PARENT, AgentRole.FEMALE_PARENT]


class ConversationEngine:
    """
    多轮对话引擎：每轮 Center 决定话题 → 4 个 Agent 并行发言 → 收集后进入下一轮或输出总结。
    """

    def __init__(
        self,
        llm_client: Any,
        max_rounds: int = 6,
        on_message: Optional[Callable[[DatingSession, DatingMessage], Any]] = None,
        on_round_start: Optional[Callable[[DatingSession, str], Any]] = None,
        on_summary: Optional[Callable[[DatingSession, str], Any]] = None,
    ):
        self.llm_client = llm_client
        self.max_rounds = max_rounds
        self.on_message = on_message
        self.on_round_start = on_round_start
        self.on_summary = on_summary

    def _history_for_prompt(self, session: DatingSession) -> list[dict[str, str]]:
        """把 session.messages 转成带角色前缀的 history，供 Skill 使用。"""
        out = []
        for m in session.messages:
            label = ROLE_DISPLAY_NAMES.get(m.role, m.role.value)
            out.append({"role": "assistant", "content": f"[{label} {m.display_name}] {m.content}"})
        return out

    async def run_session(self, session: DatingSession) -> DatingSession:
        """从当前状态跑完会话（可多轮直到 Center 输出总结或达到 max_rounds）。"""
        if session.state == DatingSessionState.COMPLETED:
            return session

        session.state = DatingSessionState.ICE_BREAKING
        session.current_round = 0
        round_goal = "请大家先打个招呼，简单介绍一下自己（可以说称呼、工作或爱好中的一两样）。"

        while session.current_round < self.max_rounds:
            session.current_round += 1
            if session.current_round > 1:
                session.state = DatingSessionState.CHATTING

            if self.on_round_start:
                try:
                    self.on_round_start(session, round_goal)
                except Exception as e:
                    logger.warning("on_round_start callback error: %s", e)

            # Center 先判断：第一轮用预设破冰，后续轮由 Center 决定
            if session.current_round > 1:
                history = self._history_for_prompt(session)
                center_out = await run_dating_center(
                    current_round=session.current_round,
                    max_rounds=self.max_rounds,
                    history_for_prompt=history,
                    llm_client=self.llm_client,
                )
                if center_out.get("action") == "summary":
                    session.state = DatingSessionState.SUMMARIZING
                    session.summary = center_out.get("summary_text", "")
                    session.state = DatingSessionState.COMPLETED
                    session.completed_at = datetime.now(timezone.utc)
                    if self.on_summary:
                        try:
                            self.on_summary(session, session.summary)
                        except Exception as e:
                            logger.warning("on_summary callback error: %s", e)
                    return session
                round_goal = center_out.get("round_goal", round_goal)

            history = self._history_for_prompt(session)
            # 并行生成 4 方发言
            async def reply_one(role: AgentRole) -> tuple[AgentRole, str]:
                profile = session.get_profile(role)
                if not profile:
                    return role, "(该方未填写档案)"
                text = await run_dating_chat(
                    role=role,
                    profile=profile,
                    round_goal=round_goal,
                    history_for_prompt=history,
                    llm_client=self.llm_client,
                )
                return role, text or "(无回复)"

            results = await asyncio.gather(
                *(reply_one(r) for r in ALL_ROLES),
                return_exceptions=True,
            )

            for i, r in enumerate(ALL_ROLES):
                if isinstance(results[i], Exception):
                    content = f"(发言生成异常: {results[i]})"
                else:
                    _, content = results[i]
                profile = session.get_profile(r)
                display_name = profile.display_name if profile else ROLE_DISPLAY_NAMES.get(r, r.value)
                msg = session.add_message(r, display_name, content, session.current_round)
                if self.on_message:
                    try:
                        self.on_message(session, msg)
                    except Exception as e:
                        logger.warning("on_message callback error: %s", e)
                # 每条消息间隔推送，模拟真人交流的思考时间（1.5-2秒间隔，加快节奏）
                # 真人对话中，每条消息之间通常有思考、组织语言的时间
                await asyncio.sleep(1.8)

        # 达到最大轮数仍未总结，由 Center 强制总结
        session.state = DatingSessionState.SUMMARIZING
        history = self._history_for_prompt(session)
        center_out = await run_dating_center(
            current_round=session.current_round,
            max_rounds=self.max_rounds,
            history_for_prompt=history,
            llm_client=self.llm_client,
        )
        session.summary = center_out.get("summary_text", "大家聊了不少，建议可以线下再约见，慢慢了解。")
        session.state = DatingSessionState.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        if self.on_summary:
            try:
                self.on_summary(session, session.summary)
            except Exception as e:
                logger.warning("on_summary callback error: %s", e)
        return session


def create_session(profiles: dict[AgentRole, DatingProfile], max_rounds: int = 6) -> DatingSession:
    """创建相亲会话，确保 4 方档案齐全（缺的用占位 Profile）。"""
    all_roles = set(ALL_ROLES)
    filled = set(profiles.keys())
    for r in all_roles - filled:
        profiles[r] = DatingProfile(role=r, display_name=ROLE_DISPLAY_NAMES.get(r, r.value))
    return DatingSession(
        session_id=generate_id("dating"),
        profiles=profiles,
        max_rounds=max_rounds,
    )
