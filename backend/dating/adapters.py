# backend/dating/adapters.py
"""将 SecondMe 用户信息映射为相亲档案（DatingProfile / ProfileInput）。"""

from __future__ import annotations

from typing import Any, Optional

from .models import AgentRole, DatingProfile

# SecondMe user/info 常见字段：name, bio, avatar/avatarUrl, email, route 等
# user/shades: result.data.shades -> 兴趣标签列表


def secondme_to_dating_profile(
    secondme_data: dict[str, Any],
    role: AgentRole,
    display_name_override: Optional[str] = None,
) -> DatingProfile:
    """
    将 SecondMe API 返回的用户信息转为 DatingProfile。
    secondme_data 来自 fetch_user_info()，可含 name, bio, avatarUrl, email, shades 等。
    """
    name = (display_name_override or secondme_data.get("name") or "").strip() or "我"
    bio = secondme_data.get("bio") or ""
    shades = secondme_data.get("shades") or []
    _parts = []
    for s in shades[:10]:
        if isinstance(s, dict):
            _parts.append(str(s.get("name") or s.get("title") or "").strip() or str(s))
        else:
            _parts.append(str(s))
    hobbies = ", ".join(p for p in _parts if p)
    if bio and not hobbies:
        hobbies = bio
    elif bio and hobbies:
        hobbies = f"{bio}；兴趣：{hobbies}"

    return DatingProfile(
        role=role,
        display_name=name,
        age=None,
        occupation=secondme_data.get("occupation") or None,
        education=secondme_data.get("education") or None,
        location=secondme_data.get("location") or None,
        hobbies=hobbies,
        family_view=secondme_data.get("family_view") or "",
        expectation=secondme_data.get("expectation") or "",
        extra=secondme_data.get("extra") or "",
        metadata={
            "source": "secondme",
            "avatar_url": secondme_data.get("avatarUrl") or secondme_data.get("avatar"),
            "email": secondme_data.get("email"),
        },
    )


def secondme_to_profile_input(secondme_data: dict[str, Any]) -> dict[str, Any]:
    """
    将 SecondMe 用户信息转为前端/API 用的 ProfileInput 风格 dict。
    用于 GET /api/auth/me 返回给前端预填表单。
    """
    name = (secondme_data.get("name") or "").strip() or "我"
    bio = secondme_data.get("bio") or ""
    shades = secondme_data.get("shades") or []
    _parts = []
    for s in shades[:10]:
        if isinstance(s, dict):
            _parts.append(str(s.get("name") or s.get("title") or "").strip() or str(s))
        else:
            _parts.append(str(s))
    hobbies = ", ".join(p for p in _parts if p)
    if bio and not hobbies:
        hobbies = bio
    elif bio and hobbies:
        hobbies = f"{bio}；兴趣：{hobbies}"

    return {
        "display_name": name,
        "age": secondme_data.get("age"),
        "occupation": secondme_data.get("occupation"),
        "education": secondme_data.get("education"),
        "location": secondme_data.get("location"),
        "hobbies": hobbies,
        "family_view": secondme_data.get("family_view") or "",
        "expectation": secondme_data.get("expectation") or "",
        "extra": secondme_data.get("extra") or "",
        "source": "secondme",
        "avatar_url": secondme_data.get("avatarUrl") or secondme_data.get("avatar"),
    }
