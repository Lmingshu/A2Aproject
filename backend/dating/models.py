# backend/dating/models.py
"""
A2A 相亲核心数据模型。
参与方固定：男方、女方、男方家长、女方家长。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def generate_id(prefix: str = "") -> str:
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


class AgentRole(str, Enum):
    """相亲中的 4 方角色。"""
    MALE = "male"              # 男方
    FEMALE = "female"          # 女方
    MALE_PARENT = "male_parent"    # 男方家长
    FEMALE_PARENT = "female_parent"  # 女方家长


ROLE_DISPLAY_NAMES = {
    AgentRole.MALE: "男方",
    AgentRole.FEMALE: "女方",
    AgentRole.MALE_PARENT: "男方家长",
    AgentRole.FEMALE_PARENT: "女方家长",
}


@dataclass
class DatingProfile:
    """单方档案（男方/女方/男方家长/女方家长）。"""
    role: AgentRole
    display_name: str
    avatar_url: str = ""  # 新增头像
    age: Optional[int] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
    hobbies: str = ""
    family_view: str = ""       # 家庭观、婚恋观
    expectation: str = ""      # 对另一半/对子女对象的期望
    extra: str = ""            # 自由补充
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """用于 LLM 的角色设定文本。"""
        parts = [
            f"角色：{ROLE_DISPLAY_NAMES.get(self.role, self.role.value)}",
            f"称呼：{self.display_name}",
        ]
        if self.age is not None:
            parts.append(f"年龄：{self.age}")
        if self.occupation:
            parts.append(f"职业：{self.occupation}")
        if self.education:
            parts.append(f"学历：{self.education}")
        if self.location:
            parts.append(f"所在地：{self.location}")
        if self.hobbies:
            parts.append(f"爱好：{self.hobbies}")
        if self.family_view:
            parts.append(f"家庭/婚恋观：{self.family_view}")
        if self.expectation:
            parts.append(f"对另一半/对子女对象期望：{self.expectation}")
        if self.extra:
            parts.append(f"其他：{self.extra}")
        return "\n".join(parts)


@dataclass
class DatingMessage:
    """单条对话消息。"""
    message_id: str
    role: AgentRole
    display_name: str
    content: str
    round_index: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class DatingSessionState(str, Enum):
    CREATED = "created"
    ICE_BREAKING = "ice_breaking"   # 破冰
    CHATTING = "chatting"           # 了解/深入
    SUMMARIZING = "summarizing"     # 总结中
    COMPLETED = "completed"


@dataclass
class DatingSession:
    """一次相亲畅聊会话。"""
    session_id: str
    profiles: dict[AgentRole, DatingProfile]  # 4 方档案
    state: DatingSessionState = DatingSessionState.CREATED
    messages: list[DatingMessage] = field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 6
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_profile(self, role: AgentRole) -> Optional[DatingProfile]:
        return self.profiles.get(role)

    def add_message(self, role: AgentRole, display_name: str, content: str, round_index: int) -> DatingMessage:
        msg = DatingMessage(
            message_id=generate_id("msg"),
            role=role,
            display_name=display_name,
            content=content,
            round_index=round_index,
        )
        self.messages.append(msg)
        return msg
