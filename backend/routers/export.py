from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..agents.s7_renderer import _playwright_pool, _playwright_render_via_url_sync
from ..core import db
from ..core.config import settings

router = APIRouter(prefix="/api", tags=["export"])


def _safe_filename(name: str | None) -> str:
    base = re.sub(r"\.pdf$", "", name or "card", flags=re.IGNORECASE)
    base = re.sub(r'[\\/:*?"<>|]+', "_", base).strip() or "card"
    return base[:80]


@router.get("/export/{export_job_id}/download")
async def download_zip(export_job_id: str):
    """완료된 ZIP 다운로드."""
    row = await db.get_export(export_job_id)
    if row is None:
        raise HTTPException(410, detail={"code": "ERR-EXP-004", "message": "파일이 만료되었습니다. 다시 내보내기를 실행해 주세요."})

    return Response(
        content=row["zip_bytes"],
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{row["filename"]}"'},
    )


@router.get("/cards/{job_id}/image/{card_num}")
async def get_card_image(job_id: str, card_num: int):
    """개별 카드 PNG 반환."""
    images = await db.get_card_images(job_id)
    png = images.get(card_num)
    if png is None:
        raise HTTPException(404, detail={"code": "ERR-EXP-001", "message": "이미지를 찾을 수 없습니다."})

    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="card_{card_num:02d}.png"'},
    )


@router.get("/cards/{job_id}/download/{card_num}")
async def download_card_png(job_id: str, card_num: int):
    """단일 카드를 즉석 렌더(S7 React goto)해서 PNG 첨부 다운로드. 항상 현재 저장 상태 반영."""
    job = await db.get_job(job_id)
    if job is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "프로젝트를 찾을 수 없습니다."})
    if await db.get_card_data(job_id) is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-002", "message": "카드 데이터가 없습니다."})

    url = f"{settings.WEB_BASE_URL}/render/{job_id}/{card_num}"
    timeout_s = settings.PLAYWRIGHT_TIMEOUT_MS / 1000
    loop = asyncio.get_event_loop()
    images, _warnings = await loop.run_in_executor(
        _playwright_pool, _playwright_render_via_url_sync, [url], timeout_s
    )
    if not images:
        raise HTTPException(502, detail={"code": "ERR-EXP-002", "message": "카드 렌더링에 실패했습니다."})

    fname = f"{_safe_filename(job['title'])}_{card_num:02d}.png"
    ascii_fallback = re.sub(r"[^\x20-\x7E]", "_", fname)
    disposition = f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(fname)}"
    return Response(
        content=images[0],
        media_type="image/png",
        headers={"Content-Disposition": disposition},
    )
