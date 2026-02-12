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
    secondme_data 来自 fetch_user_info()，可含 name, bio, avatarUrl, email, shades, softmemory 等。
    """
    name = (display_name_override or secondme_data.get("name") or "").strip() or "我"
    bio = secondme_data.get("bio") or ""
    self_intro = secondme_data.get("selfIntroduction") or ""
    
    # 处理兴趣标签（shades）
    shades = secondme_data.get("shades") or []
    _parts = []
    for s in shades[:10]:
        if isinstance(s, dict):
            # 优先使用公开标签名称
            shade_name = s.get("shadeNamePublic") or s.get("shadeName") or ""
            if shade_name:
                _parts.append(shade_name)
    hobbies = ", ".join(p for p in _parts if p)
    
    # 如果没有兴趣标签，使用 bio 或 selfIntroduction
    if not hobbies:
        if self_intro:
            hobbies = self_intro[:100]  # 限制长度
        elif bio:
            hobbies = bio
    
    # 处理软记忆（softmemory）- 提取关键信息
    softmemory = secondme_data.get("softmemory") or []
    extra_info_parts = []
    if softmemory:
        # 提取前10条软记忆的关键信息
        for mem in softmemory[:10]:
            fact_object = mem.get("factObject", "")
            fact_content = mem.get("factContent", "")
            if fact_object and fact_content:
                extra_info_parts.append(f"{fact_object}: {fact_content}")
    
    # 组合 extra 字段：selfIntroduction + softmemory 摘要
    extra_parts = []
    if self_intro and len(self_intro) > 100:
        extra_parts.append(self_intro[:200] + "...")
    if extra_info_parts:
        extra_parts.extend(extra_info_parts[:5])  # 最多5条软记忆
    extra = "；".join(extra_parts) if extra_parts else ""
    
    # 从软记忆中提取可能的职业、期望等信息
    occupation = secondme_data.get("occupation")
    if not occupation and softmemory:
        for mem in softmemory:
            fact_object = mem.get("factObject", "")
            if "职业" in fact_object or "工作" in fact_object:
                occupation = mem.get("factContent", "")
                break

    return DatingProfile(
        role=role,
        display_name=name,
        age=None,
        occupation=occupation,
        education=secondme_data.get("education") or None,
        location=secondme_data.get("location") or None,
        hobbies=hobbies,
        family_view=secondme_data.get("family_view") or "",
        expectation=secondme_data.get("expectation") or "",
        extra=extra,
        avatar_url=secondme_data.get("avatarUrl") or secondme_data.get("avatar") or "",
        metadata={
            "source": "secondme",
            "userId": secondme_data.get("userId"),
            "email": secondme_data.get("email"),
            "route": secondme_data.get("route"),
            "softmemory": softmemory,  # 保存完整软记忆供 AI 使用
            "selfIntroduction": self_intro,
            "shades": shades,  # 保存完整标签信息
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
            # 统一字段名优先级：与 secondme_to_dating_profile 保持一致
            shade_name = (
                s.get("shadeNamePublic")
                or s.get("shadeName")
                or s.get("name")
                or s.get("title")
                or ""
            )
            if shade_name:
                _parts.append(str(shade_name).strip())
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
        "avatar_url": secondme_data.get("avatarUrl") or secondme_data.get("avatar") or "",
    }
