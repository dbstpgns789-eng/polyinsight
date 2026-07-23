"""크레딧 백엔드(B1) — DB 함수: 차감·각인·환불·충전. 스펙 2026-07-23-credit-backend-b1.

적대검증 반영: 환불근거를 jobs.charged_credits에 각인(재시작 복구 가능), 멱등 환불.
"""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from backend.core import db as _db
from backend.core.config import settings


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blobstore"))
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    await _db.migrate()
    yield


async def _mk_user(email: str = "c@test") -> int:
    return await _db.create_user(email, "hash")


# ── 스키마 ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_new_user_has_zero_credits():
    uid = await _mk_user()
    assert (await _db.get_user_by_id(uid))["credits"] == 0


@pytest.mark.asyncio
async def test_new_job_has_zero_charged_credits():
    uid = await _mk_user()
    await _db.create_job("j1", "t", uid)
    assert (await _db.get_job("j1"))["charged_credits"] == 0


# ── consume_credits (동기 작업 = AI 편집) ───────────────────────────
@pytest.mark.asyncio
async def test_consume_credits_deducts_when_sufficient():
    uid = await _mk_user()
    await _db.add_credits(uid, 10)
    assert await _db.consume_credits(uid, 2) is True
    assert await _db.get_credits(uid) == 8


@pytest.mark.asyncio
async def test_consume_credits_refuses_when_insufficient():
    uid = await _mk_user()
    await _db.add_credits(uid, 1)
    assert await _db.consume_credits(uid, 2) is False
    assert await _db.get_credits(uid) == 1


@pytest.mark.asyncio
async def test_consume_credits_rejects_nonpositive_cost():
    uid = await _mk_user()
    await _db.add_credits(uid, 10)
    assert await _db.consume_credits(uid, 0) is False
    assert await _db.consume_credits(uid, -5) is False
    assert await _db.get_credits(uid) == 10  # 음수 차감으로 잔액이 늘면 안 됨


@pytest.mark.asyncio
async def test_consume_credits_atomic_under_concurrency():
    """잔액이 1건만 되는데 동시 2건 → 정확히 하나만 성공(원자 UPDATE)."""
    uid = await _mk_user()
    await _db.add_credits(uid, 10)  # cost 10짜리 2건 중 하나만 가능
    r1, r2 = await asyncio.gather(_db.consume_credits(uid, 10), _db.consume_credits(uid, 10))
    assert sorted([r1, r2]) == [False, True]
    assert await _db.get_credits(uid) == 0


# ── consume_credits_for_job (덱 생성 = 차감+각인 원자) ───────────────
@pytest.mark.asyncio
async def test_consume_for_job_deducts_and_stamps():
    uid = await _mk_user()
    await _db.add_credits(uid, 10)
    await _db.create_job("jc", "t", uid)
    assert await _db.consume_credits_for_job(uid, "jc", 10) is True
    assert await _db.get_credits(uid) == 0
    assert (await _db.get_job("jc"))["charged_credits"] == 10  # 각인됨


@pytest.mark.asyncio
async def test_consume_for_job_insufficient_leaves_both_unchanged():
    uid = await _mk_user()
    await _db.add_credits(uid, 5)
    await _db.create_job("jc", "t", uid)
    assert await _db.consume_credits_for_job(uid, "jc", 10) is False
    assert await _db.get_credits(uid) == 5                      # 불변
    assert (await _db.get_job("jc"))["charged_credits"] == 0    # 각인 안 됨(롤백)


# ── refund_job_credits (멱등) ───────────────────────────────────────
@pytest.mark.asyncio
async def test_refund_job_credits_restores_and_clears_stamp():
    uid = await _mk_user()
    await _db.add_credits(uid, 10)
    await _db.create_job("jr", "t", uid)
    await _db.consume_credits_for_job(uid, "jr", 10)
    await _db.refund_job_credits("jr")
    assert await _db.get_credits(uid) == 10                     # 복구
    assert (await _db.get_job("jr"))["charged_credits"] == 0    # 각인 소거


@pytest.mark.asyncio
async def test_refund_job_credits_is_idempotent():
    """두 진입점(_log_done·recover_stale_jobs)이 겹쳐도 1회만 환불(§13-①)."""
    uid = await _mk_user()
    await _db.add_credits(uid, 10)
    await _db.create_job("jr", "t", uid)
    await _db.consume_credits_for_job(uid, "jr", 10)
    await _db.refund_job_credits("jr")
    await _db.refund_job_credits("jr")   # 2회째는 no-op
    assert await _db.get_credits(uid) == 10  # 20이 되면 이중환불 버그


@pytest.mark.asyncio
async def test_refund_job_with_no_charge_is_noop():
    uid = await _mk_user()
    await _db.add_credits(uid, 10)
    await _db.create_job("jf", "t", uid)   # 각인 0(무료/면제 잡)
    await _db.refund_job_credits("jf")
    assert await _db.get_credits(uid) == 10


# ── add_credits (충전) ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_add_credits_adds_and_promotes_to_pro():
    uid = await _mk_user()
    await _db.add_credits(uid, 100)
    user = await _db.get_user_by_id(uid)
    assert user["credits"] == 100
    assert user["plan"] == "pro"   # 충전 = 유료 승격


@pytest.mark.asyncio
async def test_add_credits_nonpositive_is_noop():
    uid = await _mk_user()
    await _db.add_credits(uid, -50)
    user = await _db.get_user_by_id(uid)
    assert user["credits"] == 0
    assert user["plan"] == "free"  # 음수 충전이 plan을 승격시키면 안 됨


@pytest.mark.asyncio
async def test_add_credits_does_not_demote_lab():
    uid = await _mk_user("lab@test")
    await _db.set_plan(uid, "lab")
    await _db.add_credits(uid, 100)
    user = await _db.get_user_by_id(uid)
    assert user["plan"] == "lab"    # 면제 유지(pro로 강등 금지)
    assert user["credits"] == 100


# ── get_credits ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_credits_zero_for_missing_user():
    assert await _db.get_credits(999999) == 0
