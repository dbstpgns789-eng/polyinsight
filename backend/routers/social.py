"""소셜 계정 연동 상태 관리 (2026-07-23). 발행 OAuth는 auth.py, 여기는 상태 조회/해제."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core import db
from ..core.auth import get_current_user

router = APIRouter(prefix="/api/social", tags=["social"])


@router.get("/instagram/status")
async def instagram_status(user: dict = Depends(get_current_user)):
    acct = await db.get_social_account(user["id"], "instagram")
    return {"connected": acct is not None, "username": acct["ig_username"] if acct else None}


@router.delete("/instagram")
async def instagram_disconnect(user: dict = Depends(get_current_user)):
    await db.delete_social_account(user["id"], "instagram")
    await db.log_event("instagram_disconnected", user_id=user["id"])
    return {"ok": True}
