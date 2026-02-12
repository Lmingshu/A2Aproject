# backend/dating/lobby.py
"""大厅管理：NPC 角色库 + 动态用户管理。"""

from __future__ import annotations

import random
from typing import Dict, List

from backend.dating.models import AgentRole, DatingProfile

# 内存中的大厅用户列表（生产环境应用 Redis）
LOBBY_USERS: Dict[str, DatingProfile] = {}

# -------- 丰富的 NPC 角色库 --------
_NPC_POOL = [
    # ---- 男性 NPC ----
    {
        "id": "npc_alex", "role": AgentRole.MALE,
        "display_name": "Alex·科技新贵", "age": 28,
        "occupation": "AI 算法工程师 @ 字节跳动",
        "hobbies": "滑雪, 德州扑克, 养了两只英短, 周末喜欢逛科技展",
        "family_view": "父母是大学教授，家庭氛围开明民主，不催婚但偶尔旁敲侧击",
        "expectation": "希望对方有自己的热爱和独立人格，接受偶尔加班，周末一起探索城市",
        "extra": "INTJ，理工直男但在学说情话，最近在练做饭",
        "avatar_url": "images/npc-male-3d.png",
        "parent_name": "Alex的爸爸", "parent_style": "学者型父亲，说话严谨但心里希望儿子早成家",
    },
    {
        "id": "npc_chen", "role": AgentRole.MALE,
        "display_name": "陈默·文艺青年", "age": 30,
        "occupation": "独立纪录片导演 / 自由撰稿人",
        "hobbies": "拍纪录片, 骑行, 逛独立书店, 黑胶唱片收藏",
        "family_view": "单亲家庭长大，妈妈是中学老师，母子关系很亲近",
        "expectation": "找一个能聊得来的人，不在乎物质条件，更看重精神共鸣",
        "extra": "INFP，外表高冷内心柔软，朋友圈全是日落照片",
        "avatar_url": "",
        "parent_name": "陈默的妈妈", "parent_style": "温柔的妈妈，担心儿子收入不稳定但又尊重他的选择",
    },
    {
        "id": "npc_wang", "role": AgentRole.MALE,
        "display_name": "王大壮·阳光体育生", "age": 26,
        "occupation": "健身教练 / 前省队篮球运动员",
        "hobbies": "篮球, CrossFit, 做饭(蛋白质餐), 打游戏",
        "family_view": "东北大家庭，过年要放一千响的鞭炮，亲戚团特别热闹",
        "expectation": "想找个温柔的女生，能一起健身最好，不行就一起吃也行",
        "extra": "ESFP，社交达人，说话大嗓门，但对喜欢的人很细心",
        "avatar_url": "",
        "parent_name": "王大壮的爸爸", "parent_style": "东北豪爽型父亲，见面先问对方能不能喝酒",
    },
    {
        "id": "npc_li", "role": AgentRole.MALE,
        "display_name": "李泽言·金融精英", "age": 32,
        "occupation": "投行VP / CFA持证",
        "hobbies": "高尔夫, 红酒品鉴, 看财经新闻, 偶尔弹钢琴",
        "family_view": "传统中产家庭，父母经商，希望门当户对",
        "expectation": "希望对方知性优雅，有稳定工作，能理解金融行业的高压节奏",
        "extra": "ENTJ，工作狂但承诺恋爱后会留出周末，衣柜全是西装",
        "avatar_url": "",
        "parent_name": "李泽言的妈妈", "parent_style": "优雅但挑剔的妈妈，会不动声色地考察对方家庭背景",
    },

    # ---- 女性 NPC ----
    {
        "id": "npc_luna", "role": AgentRole.FEMALE,
        "display_name": "Luna·插画师", "age": 26,
        "occupation": "自由插画师 / 策展人",
        "hobbies": "看展, 烘焙, 收集黑胶唱片, 养了一只柯基叫「墩墩」",
        "family_view": "家庭氛围温暖，周末经常全家一起聚餐做饭，爸妈都是老师",
        "expectation": "喜欢温文尔雅、懂一点艺术的男生，最好对生活有热情",
        "extra": "ENFP，话匣子一打开就停不下来，笑点极低",
        "avatar_url": "images/npc-female-3d.png",
        "parent_name": "Luna的妈妈", "parent_style": "热心肠的妈妈，会拉着人聊家常，关心对方吃没吃饭",
    },
    {
        "id": "npc_lin", "role": AgentRole.FEMALE,
        "display_name": "林小溪·学霸医生", "age": 29,
        "occupation": "三甲医院心内科住院医师",
        "hobbies": "瑜伽, 看推理小说, 做手账, 偶尔追韩剧",
        "family_view": "父母都是医生，家风严谨但不古板，尊重女儿独立选择",
        "expectation": "希望对方理解医生的作息不规律，能包容偶尔的临时取消约会",
        "extra": "ISTJ，表面高冷但私下是吐槽达人，手机壁纸是自家猫",
        "avatar_url": "",
        "parent_name": "林小溪的爸爸", "parent_style": "严肃的医生爸爸，问问题像查房一样系统但其实很疼女儿",
    },
    {
        "id": "npc_zhao", "role": AgentRole.FEMALE,
        "display_name": "赵甜甜·美食博主", "age": 25,
        "occupation": "美食自媒体博主 / 前酒店甜品师",
        "hobbies": "探店, 拍美食视频, 旅行, 学各国料理",
        "family_view": "四川家庭，爸妈开了一家老火锅店，家里天天飘着火锅味",
        "expectation": "想找一个愿意陪她吃遍天下的男生，能吃辣加分！",
        "extra": "ESFJ，朋友圈每天九宫格美食，社交恐惧但一聊到吃的就超兴奋",
        "avatar_url": "",
        "parent_name": "赵甜甜的妈妈", "parent_style": "四川火辣妈妈，说话直来直去，见面先让你吃三碗",
    },
    {
        "id": "npc_su", "role": AgentRole.FEMALE,
        "display_name": "苏念·独立设计师", "age": 28,
        "occupation": "室内设计师 / 有自己的工作室",
        "hobbies": "逛家居市场, 画设计图, 养植物, 周末去郊外露营",
        "family_view": "父母退休，爸爸喜欢钓鱼妈妈跳广场舞，家庭关系轻松自在",
        "expectation": "希望对方有审美，生活有品质感，不要大男子主义",
        "extra": "INFJ，外表淡然内心戏丰富，会默默观察对方的小细节",
        "avatar_url": "",
        "parent_name": "苏念的爸爸", "parent_style": "佛系爸爸，不干涉但暗中观察，偶尔冒出一句犀利点评",
    },
]


def init_lobby():
    """初始化大厅，载入全部 NPC。"""
    for npc in _NPC_POOL:
        LOBBY_USERS[npc["id"]] = DatingProfile(
            role=npc["role"],
            display_name=npc["display_name"],
            age=npc.get("age"),
            occupation=npc.get("occupation", ""),
            hobbies=npc.get("hobbies", ""),
            family_view=npc.get("family_view", ""),
            expectation=npc.get("expectation", ""),
            extra=npc.get("extra", ""),
            avatar_url=npc.get("avatar_url", ""),
        )


def get_npc_meta(npc_id: str) -> dict | None:
    """获取 NPC 的元信息（含家长风格等，不在 DatingProfile 中的字段）。"""
    for npc in _NPC_POOL:
        if npc["id"] == npc_id:
            return npc
    return None


def add_user_to_lobby(user_id: str, profile: DatingProfile):
    """将新用户加入大厅。"""
    LOBBY_USERS[user_id] = profile


def get_lobby_users() -> List[Dict]:
    """获取大厅列表（前端渲染用）。"""
    if not LOBBY_USERS:
        init_lobby()
    return [
        {
            "id": uid,
            "display_name": p.display_name,
            "age": p.age,
            "occupation": p.occupation,
            "avatar_url": p.avatar_url,
            "role": p.role.value,
            "hobbies": p.hobbies,
            "expectation": p.expectation,
            "extra": p.extra,
            "desc": f"{p.age}岁 · {p.occupation}" if p.age else p.occupation,
        }
        for uid, p in LOBBY_USERS.items()
    ]


def get_user_from_lobby(user_id: str) -> DatingProfile | None:
    return LOBBY_USERS.get(user_id)


def random_match(exclude_ids: list[str] | None = None, prefer_role: AgentRole | None = None) -> tuple[str, DatingProfile] | None:
    """随机匹配一个 NPC（排除指定 ID，可偏好角色）。"""
    if not LOBBY_USERS:
        init_lobby()
    candidates = [
        (uid, p) for uid, p in LOBBY_USERS.items()
        if (not exclude_ids or uid not in exclude_ids)
        and (prefer_role is None or p.role == prefer_role)
        and uid.startswith("npc_")  # 只匹配 NPC
    ]
    if not candidates:
        return None
    return random.choice(candidates)
