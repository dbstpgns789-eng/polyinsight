from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Query

from ..core.config import settings

router = APIRouter(prefix="/api", tags=["images"])

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(8.0)


async def _search_pexels(client: httpx.AsyncClient, query: str, per_page: int) -> list[dict[str, Any]]:
    resp = await client.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": per_page},
        headers={"Authorization": settings.PEXELS_API_KEY},
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "id": f"pexels_{photo['id']}",
            "provider": "pexels",
            "url": photo["src"]["large"],
            "thumb": photo["src"]["medium"],
            "alt": photo.get("alt") or "",
            "credit": photo["photographer"],
            "credit_url": photo["photographer_url"],
        }
        for photo in data.get("photos", [])
    ]


async def _search_unsplash(client: httpx.AsyncClient, query: str, per_page: int) -> list[dict[str, Any]]:
    resp = await client.get(
        "https://api.unsplash.com/search/photos",
        params={"query": query, "per_page": per_page},
        headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "id": f"unsplash_{photo['id']}",
            "provider": "unsplash",
            "url": photo["urls"]["regular"],
            "thumb": photo["urls"]["thumb"],
            "alt": photo.get("alt_description") or "",
            "credit": photo["user"]["name"],
            "credit_url": photo["user"]["links"]["html"],
        }
        for photo in data.get("results", [])
    ]


@router.get("/images/search")
async def search_images(
    q: str = Query(..., min_length=1, max_length=200),
    per_page: int = Query(20, ge=1, le=40),
):
    """무료 스톡 이미지 검색 (Pexels + Unsplash 동시 조회).

    API 키가 설정되지 않은 provider는 자동으로 건너뛴다 — 둘 다 비어 있으면
    빈 결과를 반환하고 에디터는 업로드만으로 정상 동작한다(degrade, not error).
    """
    providers: list[tuple[str, Any]] = []
    if settings.PEXELS_API_KEY:
        providers.append(("pexels", _search_pexels))
    if settings.UNSPLASH_ACCESS_KEY:
        providers.append(("unsplash", _search_unsplash))

    if not providers:
        return {"results": []}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        outcomes = await asyncio.gather(
            *(fn(client, q, per_page) for _, fn in providers),
            return_exceptions=True,
        )

    results: list[dict[str, Any]] = []
    for (name, _), outcome in zip(providers, outcomes):
        if isinstance(outcome, Exception):
            logger.warning("이미지 검색 provider 실패: %s — %s", name, outcome)
            continue
        results.extend(outcome)

    return {"results": results}
