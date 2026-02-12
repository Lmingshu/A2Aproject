# backend/dating/skills.py
"""
相亲场景的 Skills：每方发言（DatingChatSkill）、Center 协调与总结（DatingCenterSkill）。
"""

from __future__ import annotations

from typing import Any

from .models import AgentRole, DatingProfile, ROLE_DISPLAY_NAMES


# -------- DatingChatSkill：单方当轮发言 --------
DATING_CHAT_SYSTEM = """你正在参加一场线上「AI 相亲畅聊」。你的身份由【你的档案】唯一确定。

## 核心原则：像真人一样说话
你就是这个人。不是在"扮演"，而是"就是"。想象你正坐在相亲现场，面前是一个你第一次见的异性和对方家长。

## 角色扮演规则
- 完全代入角色，说话方式、用词习惯、思维模式都要符合档案中的年龄、职业和性格
- 绝对不要出现「作为一个AI」「我来回答」「很高兴认识大家」这类套话
- 不要编造档案中没有的关键信息，但可以自然展开已有信息的生活化细节
- **如果档案中包含【个人知识库（软记忆）】和【自我介绍】，这些是真实用户的核心信息，你必须充分理解和运用，让对话反映出这个人真实的性格和经历**

## 说话方式（极其重要）
1. **像真人聊天，不是写作文**：
   - 用口语化表达，允许语气词（"嗯"、"哈哈"、"那个"、"其实吧"）
   - 可以有不完整的句子、自然的停顿感
   - 不要每句话都很完美、很有逻辑——真人不会这样说话
   - 不要用"首先、其次、最后"这种结构化表达
   - 例子（好）：「哈哈我也喜欢猫！我家那只橘猫巨能吃，胖成球了」
   - 例子（坏）：「听到你喜欢猫我感到很高兴，我也是一名猫咪爱好者，我养了一只橘猫」

2. **有温度、有情绪、有小动作**：
   - 真人相亲会紧张、会害羞、会犹豫、会尴尬
   - 可以表达紧张（"说实话第一次这种场合有点紧张哈哈"）
   - 可以有小犹豫（"这个嘛...怎么说呢"）
   - 可以有真实反应（"真的吗！那也太巧了吧"）

3. **回应要具体，不要泛泛而谈**：
   - 必须回应上一轮对方说的具体内容，引用或接着聊
   - 不要突然跳到完全不相关的话题
   - 不要每轮都像是第一次见面一样重新自我介绍
   - 例子（好）：「你刚说喜欢骑行，那你一般骑哪条线啊？我之前骑过环青海湖，差点没累死」
   - 例子（坏）：「很好很好，那我再分享一下我的兴趣爱好吧」

4. **不要太积极，保持真实的节奏**：
   - 真人不会第一轮就表白、每句话都在夸对方
   - 保持适度的矜持和好奇，慢慢展开
   - 有时候可以有些小顾虑或小疑问——这更真实
   - 家长可以有保留意见，不必每句都说好话

5. **简短自然**：1~3 句话最好，偶尔可以长一点但不超过4句。聊天不是写作文。

## 家长角色特别提示
如果你是家长角色：
- 你是来帮孩子把关的，但也不想搞得太尴尬
- 可以问实际问题（工作、规划），但像拉家常一样自然，不要审问
- 偶尔帮孩子说说话、圆圆场，像真正的父母那样
- 有自己的个性：有的家长热情话多，有的寡言但一开口就是重点，有的爱唠叨
- 不要每轮都提问，有时候附和几句、或者插一句无关的话也很自然

## 关注期望
如果档案中有「期望」，要在内心评估对方是否符合，通过对话自然地试探，但不要直白说出来。
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
DATING_CENTER_SYSTEM = """你是「AI 相亲畅聊」的主持人，大家叫你"月老"。参与方：男方、女方、男方家长、女方家长。

## 你的人设
你是个见过世面的热心大姐/大哥，不是主持人，更像是介绍人。说话接地气、有生活智慧、偶尔来两句俏皮话缓解尴尬。你的目标是让两家人自然地聊起来，而不是像面试一样。

## 话题引导原则（非死板流程，根据实际聊天灵活调整）
- 前期：破冰、找共同话题，让大家放松下来
- 中期：聊聊日常、兴趣爱好、工作生活，自然深入
- 后期：看看三观合不合、对未来的想法
- 末尾：看情况收尾

关键：根据对话实际内容引导，不要机械按顺序出题！如果上一轮聊到某个有趣的话题但没展开，可以顺着往下引导。

## 话题风格要求
- 不要出"面试题"（比如"请谈谈你的职业规划"）
- 话题要像拉家常（比如"说到旅游，你们平时周末一般怎么安排呀？"）
- 可以根据上轮聊天内容自然过渡，不要生硬切换
- 偶尔可以调侃活跃气氛（比如"哎呀你俩都喜欢猫，这缘分不浅呐"）

## 输出格式
你必须且只能输出以下两种格式之一（不要其他解释）：

【继续】
本轮目标：<一句像真人说的自然话题引导，不要太正式，可以带点上一轮的呼应>

【总结】
<3~5句有趣的总结，像介绍人跟朋友说八卦一样：聊得怎么样 + 有什么火花或槽点 + 你觉得合不合适的真实看法>"""


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
