from __future__ import annotations

import io
import json
import uuid
import zipfile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Response, UploadFile

from ..agents.deck.pipeline import run_authoring_pipeline
from ..core import db
from ..core.auth import get_current_user
from ..core.config import settings

router = APIRouter(prefix="/api", tags=["deck"])

_MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/deck/upload", status_code=202)
async def deck_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    card_count: Annotated[int, Form(ge=3, le=12)] = 7,
    persona: Annotated[str | None, Form()] = None,
    user: dict = Depends(get_current_user),
):
    """PDF 업로드 → 단일 저작 파이프라인 백그라운드 시작 (헌법 v3.0)."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, detail={"code": "ERR-INP-001", "message": "PDF 파일만 업로드 가능합니다."})

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(400, detail={"code": "ERR-INP-002", "message": "파일 크기가 50MB를 초과합니다."})

    # 티어 상한으로 클램프(base=Sonnet/AUTHOR_MAX_CARDS, 추후 premium 확장)
    card_count = max(3, min(card_count, settings.AUTHOR_MAX_CARDS))

    job_id = str(uuid.uuid4())
    await db.create_job(job_id, title=file.filename)
    await db.log_event("deck_upload", user_id=user["id"], job_id=job_id,
                       payload={"filename": file.filename, "card_count": card_count})
    background_tasks.add_task(
        run_authoring_pipeline, job_id, pdf_bytes, card_count, persona, user["id"]
    )
    return {"jobId": job_id, "status": "PENDING"}


@router.get("/deck/{job_id}")
async def get_deck(job_id: str, user: dict = Depends(get_current_user)):
    """덱 뷰용 — 저작 HTML + 충실성 검증 + 상태."""
    job = await db.get_job(job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})
    deck = await db.get_authored_deck(job_id)
    verify = None
    if deck and deck.get("verify_json"):
        try:
            verify = json.loads(deck["verify_json"])
        except Exception:
            verify = None
    return {
        "jobId": job_id,
        "filename": job["title"],
        "status": job["status"],
        "warnings": job.get("warnings", []),
        "html": deck["html"] if deck else None,
        "verify": verify,
        "cardCount": deck["card_count"] if deck else 0,
    }


@router.get("/deck/{job_id}/cards/{card_num}")
async def get_deck_card(job_id: str, card_num: int, user: dict = Depends(get_current_user)):
    """덱 카드 1장 PNG."""
    images = await db.get_card_images(job_id)
    png = images.get(card_num)
    if png is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "카드 이미지가 없습니다."})
    return Response(content=png, media_type="image/png")


@router.post("/deck/{job_id}/export")
async def export_deck(job_id: str, user: dict = Depends(get_current_user)):
    """저장된 카드 PNG + HTML + 검증 결과를 ZIP으로. 다운로드는 /api/export/{id}/download 재사용."""
    deck = await db.get_authored_deck(job_id)
    if deck is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})
    images = await db.get_card_images(job_id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in sorted(images):
            zf.writestr(f"card_{n:02d}.png", images[n])
        zf.writestr("deck.html", deck["html"] or "")
        if deck.get("verify_json"):
            zf.writestr("verify.json", deck["verify_json"])

    export_id = str(uuid.uuid4())
    await db.save_export(export_id, job_id, buf.getvalue(), f"polyinsight_deck_{job_id[:8]}.zip")
    await db.log_event("deck_export", user_id=user["id"], job_id=job_id,
                       payload={"export_id": export_id, "image_count": len(images)})
    return {"exportId": export_id, "status": "DONE"}
