# backend/api/auth_routes.py
"""SecondMe OAuth2 登录与用户信息接口。"""

from __future__ import annotations

import os
import logging
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from backend.auth.secondme import (
    build_login_url,
    exchange_code_for_token,
    fetch_user_info,
    get_config,
    refresh_access_token,
)
from backend.auth.session_store import (
    create_session as create_auth_session,
    delete_session,
    get_session,
    get_session_gender,
    set_session_user_info,
    update_session_tokens,
)
from backend.dating.adapters import secondme_to_profile_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Cookie 名（可配置）
SESSION_COOKIE_NAME = "a2a_session"
SESSION_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天
FRONTEND_REDIRECT_URI = "/"  # 登录成功后跳转的前端路径（相对路径）
# 若前后端分离，在 .env 中设置 FRONTEND_BASE_URL 如 http://localhost:3000，回调将重定向到该地址
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").rstrip("/")


@router.get("/secondme/login")
async def secondme_login(
    state: Optional[str] = Query(None),
    role: Optional[str] = Query(None, description="登录后作为男方 male / 女方 female"),
    redirect_path: Optional[str] = Query(None, description="登录成功后跳转路径"),
) -> RedirectResponse:
    """
    发起 SecondMe OAuth 登录。
    可选 query: role=male|female（用于登录后预填男方/女方档案）, redirect_path=...
    """
    cfg = get_config()
    if not cfg["client_id"] or not cfg["redirect_uri"]:
        raise HTTPException(status_code=503, detail="SecondMe 未配置（缺少 SECONDME_CLIENT_ID 或 SECONDME_REDIRECT_URI）")
    try:
        url, new_state = build_login_url(state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 将 role/redirect_path 存到 state 中，callback 时解析
    state_with_role = f"{new_state}"
    if role:
        state_with_role += f":role={role}"
    if redirect_path:
        state_with_role += f":path={redirect_path}"
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs["state"] = [state_with_role]
    redirect_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(qs, doseq=True)}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/secondme/callback")
async def secondme_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
) -> RedirectResponse:
    """
    SecondMe 授权回调。用 code 换 token，创建 session，写 cookie，重定向回前端。
    state 可带 :role=male|female :path=/xxx
    使用绝对 URL 重定向，避免相对路径导致 query 丢失。
    """
    base_url = FRONTEND_BASE_URL or str(request.base_url).rstrip("/")
    if not code:
        return RedirectResponse(url=f"{base_url}{FRONTEND_REDIRECT_URI}?error=missing_code", status_code=302)
    try:
        token_data = await exchange_code_for_token(code)
    except Exception as e:
        logger.warning("Token exchange failed: %s", e)
        return RedirectResponse(url=f"{base_url}{FRONTEND_REDIRECT_URI}?error=token_failed", status_code=302)

    access_token = token_data.get("accessToken") or token_data.get("access_token")
    refresh_token = token_data.get("refreshToken") or token_data.get("refresh_token")
    expires_in = token_data.get("expiresIn") or token_data.get("expires_in") or 7200
    if not access_token:
        return RedirectResponse(url=f"{base_url}{FRONTEND_REDIRECT_URI}?error=no_token", status_code=302)

    session_id = create_auth_session(access_token, refresh_token, expires_in)

    # 拉取用户信息并缓存到 session
    try:
        user_info = await fetch_user_info(access_token)
        set_session_user_info(session_id, user_info)
        
        # 注意：不在此处加入大厅，等用户在前端选择性别后，
        # 通过 POST /api/dating/lobby/update-gender 正式加入大厅
        logger.info("用户 %s 登录成功，待选择性别后加入大厅", user_info.get("name"))
    except Exception as e:
        logger.warning("Fetch user info failed: %s", e)

    # 解析 state 中的 role / path
    role_param = ""
    path_param = FRONTEND_REDIRECT_URI
    if state:
        for part in state.split(":"):
            if part.startswith("role="):
                role_param = part.split("=", 1)[1].strip()
            elif part.startswith("path="):
                path_param = part.split("=", 1)[1].strip() or FRONTEND_REDIRECT_URI

    path_param = path_param if path_param.startswith("/") else "/" + path_param
    redirect_to = base_url + path_param
    if "?" in redirect_to:
        redirect_to += "&"
    else:
        redirect_to += "?"
    redirect_to += f"session={session_id}"
    if role_param:
        redirect_to += f"&secondme_role={role_param}"

    resp = RedirectResponse(url=redirect_to, status_code=302)
    resp.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/me")
async def get_me(request: Request, session_id: Optional[str] = Query(None)) -> dict[str, Any]:
    """
    获取当前登录用户信息（SecondMe 档案）。
    优先从 Cookie 读 session，也可 query 传 session_id（用于回调页拿到 session 后请求）。
    返回 secondme 用户信息 + profile（用于前端预填男方/女方表单）。
    """
    if not session_id:
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return {"logged_in": False, "profile": None}

    sess = get_session(session_id)
    if not sess:
        return {"logged_in": False, "profile": None}

    user_info = sess.get("user_info")
    if not user_info:
        access_token = sess.get("access_token")
        if access_token:
            try:
                user_info = await fetch_user_info(access_token)
                set_session_user_info(session_id, user_info)
            except Exception as e:
                logger.warning("Fetch user info in /me: %s", e)
                return {"logged_in": True, "profile": None, "error": str(e)}
        else:
            return {"logged_in": True, "profile": None}

    if not user_info:
        return {"logged_in": True, "profile": None}

    profile = secondme_to_profile_input(user_info)
    gender = get_session_gender(session_id)
    return {
        "logged_in": True,
        "session_id": session_id,
        "profile": profile,
        "name": user_info.get("name"),
        "avatar_url": user_info.get("avatarUrl") or user_info.get("avatar"),
        "gender": gender,  # 用户选择的性别（可能为 None，前端默认 male）
    }


@router.post("/logout")
async def logout(request: Request, response: Response, session_id: Optional[str] = Query(None)) -> dict[str, Any]:
    """登出：删除服务端 session，并清除 Cookie。"""
    sid = session_id or request.cookies.get(SESSION_COOKIE_NAME)
    if sid:
        delete_session(sid)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}
