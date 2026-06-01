from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..core import db

router = APIRouter(prefix="/api", tags=["export"])


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
