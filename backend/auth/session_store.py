# backend/auth/session_store.py
"""
登录态存储：session_id -> tokens + user_info 缓存。

注意：当前使用内存存储，服务重启后所有 session 和大厅用户数据会丢失。
生产环境建议使用 Redis 等持久化存储。
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

SESSION_MAX_AGE = 30 * 24 * 3600  # 30 天
_CLEANUP_INTERVAL = 3600  # 每小时清理一次
_last_cleanup = 0.0

# session_id -> { "access_token", "refresh_token", "expires_at", "user_info", "created_at" }
_sessions: dict[str, dict[str, Any]] = {}


def _cleanup_expired():
    """定期清理过期 session。"""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    expired = [
        sid for sid, sess in _sessions.items()
        if now - sess.get("created_at", 0) > SESSION_MAX_AGE
    ]
    for sid in expired:
        _sessions.pop(sid, None)
    if expired:
        logger.info("清理了 %d 个过期 session", len(expired))


def create_session(access_token: str, refresh_token: str, expires_in: int = 7200) -> str:
    session_id = secrets.token_urlsafe(24)
    _sessions[session_id] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + expires_in,
        "user_info": None,
        "created_at": time.time(),
    }
    return session_id


def get_session(session_id: Optional[str]) -> Optional[dict[str, Any]]:
    if not session_id:
        return None
    _cleanup_expired()
    sess = _sessions.get(session_id)
    if not sess:
        return None
    # 检查会话是否过期
    if time.time() - sess.get("created_at", 0) > SESSION_MAX_AGE:
        _sessions.pop(session_id, None)
        return None
    return sess


def set_session_user_info(session_id: str, user_info: dict[str, Any]) -> None:
    if session_id in _sessions:
        _sessions[session_id]["user_info"] = user_info


def set_session_gender(session_id: str, gender: str) -> None:
    """保存用户选择的性别到 session。"""
    if session_id in _sessions:
        _sessions[session_id]["gender"] = gender


def get_session_gender(session_id: str) -> Optional[str]:
    """获取用户在 session 中选择的性别。"""
    sess = _sessions.get(session_id)
    if sess:
        return sess.get("gender")
    return None


def update_session_tokens(session_id: str, access_token: str, refresh_token: str, expires_in: int) -> None:
    if session_id in _sessions:
        _sessions[session_id]["access_token"] = access_token
        _sessions[session_id]["refresh_token"] = refresh_token
        _sessions[session_id]["expires_at"] = time.time() + expires_in


def delete_session(session_id: Optional[str]) -> None:
    if session_id:
        _sessions.pop(session_id, None)


def get_all_sessions() -> dict[str, dict[str, Any]]:
    """获取所有有效 session（调试用）。"""
    _cleanup_expired()
    return dict(_sessions)
