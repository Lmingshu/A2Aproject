# backend/dating/skills.py
"""
相亲场景的 Skills：每方发言（DatingChatSkill）、Center 协调与总结（DatingCenterSkill）。
"""

from __future__ import annotations

from typing import Any

from .models import AgentRole, DatingProfile, ROLE_DISPLAY_NAMES


# -------- DatingChatSkill：单方当轮发言 --------
DATING_CHAT_SYSTEM = """你正在参加一场「相亲畅聊」的线上交流。你的身份由下面的【你的档案】唯一确定。
请严格以该身份发言：语气、用词、立场都要符合该角色（本人或家长），不要跳出角色。
要求：
1. 回复简洁自然，一两段即可，不要长篇大论。
2. 可以礼貌性问候、回应对方、或简短表达自己的看法。
3. 不要编造档案中没有的信息；若当前话题档案未涉及，可委婉说「这个我还没细想」或简单带过。
"""


async def run_dating_chat(
    role: AgentRole,
    profile: DatingProfile,
    round_goal: str,
    history_for_prompt: list[dict[str, str]],
    llm_client: Any,
) -> str:
    """
    生成当前角色在本轮的发言。
    history_for_prompt: [{"role":"user"|"assistant", "content": "..."}]，其中 user 可表示「主持人/话题」，assistant 表示某方发言（可带 [男方] 等前缀）。
    """
    identity = f"【你的档案】\n{profile.to_prompt_text()}"
    lines = [
        f"【本轮目标】{round_goal}",
        "",
        "【当前对话历史】",
    ]
    for h in history_for_prompt[-20:]:  # 最近 20 条
        r = h.get("role", "user")
        c = h.get("content", "")
        if r == "user":
            lines.append(f"主持人/话题: {c}")
        else:
            lines.append(c)
    lines.append("")
    lines.append(f"请以「{profile.display_name}」的身份，根据上述对话做一次简短发言（直接输出你要说的内容，不要加「男方说：」等前缀）：")
    user_content = "\n".join(lines)

    messages = [
        {"role": "system", "content": DATING_CHAT_SYSTEM + "\n\n" + identity},
        {"role": "user", "content": user_content},
    ]
    reply = await llm_client.chat(messages, max_tokens=400)
    return (reply or "").strip()


# -------- DatingCenterSkill：决定本轮话题或输出总结 --------
DATING_CENTER_SYSTEM = """你是「相亲畅聊」的主持人（Center）。参与方固定为：男方、女方、男方家长、女方家长。
你的职责：
1. 在每轮给出「本轮目标」：一句简短话题或引导语，让 4 方基于当前对话继续聊（例如：请大家简单介绍一下自己的工作和日常爱好）。
2. 当对话轮数足够（例如已 4～6 轮）或你认为可以收尾时，输出最终「总结」并结束。
你必须且只能输出以下两种格式之一（不要其他解释）：

【继续】
本轮目标：<一句简短话题或引导语>

【总结】
<一段 2～5 句的总结，包含：双方匹配度简述 + 是否建议见面/再聊/暂缓>"""


async def run_dating_center(
    current_round: int,
    max_rounds: int,
    history_for_prompt: list[dict[str, str]],
    llm_client: Any,
) -> dict[str, Any]:
    """
    返回 {"action": "continue" | "summary", "round_goal": "..." 或 "summary_text": "..."}。
    """
    lines = ["【当前轮次】", f"第 {current_round} 轮 / 最多 {max_rounds} 轮", "", "【对话历史】"]
    for h in history_for_prompt[-30:]:
        c = h.get("content", "")
        lines.append(c)
    lines.append("")
    lines.append("请根据上述对话，决定是【继续】还是【总结】，并严格按格式输出。")
    user_content = "\n".join(lines)

    messages = [
        {"role": "system", "content": DATING_CENTER_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    raw = await llm_client.chat(messages, max_tokens=600)
    raw = (raw or "").strip()

    if "【总结】" in raw:
        summary = raw.split("【总结】")[-1].strip()
        return {"action": "summary", "summary_text": summary}
    if "【继续】" in raw:
        goal = ""
        for line in raw.split("\n"):
            if "本轮目标" in line:
                goal = line.replace("本轮目标：", "").replace("本轮目标:", "").strip()
                break
        if not goal:
            goal = "请大家根据刚才的交流，再聊聊各自的想法或关心的问题。"
        return {"action": "continue", "round_goal": goal}
    # 默认继续
    return {"action": "continue", "round_goal": "请大家简单说说自己的看法或补充一下。"}
