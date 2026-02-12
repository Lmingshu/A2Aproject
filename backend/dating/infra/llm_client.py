# backend/dating/infra/llm_client.py
"""LLM 客户端抽象，支持 Kimi (Moonshot AI)、Claude API 或 Mock。"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from typing import Any

# 可选：若未安装 httpx，用 urllib
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

logger = logging.getLogger(__name__)

# -------- 全局共享 httpx 连接池，避免每次请求都新建连接 --------
_shared_client: httpx.AsyncClient | None = None


def _get_shared_client(timeout: float = 60.0) -> httpx.AsyncClient:
    """获取全局共享的 httpx 异步客户端（连接池复用）。"""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _shared_client


async def close_shared_client():
    """关闭全局客户端（在应用关闭时调用）。"""
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None


# -------- 重试工具 --------
async def _retry_request(func, max_retries: int = 2, base_delay: float = 1.0):
    """带指数退避的重试机制。"""
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last_exc = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning("LLM 请求失败 (第%d次)，%0.1fs 后重试: %s", attempt + 1, delay, type(e).__name__)
                await asyncio.sleep(delay)
            else:
                logger.error("LLM 请求失败，已达最大重试次数: %s", e)
    raise last_exc  # type: ignore


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
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async def _do_request():
            client = _get_shared_client()
            return await client.post(url, json=payload, headers=headers)

        try:
            r = await _retry_request(_do_request)
        except Exception as e:
            logger.error("Claude API 请求异常: %s", e)
            return f"[Claude API 网络异常，请稍后重试]"

        if r.status_code != 200:
            logger.warning("Claude API 错误 %d: %s", r.status_code, r.text[:200])
            return f"[AI 服务暂时不可用 ({r.status_code})，请稍后重试]"
        try:
            data = r.json()
        except Exception:
            return "[AI 返回格式异常]"
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""


class KimiLLMClient(LLMClient):
    """Kimi (Moonshot AI) API 客户端，兼容 OpenAI SDK 格式。"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "kimi-k2-turbo-preview",
        base_url: str = "https://api.moonshot.cn/v1",
    ):
        self.api_key = api_key or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
        if not self.api_key:
            return "[未配置 MOONSHOT_API_KEY，使用 Mock 回复]"
        if not HAS_HTTPX:
            return "[请安装 httpx: pip install httpx]"

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async def _do_request():
            client = _get_shared_client()
            return await client.post(url, json=payload, headers=headers)

        try:
            r = await _retry_request(_do_request)
        except Exception as e:
            logger.error("Kimi API 请求异常: %s", e)
            return "[Kimi API 网络异常，请稍后重试]"

        if r.status_code != 200:
            logger.warning("Kimi API 错误 %d: %s", r.status_code, r.text[:200])
            # 429 = 限流
            if r.status_code == 429:
                return "[AI 请求过于频繁，请稍等片刻再试]"
            return f"[AI 服务暂时不可用 ({r.status_code})，请稍后重试]"

        try:
            data = r.json()
        except Exception:
            return "[AI 返回格式异常]"

        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"].get("content", "")
        return "[AI 返回内容为空]"


class MockLLMClient(LLMClient):
    """无 API Key 时返回固定示例回复，便于本地跑通。"""

    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> str:
        # 模拟网络延迟，让体验更真实
        await asyncio.sleep(0.3)
        last = messages[-1] if messages else {}
        content = (last.get("content") or "").lower()
        if "介绍" in content or "你好" in content or "开场" in content:
            return "大家好，很高兴能一起聊聊，希望今天能互相多了解一下。"
        if "总结" in content or "匹配" in content:
            return "根据刚才的交流，双方在兴趣和家庭观上有一定共识，建议可以线下再约见一次，慢慢了解。"
        return "我觉得这个话题挺有意义的，大家也可以说说自己的想法。"
