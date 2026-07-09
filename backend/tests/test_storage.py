"""Storage 창구 단위 테스트 — 파일시스템 라운드트립·원자성·안전성."""
from __future__ import annotations

import asyncio

import pytest

from backend.core import storage as storage_mod
from backend.core.config import settings


@pytest.fixture(autouse=True)
def tmp_storage(tmp_path, monkeypatch):
    # 무상태 접근자라 settings 라이브 read → 테스트별 tmp 격리.
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))


@pytest.mark.asyncio
async def test_put_get_roundtrip():
    s = storage_mod.get_storage()
    await s.put("jobs/j1/cards/1.png", b"\x89PNG-hello")
    assert await s.get("jobs/j1/cards/1.png") == b"\x89PNG-hello"


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    s = storage_mod.get_storage()
    assert await s.get("nope/missing.bin") is None


@pytest.mark.asyncio
async def test_delete_is_idempotent():
    s = storage_mod.get_storage()
    await s.put("a/b.bin", b"x")
    await s.delete("a/b.bin")
    await s.delete("a/b.bin")  # 두 번째도 예외 없이 통과
    assert await s.get("a/b.bin") is None


@pytest.mark.asyncio
async def test_delete_prefix_removes_subtree_only():
    s = storage_mod.get_storage()
    await s.put("jobs/j1/cards/1.png", b"a")
    await s.put("jobs/j1/exports/e.zip", b"b")
    await s.put("jobs/j2/cards/1.png", b"c")
    await s.delete_prefix("jobs/j1")
    assert await s.get("jobs/j1/cards/1.png") is None
    assert await s.get("jobs/j1/exports/e.zip") is None
    assert await s.get("jobs/j2/cards/1.png") == b"c"  # 다른 job은 무사


@pytest.mark.asyncio
async def test_concurrent_put_same_key_no_torn_file():
    # 원자적 쓰기(temp+os.replace)라 동시 put에도 온전한 한 파일만 남는다.
    s = storage_mod.get_storage()
    payloads = [bytes([i]) * 100_000 for i in range(1, 9)]
    await asyncio.gather(*(s.put("jobs/j/cards/1.png", p) for p in payloads))
    result = await s.get("jobs/j/cards/1.png")
    assert result in payloads          # 찢어진 혼합 바이트가 아니라 어느 하나의 완전본
    assert len(result) == 100_000


@pytest.mark.asyncio
async def test_key_traversal_blocked():
    s = storage_mod.get_storage()
    with pytest.raises(ValueError):
        await s.put("../escape.bin", b"x")
