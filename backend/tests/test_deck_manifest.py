# -*- coding: utf-8 -*-
"""PI_MANIFEST / PI_SELFCHECK 파싱 + 반복이력 소프트 주입."""
import pytest_asyncio

from backend.agents.deck.manifest import build_history_block, parse_manifest, selfcheck_failures
from backend.core import db
from backend.core.config import settings


@pytest_asyncio.fixture(autouse=True)
async def _isolated_db(tmp_path, monkeypatch):
    """각 테스트를 격리된 tmp DB로 실행(주변 polyinsight.db 오염 방지)."""
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'deck.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blobstore"))
    await db.migrate()
    yield

_HTML = ('<!DOCTYPE html><html><head>'
         '<!-- PI_MANIFEST {"archetype": "반전형", "killer_asset": "플라스틱보다 단단", '
         '"palette": "아이보리·세이지", "motif": "구슬", "rejected_arc": "데이터 클라이맥스형 — 수치가 약함"} -->'
         '<style></style></head><body></body></html>')


def test_parse_manifest_ok():
    m = parse_manifest(_HTML)
    assert m["archetype"] == "반전형"
    assert m["motif"] == "구슬"
    assert "rejected_arc" in m


def test_parse_manifest_absent_returns_none():
    assert parse_manifest("<!DOCTYPE html><html></html>") is None


def test_parse_manifest_broken_json_returns_none():
    assert parse_manifest('<!-- PI_MANIFEST {broken -->') is None


def test_history_block_empty_when_no_history():
    assert build_history_block([]) == ""


def test_history_block_soft_wording():
    block = build_history_block([
        {"archetype": "데이터 클라이맥스형", "palette": "아이보리", "motif": "구슬"},
        {"archetype": "반전형", "palette": "네이비", "motif": "그래프"},
    ])
    assert "데이터 클라이맥스형" in block
    assert "적합이 신선함을 이긴다" in block      # 소프트 선호 — 하드 금지가 아니다
    assert "금지" not in block.split("적합")[0]   # 하드 금지 표현 없음


def test_selfcheck_failures_lists_false_items():
    # 자기신고 의미론: placeholder/emoji는 true=결함, *_ok/no_*/*_matches는 false=결함
    html = ('<html><body></body>'
            '<!-- PI_SELFCHECK {"placeholder": false, "emoji": true, "derived_ok": false} -->'
            '</html>')
    fails = selfcheck_failures(html)
    assert "emoji" in fails and "derived_ok" in fails
    assert "placeholder" not in fails


def test_selfcheck_absent_returns_empty():
    assert selfcheck_failures("<html></html>") == []


async def test_manifest_history_roundtrip():
    """저장 → 최근 조회 → 주입 텍스트까지 실제 DB 라운드트립. eval 격리(삭제)도 함께 검증."""
    import json as _json

    uid = 9901
    for jid, arc in (("m-hist-1", "데이터 클라이맥스형"), ("m-hist-2", "반전형")):
        await db.delete_job(jid)
        await db.create_job(jid, title=f"{jid}.pdf", user_id=uid)
        await db.save_deck_manifest(jid, uid, _json.dumps(
            {"archetype": arc, "palette": "아이보리", "motif": "구슬"}, ensure_ascii=False))
    try:
        recent = await db.get_recent_manifests(uid, limit=3)
        assert len(recent) == 2
        block = build_history_block(recent)
        assert "반전형" in block and "데이터 클라이맥스형" in block

        await db.delete_deck_manifests(uid)        # eval 격리 — 이력 0에서 측정
        assert await db.get_recent_manifests(uid) == []
        assert build_history_block([]) == ""       # 이력 없으면 주입도 없음
    finally:
        for jid in ("m-hist-1", "m-hist-2"):
            await db.delete_job(jid)
