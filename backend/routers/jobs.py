from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..agents.s7_renderer import S7Renderer
from ..core import db, plans
from ..core.auth import get_current_user, require_owned_job
from ..core.models import CardEditorData

# 이 라우터는 레거시 카드 에디터(CardEditorData) 서브시스템만 담당한다.
# 저작 진입(구 POST /api/upload → run_pipeline)은 L0(2026-07-09)에서 삭제됨 —
# 현행 저작 진입은 routers/deck.py 의 POST /api/deck/upload.
router = APIRouter(prefix="/api", tags=["jobs"])


# ── 상태 폴링 ─────────────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_status(job_id: str, user: dict = Depends(get_current_user)):
    """파이프라인 진행 상태 반환."""
    row = await require_owned_job(job_id, user)

    return {
        "jobId": row["job_id"],
        "status": row["status"],
        "stage": row["stage"],
        "progress": row["progress"],
        "degraded": bool(row["degraded"]),
        "warnings": row["warnings"],
        "updatedAt": row["updated_at"],
    }


# ── 카드 데이터 ───────────────────────────────────────────────────────────

@router.get("/cards/{job_id}")
async def get_cards(job_id: str, user: dict = Depends(get_current_user)):
    """카드 에디터용 CardEditorData 반환."""
    job = await require_owned_job(job_id, user)

    raw = await db.get_card_data(job_id)
    if raw is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "카드 데이터가 아직 없습니다."})

    return {
        "jobId": job_id,
        "filename": job["title"],
        "cardData": json.loads(raw),
        "updatedAt": job["updated_at"],
    }


# ── 자동저장 ──────────────────────────────────────────────────────────────

class PatchCardBody(BaseModel):
    cardData: dict


@router.patch("/cards/{job_id}/data")
async def patch_cards(job_id: str, body: PatchCardBody, user: dict = Depends(get_current_user)):
    """에디터 자동저장 — CardEditorData 전체 교체."""
    await require_owned_job(job_id, user)

    # 스키마 검증
    import logging as _logging
    try:
        CardEditorData.model_validate(body.cardData)
    except Exception as exc:
        _logging.getLogger(__name__).error("PATCH 422 validation error: %s", exc)
        raise HTTPException(422, detail={"code": "ERR-VAL-001", "message": str(exc)})

    await db.save_card_data(job_id, json.dumps(body.cardData))
    row = await db.get_job(job_id)
    return {"autoSaveStatus": "saved", "updatedAt": row["updated_at"]}


# ── 파일명 변경 / 프로젝트 삭제 ────────────────────────────────────────────

class RenameJobBody(BaseModel):
    title: str


@router.patch("/jobs/{job_id}")
async def rename_job(job_id: str, body: RenameJobBody, user: dict = Depends(get_current_user)):
    """프로젝트 표시명(파일명) 변경."""
    title = body.title.strip()
    if not title:
        raise HTTPException(400, detail={"code": "ERR-VAL-002", "message": "이름은 비울 수 없습니다."})
    await require_owned_job(job_id, user)
    await db.update_job_title(job_id, title)
    return {"ok": True, "title": title}


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job_endpoint(job_id: str, user: dict = Depends(get_current_user)):
    """프로젝트와 연관 데이터(card_data·card_images·exports) 일괄 삭제."""
    await require_owned_job(job_id, user)
    await db.delete_job(job_id)
    return None


# ── 내보내기 트리거 ───────────────────────────────────────────────────────

@router.post("/cards/{job_id}/export")
async def trigger_export(job_id: str, user: dict = Depends(get_current_user)):
    """카드 데이터 기반 PNG 재렌더링 → ZIP 저장. 렌더링 완료 후 응답."""
    import io
    import zipfile as zf_mod
    from ..core.models import S7Input

    plans.require_can_export(user)
    await require_owned_job(job_id, user)
    raw = await db.get_card_data(job_id)
    if raw is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "카드 데이터가 없습니다."})

    card_data = CardEditorData.model_validate_json(raw)
    renderer = S7Renderer()
    s7_out = await renderer.execute(S7Input(job_id=job_id, card_data=card_data, theme=card_data.theme))

    buf = io.BytesIO()
    with zf_mod.ZipFile(buf, "w", zf_mod.ZIP_DEFLATED) as zfile:
        for i, png in enumerate(s7_out.images, start=1):
            zfile.writestr(f"card_{i:02d}.png", png)
        zfile.writestr("card_data.json", card_data.model_dump_json(indent=2))

    export_id = str(uuid.uuid4())
    await db.save_export(export_id, job_id, buf.getvalue(), f"papersweep_{job_id[:8]}.zip")
    await db.log_event(
        "export",
        user_id=user["id"],
        job_id=job_id,
        payload={"export_id": export_id, "image_count": len(s7_out.images)},
    )
    return {"exportId": export_id, "status": "DONE"}
