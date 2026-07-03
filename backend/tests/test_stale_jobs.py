"""stale-job 회수 스윕 + busy_timeout 테스트.

서버 재시작 시 이전 프로세스의 PENDING/RUNNING 잡은 영원히 고아로 남는다.
recover_stale_jobs()가 startup에서 이들을 ERROR로 회수하는지 검증.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from backend.core import db as _db
from backend.core.config import settings


@pytest_asyncio.fixture(autouse=True)
async def use_tmp_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    await _db.migrate()


@pytest.mark.asyncio
async def test_recover_stale_jobs_marks_pending_and_running_as_error():
    await _db.create_job("j-pending", "고아1")
    await _db.create_job("j-running", "고아2")
    await _db.update_job("j-running", status="RUNNING", stage="S6")

    recovered = await _db.recover_stale_jobs()

    assert recovered == 2
    for job_id in ("j-pending", "j-running"):
        job = await _db.get_job(job_id)
        assert job["status"] == "ERROR"
        assert any("재시작" in w for w in job["warnings"])


@pytest.mark.asyncio
async def test_recover_stale_jobs_leaves_done_and_error_untouched():
    await _db.create_job("j-done", "완료")
    await _db.update_job("j-done", status="DONE", warnings=["기존경고"])
    await _db.create_job("j-error", "실패")
    await _db.update_job("j-error", status="ERROR")

    recovered = await _db.recover_stale_jobs()

    assert recovered == 0
    done = await _db.get_job("j-done")
    assert done["status"] == "DONE"
    assert done["warnings"] == ["기존경고"]
    assert (await _db.get_job("j-error"))["status"] == "ERROR"


@pytest.mark.asyncio
async def test_connect_applies_busy_timeout():
    async with _db._connect() as conn:
        async with conn.execute("PRAGMA busy_timeout") as cursor:
            row = await cursor.fetchone()
    assert row[0] == 5000
