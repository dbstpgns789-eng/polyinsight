from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..core import db
from ..core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects")
async def list_projects(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """프로젝트 목록 — 본인 소유만."""
    offset = (page - 1) * limit
    rows = await db.list_jobs(limit=limit, offset=offset, user_id=user["id"])

    if status:
        rows = [r for r in rows if r["status"] == status.upper()]

    projects = [
        {
            "jobId": r["job_id"],
            "title": r["title"],
            "status": r["status"],
            "createdAt": r["created_at"],
            "updatedAt": r["updated_at"],
        }
        for r in rows
    ]
    return {"projects": projects, "total": len(projects), "page": page}


@router.get("/projects/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    """대시보드 통계 — 본인 소유만."""
    rows = await db.list_jobs(limit=1000, offset=0, user_id=user["id"])
    counts: dict[str, int] = {"PENDING": 0, "RUNNING": 0, "DONE": 0, "ERROR": 0}
    for r in rows:
        s = r["status"]
        if s in counts:
            counts[s] += 1

    return {
        "total": len(rows),
        "done": counts["DONE"],
        "draft": counts["PENDING"],
        "running": counts["RUNNING"],
        "error": counts["ERROR"],
    }


@router.get("/activities")
async def get_activities(user: dict = Depends(get_current_user)):
    """최근 활동 피드 (최신 20건) — 본인 소유만."""
    rows = await db.list_jobs(limit=20, offset=0, user_id=user["id"])
    activities = [
        {
            "type": r["status"],
            "jobId": r["job_id"],
            "title": r["title"],
            "at": r["updated_at"],
        }
        for r in rows
    ]
    return {"activities": activities}
