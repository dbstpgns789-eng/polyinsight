"""행동 로깅(events) 테스트."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core.config import settings
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "events.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "RENDER_TOKEN", "")
    await _db.migrate()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_log_and_list_event():
    await _db.log_event("test_evt", user_id=7, job_id="j1", payload={"k": "v"})
    events = await _db.list_events()
    assert len(events) == 1
    assert events[0]["event_type"] == "test_evt"
    assert events[0]["user_id"] == 7
    assert events[0]["payload"] == {"k": "v"}


@pytest.mark.asyncio
async def test_login_records_event(client):
    from backend.core.auth import hash_password
    uid = await _db.create_user("ev@b.com", hash_password("password1"))
    await client.post("/api/auth/login", json={"email": "ev@b.com", "password": "password1"})
    events = await _db.list_events()
    assert any(e["event_type"] == "login" and e["user_id"] == uid for e in events)


@pytest.mark.asyncio
async def test_upload_records_event(client):
    from backend.core.auth import hash_password
    uid = await _db.create_user("up@b.com", hash_password("password1"))
    await client.post("/api/auth/login", json={"email": "up@b.com", "password": "password1"})
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        resp = await client.post(
            "/api/upload",
            files={"file": ("paper.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            data={"card_count": "5"},
        )
    assert resp.status_code == 202
    job_id = resp.json()["jobId"]
    events = await _db.list_events()
    upload_evts = [e for e in events if e["event_type"] == "upload"]
    assert len(upload_evts) == 1
    assert upload_evts[0]["user_id"] == uid
    assert upload_evts[0]["job_id"] == job_id
    assert upload_evts[0]["payload"]["card_count"] == 5


def test_usage_capture_accumulates():
    from backend.core.llm_client import _record_usage, get_usage, start_usage_capture
    start_usage_capture()
    _record_usage(100, 50)
    _record_usage(30, 20)
    usage = get_usage()
    assert usage["input_tokens"] == 130
    assert usage["output_tokens"] == 70
    assert usage["calls"] == 2
