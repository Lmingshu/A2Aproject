# backend/server.py
"""
A2A 相亲后端入口。
启动：在项目根目录执行
  python -m uvicorn backend.server:app --reload --port 8080
或在 backend 目录：
  uvicorn server:app --reload --port 8080
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 保证 backend 与项目根在 path 中
_backend = Path(__file__).resolve().parent
_root = _backend.parent
for p in (str(_root), str(_backend)):
    if p not in sys.path:
        sys.path.insert(0, p)

# 加载 backend/.env（SecondMe、Claude 等）
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env")
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as dating_router
from backend.api.auth_routes import router as auth_router

app = FastAPI(
    title="A2A 相亲",
    description="过年回家相亲不尴尬 — 男女双方与家长 AI 畅聊",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dating_router)
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "a2a-dating"}


# 前端静态文件放在最后挂载，避免把 /health、/api 等误交给静态
_frontend = _root / "website"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="static")
