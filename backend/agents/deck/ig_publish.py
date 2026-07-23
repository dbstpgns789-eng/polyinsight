"""Instagram 캐러셀 발행 (2026-07-23, graph.instagram.com).
공개 URL 리스트 + 캡션 → 게시글 permalink. 실패는 예외로 표면화(호출자가 크레딧 미차감).

★M1: GET(상태폴링·permalink)은 토큰을 Bearer 헤더로(URL·로그 유출 방지). POST는 body라 안전.
★M2: 성공 경계 = media_publish. 그 뒤 permalink GET은 best-effort — 실패해도 예외 안 냄
      (이미 게시됐는데 permalink 실패로 502→재클릭→중복게시 방지). 실패 시 None 반환.
★m1: 카드 1장이면 캐러셀(children 2~10 필수) 대신 단일 이미지 발행."""
from __future__ import annotations

import asyncio

import httpx

_G = "https://graph.instagram.com"
_POLL_MAX = 10
_POLL_INTERVAL_S = 2.0


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _wait_finished(client: httpx.AsyncClient, container_id: str, token: str) -> None:
    for _ in range(_POLL_MAX):
        s = await client.get(f"{_G}/{container_id}",
                             params={"fields": "status_code"}, headers=_bearer(token))
        s.raise_for_status()
        if s.json().get("status_code") == "FINISHED":
            return
        await asyncio.sleep(_POLL_INTERVAL_S)
    raise RuntimeError("container not FINISHED after polling")


async def _permalink(client: httpx.AsyncClient, media_id: str, token: str) -> str | None:
    """M2: 발행 성공 뒤 best-effort. 실패해도 None(예외 X) — 중복게시 방지."""
    try:
        pl = await client.get(f"{_G}/{media_id}",
                             params={"fields": "permalink"}, headers=_bearer(token))
        pl.raise_for_status()
        return pl.json().get("permalink")
    except Exception:
        return None


async def _publish_single(client: httpx.AsyncClient, ig_user_id: str, token: str,
                          image_url: str, caption: str) -> str | None:
    r = await client.post(f"{_G}/{ig_user_id}/media", data={
        "image_url": image_url, "caption": caption, "access_token": token})
    r.raise_for_status()
    container_id = r.json()["id"]
    await _wait_finished(client, container_id, token)
    p = await client.post(f"{_G}/{ig_user_id}/media_publish", data={
        "creation_id": container_id, "access_token": token})
    p.raise_for_status()
    return await _permalink(client, p.json()["id"], token)


async def publish_carousel(ig_user_id: str, access_token: str,
                           image_urls: list[str], caption: str) -> str | None:
    """카드 PNG 공개URL 리스트 → 게시. 성공 시 permalink(또는 None). media_publish까지 실패 시 예외."""
    async with httpx.AsyncClient(timeout=30) as client:
        if len(image_urls) == 1:                      # m1: 단일 카드
            return await _publish_single(client, ig_user_id, access_token, image_urls[0], caption)
        # 1) item 컨테이너
        child_ids: list[str] = []
        for url in image_urls:
            r = await client.post(f"{_G}/{ig_user_id}/media", data={
                "image_url": url, "is_carousel_item": "true", "access_token": access_token})
            r.raise_for_status()
            child_ids.append(r.json()["id"])
        # 2) 캐러셀 컨테이너
        r = await client.post(f"{_G}/{ig_user_id}/media", data={
            "media_type": "CAROUSEL", "children": ",".join(child_ids),
            "caption": caption, "access_token": access_token})
        r.raise_for_status()
        container_id = r.json()["id"]
        # 3) 준비 폴링
        await _wait_finished(client, container_id, access_token)
        # 4) 발행 (성공 경계)
        p = await client.post(f"{_G}/{ig_user_id}/media_publish", data={
            "creation_id": container_id, "access_token": access_token})
        p.raise_for_status()
        # 5) permalink best-effort
        return await _permalink(client, p.json()["id"], access_token)
