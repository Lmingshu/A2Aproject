# backend/auth/session_store.py
"""登录态存储：session_id -> tokens + user_info 缓存。生产可换 Redis。"""

from __future__ import annotations

import secrets
import time
from typing import Any, Optional

# session_id -> { "access_token", "refresh_token", "expires_at", "user_info" }
_sessions: dict[str, dict[str, Any]] = {}


def create_session(access_token: str, refresh_token: str, expires_in: int = 7200) -> str:
    session_id = secrets.token_urlsafe(24)
    _sessions[session_id] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + expires_in,
        "user_info": None,
    }
    return session_id


def get_session(session_id: Optional[str]) -> Optional[dict[str, Any]]:
    if not session_id:
        return None
    return _sessions.get(session_id)


def set_session_user_info(session_id: str, user_info: dict[str, Any]) -> None:
    if session_id in _sessions:
        _sessions[session_id]["user_info"] = user_info


def update_session_tokens(session_id: str, access_token: str, refresh_token: str, expires_in: int) -> None:
    if session_id in _sessions:
        _sessions[session_id]["access_token"] = access_token
        _sessions[session_id]["refresh_token"] = refresh_token
        _sessions[session_id]["expires_at"] = time.time() + expires_in


def delete_session(session_id: Optional[str]) -> None:
    if session_id:
        _sessions.pop(session_id, None)
