# backend/api/events.py
"""简单的事件推送：内存版，可替换为 WebSocket。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class InMemoryEventPusher:
    """按 session_id 订阅，推送事件（可被 WebSocket 或 SSE 包装）。"""

    def __init__(self):
        self._listeners: dict[str, list[Callable[[dict], Any]]] = {}

    def subscribe(self, session_id: str, callback: Callable[[dict], Any]) -> None:
        self._listeners.setdefault(session_id, []).append(callback)

    def unsubscribe(self, session_id: str, callback: Callable[[dict], Any]) -> None:
        if session_id in self._listeners:
            try:
                self._listeners[session_id].remove(callback)
            except ValueError:
                pass

    async def push(self, session_id: str, event: dict) -> None:
        payload = {"session_id": session_id, **event}
        for cb in self._listeners.get(session_id, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(payload)
                else:
                    cb(payload)
            except Exception as e:
                logger.warning("event callback error: %s", e)


# 全局单例，供 server 与 engine 使用
_event_pusher: Optional[InMemoryEventPusher] = None


def get_event_pusher() -> InMemoryEventPusher:
    global _event_pusher
    if _event_pusher is None:
        _event_pusher = InMemoryEventPusher()
    return _event_pusher
