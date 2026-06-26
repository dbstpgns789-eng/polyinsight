"""GET /api/images/search — 스톡 이미지 검색 프록시 테스트.

외부 API(Pexels/Unsplash)는 _search_pexels/_search_unsplash 경계에서 mock —
실제 HTTP 호출 없이 오케스트레이션(키 없음 skip, provider 실패 격리, 병합)만 검증.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def use_memory_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    await _db.migrate()
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "test@test", "role": "user"}
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_search_without_any_key_returns_empty(client, monkeypatch):
    monkeypatch.setattr(settings, "PEXELS_API_KEY", "")
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "")

    resp = await client.get("/api/images/search", params={"q": "cellulose"})

    assert resp.status_code == 200
    assert resp.json() == {"results": []}


@pytest.mark.asyncio
async def test_search_merges_both_providers(client, monkeypatch):
    monkeypatch.setattr(settings, "PEXELS_API_KEY", "fake-pexels-key")
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "fake-unsplash-key")

    pexels_result = [{"id": "pexels_1", "provider": "pexels", "url": "u1", "thumb": "t1", "alt": "", "credit": "A", "credit_url": "a"}]
    unsplash_result = [{"id": "unsplash_1", "provider": "unsplash", "url": "u2", "thumb": "t2", "alt": "", "credit": "B", "credit_url": "b"}]

    with patch("backend.routers.images._search_pexels", new=AsyncMock(return_value=pexels_result)), \
         patch("backend.routers.images._search_unsplash", new=AsyncMock(return_value=unsplash_result)):
        resp = await client.get("/api/images/search", params={"q": "cellulose"})

    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()["results"]}
    assert ids == {"pexels_1", "unsplash_1"}


@pytest.mark.asyncio
async def test_search_isolates_single_provider_failure(client, monkeypatch):
    monkeypatch.setattr(settings, "PEXELS_API_KEY", "fake-pexels-key")
    monkeypatch.setattr(settings, "UNSPLASH_ACCESS_KEY", "fake-unsplash-key")

    unsplash_result = [{"id": "unsplash_1", "provider": "unsplash", "url": "u2", "thumb": "t2", "alt": "", "credit": "B", "credit_url": "b"}]

    with patch("backend.routers.images._search_pexels", new=AsyncMock(side_effect=RuntimeError("rate limited"))), \
         patch("backend.routers.images._search_unsplash", new=AsyncMock(return_value=unsplash_result)):
        resp = await client.get("/api/images/search", params={"q": "cellulose"})

    assert resp.status_code == 200
    assert resp.json() == {"results": unsplash_result}


@pytest.mark.asyncio
async def test_search_requires_query_param(client):
    resp = await client.get("/api/images/search")
    assert resp.status_code == 422
