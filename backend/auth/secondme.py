# backend/auth/secondme.py
"""
SecondMe OAuth2 集成（参考 Second-Me-Skills 与官方文档）。
- 授权 URL: https://go.second.me/oauth/?client_id=...&redirect_uri=...&response_type=code&state=...
- Token 交换: POST {base}/api/oauth/token/code (application/x-www-form-urlencoded)
- 用户信息: GET {base}/api/secondme/user/info, GET {base}/api/secondme/user/shades
文档: https://develop-docs.second.me/zh/docs/authentication/oauth2
"""

from __future__ import annotations

import os
import secrets
import time
from typing import Any, Optional
from urllib.parse import urlencode

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# 与 Second-Me-Skills 一致
SECONDME_OAUTH_URL = "https://go.second.me/oauth/"
SECONDME_API_BASE = "https://app.mindos.com/gate/lab"
SCOPES = ["user.info", "user.info.shades", "user.info.softmemory"]


def get_config() -> dict[str, str]:
    return {
        "client_id": os.environ.get("SECONDME_CLIENT_ID", ""),
        "client_secret": os.environ.get("SECONDME_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("SECONDME_REDIRECT_URI", "").rstrip("/"),
    }


def build_login_url(state: Optional[str] = None) -> tuple[str, str]:
    """
    构造 SecondMe 授权登录 URL 和 state。
    返回 (auth_url, state)。
    """
    cfg = get_config()
    if not cfg["client_id"] or not cfg["redirect_uri"]:
        raise ValueError("SECONDME_CLIENT_ID 和 SECONDME_REDIRECT_URI 必须配置")
    state = state or secrets.token_urlsafe(24)
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "state": state,
    }
    url = f"{SECONDME_OAUTH_URL}?{urlencode(params)}"
    return url, state


async def exchange_code_for_token(code: str, redirect_uri: Optional[str] = None) -> dict[str, Any]:
    """
    用授权码换取 access_token、refresh_token。
    响应格式（SecondMe 统一包装，camelCase）：
    { "code": 0, "data": { "accessToken", "refreshToken", "tokenType", "expiresIn", "scope" } }
    """
    cfg = get_config()
    redirect_uri = redirect_uri or cfg["redirect_uri"]
    if not HAS_HTTPX:
        raise RuntimeError("请安装 httpx: pip install httpx")
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"{SECONDME_API_BASE}/api/oauth/token/code",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
        )
    data = r.json()
    if data.get("code") != 0 or not data.get("data"):
        raise ValueError(data.get("message", "Token 交换失败"))
    return data["data"]


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """用 refresh_token 刷新 access_token。"""
    cfg = get_config()
    if not HAS_HTTPX:
        raise RuntimeError("请安装 httpx: pip install httpx")
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(
            f"{SECONDME_API_BASE}/api/oauth/token/refresh",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            },
        )
    data = r.json()
    if data.get("code") != 0 or not data.get("data"):
        raise ValueError(data.get("message", "Token 刷新失败"))
    return data["data"]


async def fetch_user_info(access_token: str) -> dict[str, Any]:
    """
    拉取 SecondMe 用户信息。
    GET /api/secondme/user/info -> result.data (name, bio, avatar, email, ...)
    GET /api/secondme/user/shades -> result.data.shades (兴趣标签)
    """
    if not HAS_HTTPX:
        raise RuntimeError("请安装 httpx: pip install httpx")
    headers = {"Authorization": f"Bearer {access_token}"}

    # 所有请求共用一个 AsyncClient，避免连接泄漏
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. 拉取基本用户信息
        info_r = await client.get(
            f"{SECONDME_API_BASE}/api/secondme/user/info",
            headers=headers,
        )
        info_data = info_r.json()
        if info_data.get("code") != 0 or not info_data.get("data"):
            raise ValueError(info_data.get("message", "获取用户信息失败"))
        user = info_data["data"]

        # 2. 可选：拉取兴趣标签
        try:
            shades_r = await client.get(
                f"{SECONDME_API_BASE}/api/secondme/user/shades",
                headers=headers,
            )
            shades_data = shades_r.json()
            if shades_data.get("code") == 0 and shades_data.get("data"):
                user["shades"] = shades_data["data"].get("shades", [])
            else:
                user["shades"] = []
        except Exception:
            user["shades"] = []

        # 3. 可选：拉取软记忆（个人知识库）
        try:
            softmemory_r = await client.get(
                f"{SECONDME_API_BASE}/api/secondme/user/softmemory",
                headers=headers,
                params={"pageNo": 1, "pageSize": 50},
            )
            softmemory_data = softmemory_r.json()
            if softmemory_data.get("code") == 0 and softmemory_data.get("data"):
                user["softmemory"] = softmemory_data["data"].get("list", [])
            else:
                user["softmemory"] = []
        except Exception:
            user["softmemory"] = []

    return user
