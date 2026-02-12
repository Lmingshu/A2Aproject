# backend/dating/skills.py
"""
相亲场景的 Skills：每方发言（DatingChatSkill）、Center 协调与总结（DatingCenterSkill）。
"""

from __future__ import annotations

from typing import Any

from .models import AgentRole, DatingProfile, ROLE_DISPLAY_NAMES


# -------- DatingChatSkill：单方当轮发言 --------
DATING_CHAT_SYSTEM = """你正在参加一场线上「AI 相亲畅聊」。你的身份由【你的档案】唯一确定。

## 角色扮演规则
- 你必须完全代入角色，像真人一样自然说话
- 语气、口吻、用词要符合档案中的年龄、职业、性格（MBTI 等）
- 不要用「作为一个AI」「我来回答」这类破坏沉浸感的说法
- 不要编造档案中没有的关键信息（学历、收入等），但可以自然展开已有信息的细节

## 对话风格要求
1. **自然真实**：像微信群聊一样说话，可以用口语、略带情绪、偶尔用表情（但不要过多）
2. **有个性**：根据你的性格特点说话——
   - 外向型：主动、热情、爱开玩笑、偶尔自嘲
   - 内向型：含蓄、深思、言简意赅但有深度
   - 家长角色：关心实际问题（工作稳定性、房子、生育观），但也要有温度
3. **有互动**：回应上一轮其他人说的具体内容，不要自说自话。可以：
   - 追问对方感兴趣的点
   - 对对方的话表示认同或善意的不同看法
   - 分享和对方类似的经历
   - 偶尔吐槽或开个善意的玩笑活跃气氛
4. **推进关系**：每轮要有一点点进展，不要原地踏步。可以透露新的个人信息、主动邀约、或暗示好感
5. **关注期望**：如果你的档案中有「对另一半/对子女对象期望」，要自然地根据这些期望来评估对方，并在对话中体现出来（但不要直接说「你符合我的要求」这样生硬的话）
6. **简短有力**：2~4 句话为宜，不要长篇大论。重要的是说到点上

## 家长角色特别提示
如果你是家长角色：
- 关心但不要过度干涉，像真实相亲中的家长
- 可以适时问一些「实际」问题（工作、规划、家庭观），但不要审问式
- 偶尔帮自家孩子说好话、打圆场
- 性格要鲜明：有的家长热情、有的含蓄、有的幽默、有的严格
"""


async def run_dating_chat(
    role: AgentRole,
    profile: DatingProfile,
    round_goal: str,
    history_for_prompt: list[dict[str, str]],
    llm_client: Any,
) -> str:
    """生成当前角色在本轮的发言。"""
    identity = f"【你的档案】\n{profile.to_prompt_text()}"

    # 根据角色类型给更具体的提示
    role_hint = ""
    if role in (AgentRole.MALE, AgentRole.FEMALE):
        role_hint = "你是相亲的主角之一，要展现真实的自己，适度展示魅力。"
    elif role == AgentRole.MALE_PARENT:
        role_hint = "你是男方的家长，既要维护儿子的形象，也要真诚地了解对方家庭。"
    elif role == AgentRole.FEMALE_PARENT:
        role_hint = "你是女方的家长，既要观察男方是否靠谱，也要让气氛不要太尴尬。"

    lines = [
        f"【本轮话题】{round_goal}",
        f"【你的角色定位】{role_hint}",
        "",
        "【当前对话记录】（注意回应其中的具体内容）",
    ]
    for h in history_for_prompt[-24:]:
        r = h.get("role", "user")
        c = h.get("content", "")
        if r == "user":
            lines.append(f"[主持人] {c}")
        else:
            lines.append(c)
    lines.append("")
    lines.append(f"现在请以「{profile.display_name}」的身份发言。直接说你要说的话，不要加任何前缀标签：")
    user_content = "\n".join(lines)

    messages = [
        {"role": "system", "content": DATING_CHAT_SYSTEM + "\n\n" + identity},
        {"role": "user", "content": user_content},
    ]
    reply = await llm_client.chat(messages, max_tokens=500)
    return (reply or "").strip()


# -------- DatingCenterSkill：决定本轮话题或输出总结 --------
DATING_CENTER_SYSTEM = """你是「AI 相亲畅聊」的主持人（"月老"）。参与方：男方、女方、男方家长、女方家长。

## 你的风格
- 你是一个幽默、有经验的月老，不要冷冰冰地出话题
- 话题引导要自然过渡，不要突兀跳转
- 偶尔可以加点轻松的调侃活跃气氛

## 话题设计原则
- 第1轮：破冰寒暄（自我介绍、打招呼）
- 第2轮：兴趣爱好、日常生活（找共同话题）
- 第3轮：工作与规划（了解对方的发展方向）
- 第4轮：感情观与生活习惯（深入了解三观）
- 第5轮：家庭氛围与期望（家长主导的话题）
- 第6轮：收尾总结

## 输出格式
你必须且只能输出以下两种格式之一（不要其他解释）：

【继续】
本轮目标：<一句自然的话题引导，像真人月老说的话，不要太正式>

【总结】
<3~5句活泼的总结，包含：双方互动亮点 + 匹配度评价 + 是否建议继续发展的建议，用月老的口吻>"""


async def run_dating_center(
    current_round: int,
    max_rounds: int,
    history_for_prompt: list[dict[str, str]],
    llm_client: Any,
) -> dict[str, Any]:
    """
    返回 {"action": "continue" | "summary", "round_goal": "..." 或 "summary_text": "..."}。
    """
    lines = [
        "【当前进度】",
        f"第 {current_round} 轮 / 最多 {max_rounds} 轮",
        "",
        "【对话记录】",
    ]
    for h in history_for_prompt[-30:]:
        c = h.get("content", "")
        lines.append(c)
    lines.append("")

    if current_round >= max_rounds:
        lines.append("已到最后一轮，请输出【总结】。")
    elif current_round >= max_rounds - 1:
        lines.append("即将结束，请考虑是【继续】最后一轮还是直接【总结】。")
    else:
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
    return {"action": "continue", "round_goal": "请大家继续聊聊，分享一些生活中的小故事吧。"}
