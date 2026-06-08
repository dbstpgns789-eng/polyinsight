from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..agents.orchestrator import run_pipeline
from ..agents.s7_renderer import S7Renderer
from ..core import db
from ..core.models import CardEditorData, CardTheme

router = APIRouter(prefix="/api", tags=["jobs"])

_MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB


# ── 업로드 ──────────────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    # le=7: Haiku 4.5 출력 한계(8192 토큰) 안전권. 8장 이상은 큰 논문에서 JSON 잘림 위험.
    # 미래 등급제에서 상위 모델(Sonnet 등) 사용 시 등급별로 상한 확장.
    card_count: Annotated[int, Form(ge=3, le=7)] = 7,
):
    """PDF 업로드 → 파이프라인 백그라운드 시작."""
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, detail={"code": "ERR-INP-001", "message": "PDF 파일만 업로드 가능합니다."})

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(400, detail={"code": "ERR-INP-002", "message": "파일 크기가 50MB를 초과합니다."})

    job_id = str(uuid.uuid4())
    await db.create_job(job_id, title=file.filename)
    background_tasks.add_task(run_pipeline, job_id, pdf_bytes, CardTheme(), card_count)

    return {"jobId": job_id, "status": "PENDING"}


# ── 상태 폴링 ─────────────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """파이프라인 진행 상태 반환."""
    row = await db.get_job(job_id)
    if row is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})

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
async def get_cards(job_id: str):
    """카드 에디터용 CardEditorData 반환."""
    job = await db.get_job(job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})

    raw = await db.get_card_data(job_id)
    if raw is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "카드 데이터가 아직 없습니다."})

    return {
        "jobId": job_id,
        "cardData": json.loads(raw),
        "updatedAt": job["updated_at"],
    }


# ── 자동저장 ──────────────────────────────────────────────────────────────

class PatchCardBody(BaseModel):
    cardData: dict


@router.patch("/cards/{job_id}/data")
async def patch_cards(job_id: str, body: PatchCardBody):
    """에디터 자동저장 — CardEditorData 전체 교체."""
    job = await db.get_job(job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})

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
async def rename_job(job_id: str, body: RenameJobBody):
    """프로젝트 표시명(파일명) 변경."""
    title = body.title.strip()
    if not title:
        raise HTTPException(400, detail={"code": "ERR-VAL-002", "message": "이름은 비울 수 없습니다."})
    ok = await db.update_job_title(job_id, title)
    if not ok:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})
    return {"ok": True, "title": title}


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job_endpoint(job_id: str):
    """프로젝트와 연관 데이터(card_data·card_images·exports) 일괄 삭제."""
    ok = await db.delete_job(job_id)
    if not ok:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})
    return None


# ── 내보내기 트리거 ───────────────────────────────────────────────────────

@router.post("/cards/{job_id}/export")
async def trigger_export(job_id: str):
    """카드 데이터 기반 PNG 재렌더링 → ZIP 저장. 렌더링 완료 후 응답."""
    import io
    import zipfile as zf_mod
    from ..core.models import S7Input

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
    await db.save_export(export_id, job_id, buf.getvalue(), f"polyinsight_{job_id[:8]}.zip")
    return {"exportId": export_id, "status": "DONE"}
