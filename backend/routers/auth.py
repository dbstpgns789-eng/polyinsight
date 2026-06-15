from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..core import auth as auth_core
from ..core import db
from ..core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session"


class SignupBody(BaseModel):
    email: str
    password: str
    invite: str


class LoginBody(BaseModel):
    email: str
    password: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )


async def _start_session(response: Response, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    await db.create_session(token, user_id, settings.SESSION_TTL_HOURS)
    _set_session_cookie(response, token)
    return token


@router.post("/signup")
async def signup(body: SignupBody, response: Response):
    if len(body.password) < 8:
        raise HTTPException(400, detail={"code": "ERR-AUTH-002", "message": "비밀번호는 8자 이상이어야 합니다."})
    if await db.get_user_by_email(body.email) is not None:
        raise HTTPException(400, detail={"code": "ERR-AUTH-003", "message": "이미 사용 중인 이메일입니다."})
    invite = await db.get_invite(body.invite)
    if invite is None or invite["used_by"] is not None:
        raise HTTPException(403, detail={"code": "ERR-AUTH-004", "message": "유효하지 않은 초대코드입니다."})
    user_id = await db.create_user(body.email, auth_core.hash_password(body.password))
    await db.consume_invite(body.invite, user_id)
    await _start_session(response, user_id)
    return {"email": body.email}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    user = await db.get_user_by_email(body.email)
    if user is None or not auth_core.verify_password(user["password_hash"], body.password):
        raise HTTPException(401, detail={"code": "ERR-AUTH-005", "message": "이메일 또는 비밀번호가 올바르지 않습니다."})
    await _start_session(response, user["id"])
    return {"email": user["email"]}


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await db.delete_session(token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(auth_core.get_current_user)):
    return {"email": user["email"], "role": user["role"]}
