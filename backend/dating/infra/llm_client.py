# backend/dating/infra/llm_client.py
"""LLM 客户端抽象，支持 Claude API 或 Mock。"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

# 可选：若未安装 httpx，用 urllib
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
        """输入 messages [{"role":"user"/"assistant","content":"..."}]，返回 assistant 回复文本。"""
        pass


class ClaudeLLMClient(LLMClient):
    """Claude API（与 Towow 的 ClaudePlatformClient 用法类似）。"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        base_url: str = "https://api.anthropic.com",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("TOWOW_ANTHROPIC_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
        if not self.api_key:
            return "[未配置 ANTHROPIC_API_KEY，使用 Mock 回复]"
        if not HAS_HTTPX:
            return "[请安装 httpx: pip install httpx]"

        # 转为 Claude 格式：system 取第一条 system 或首条 user 前文
        system = ""
        claude_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system = content
            else:
                claude_messages.append({"role": role, "content": content})

        url = f"{self.base_url}/v1/messages"
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system or "You are a helpful assistant.",
            "messages": claude_messages,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                url,
                json=payload,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            if r.status_code != 200:
                return f"[API 错误 {r.status_code}] {r.text[:200]}"
            data = r.json()
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""

    # 同步版供无 async 环境
    def chat_sync(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.chat(messages, max_tokens))


class MockLLMClient(LLMClient):
    """无 API Key 时返回固定示例回复，便于本地跑通。"""

    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
        last = messages[-1] if messages else {}
        content = (last.get("content") or "").lower()
        if "介绍" in content or "你好" in content or "开场" in content:
            return "大家好，很高兴能一起聊聊，希望今天能互相多了解一下。"
        if "总结" in content or "匹配" in content:
            return "根据刚才的交流，双方在兴趣和家庭观上有一定共识，建议可以线下再约见一次，慢慢了解。"
        return "我觉得这个话题挺有意义的，大家也可以说说自己的想法。"
