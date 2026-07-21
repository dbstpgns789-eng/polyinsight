# -*- coding: utf-8 -*-
"""인스타 캡션 생성기 (Phase 0, 2026-07-21).

핵심 불변식: 캡션에 미확인 수치 0(fidelity 배관). 계약 { caption, hashtags }. IG 상한. lazy 캐시.
LLM은 mock — 배관(제약·상한·캐시·무효화)을 검증한다.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from backend.agents.deck import caption as capmod
from backend.core import db as _db
from backend.core.config import settings


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))
    monkeypatch.setattr(settings, "DEV_MOCK_LLM", False)
    await _db.migrate()
    yield


_DECK = (
    '<div data-screen-label="00">천연 셀룰로오스 구슬이 238 MPa로 플라스틱(199 MPa)을 넘어섰다. '
    'Ryu · Kim et al. · Cellulose (2024)</div>'
)
_PAPER = "cellulose beads reached 238 MPa, exceeding polypropylene at 199 MPa"


def _llm(caption: str, hashtags: list[str]) -> AsyncMock:
    return AsyncMock(return_value=json.dumps({"caption": caption, "hashtags": hashtags}, ensure_ascii=False))


# ── 계약 형태 ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_contract_shape():
    with patch.object(capmod.llm_client, "call", _llm("셀룰로오스가 238 MPa로 강해졌다. Ryu et al. (2024)", ["연구", "cellulose"])):
        r = await capmod.generate_caption(_DECK, _PAPER)
    assert isinstance(r["caption"], str) and r["caption"]
    assert isinstance(r["hashtags"], list)
    assert all(isinstance(t, str) for t in r["hashtags"])


# ── ★검증수치 제약 (해자) ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_verified_number_passes_through():
    """238은 덱 검증집합에 있으므로 캡션에 남는다."""
    with patch.object(capmod.llm_client, "call", _llm("셀룰로오스가 238 MPa를 기록했다. Ryu et al. (2024)", ["연구"])):
        r = await capmod.generate_caption(_DECK, _PAPER)
    assert "238" in r["caption"]


@pytest.mark.asyncio
async def test_unverified_number_triggers_numberless_regen():
    """★캡션이 덱에 없는 수치(예: 999)를 쓰면 → 수치 없는 캡션으로 재생성 → 미확인 수치 0."""
    call = AsyncMock(side_effect=[
        json.dumps({"caption": "무려 999배 강해졌다!", "hashtags": ["과장"]}, ensure_ascii=False),  # 위반
        json.dumps({"caption": "셀룰로오스 구슬이 크게 강해졌다. Ryu et al. (2024)", "hashtags": ["연구"]}, ensure_ascii=False),  # 수치없음
    ])
    with patch.object(capmod.llm_client, "call", call):
        r = await capmod.generate_caption(_DECK, _PAPER)
    assert call.call_count == 2                       # 재생성 발동
    from backend.core.fidelity import verified_number_strings, caption_numbers_ok
    ok, viol = caption_numbers_ok(r["caption"], verified_number_strings(_DECK, _PAPER))
    assert ok, f"미확인 수치 남음: {viol}"            # 최종 캡션엔 미확인 수치 0


# ── IG 상한 ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_hashtags_capped_at_30():
    many = [f"tag{i}" for i in range(50)]
    with patch.object(capmod.llm_client, "call", _llm("요약. Ryu et al. (2024)", many)):
        r = await capmod.generate_caption(_DECK, _PAPER)
    assert len(r["hashtags"]) <= 30


@pytest.mark.asyncio
async def test_combined_length_under_2200():
    """본문+해시태그 합산이 2200 넘으면 해시태그를 덜어낸다."""
    long_tags = [f"verylonghashtag{i}" for i in range(30)]
    body = "요약 " * 400                              # 긴 본문(~1600자)
    with patch.object(capmod.llm_client, "call", _llm(body, long_tags)):
        r = await capmod.generate_caption(_DECK, _PAPER)
    combined = r["caption"] + "\n\n" + " ".join(f"#{t}" for t in r["hashtags"])
    assert len(combined) <= capmod.IG_CAPTION_MAX


# ── LLM 출력 파싱 관대성 ───────────────────────────────────────────
@pytest.mark.asyncio
async def test_parses_json_in_code_fence():
    fenced = '```json\n{"caption": "요약. Ryu et al. (2024)", "hashtags": ["a", "b"]}\n```'
    with patch.object(capmod.llm_client, "call", AsyncMock(return_value=fenced)):
        r = await capmod.generate_caption(_DECK, _PAPER)
    assert r["caption"].startswith("요약")
    assert r["hashtags"] == ["a", "b"]


# ── 엔드포인트: lazy 캐시 + 편집 무효화 ────────────────────────────
@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from backend.core.auth import get_current_user
    from backend.main import app
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "t@t", "role": "user", "plan": "lab", "free_decks_used": 0}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_endpoint_lazy_generates_then_caches(client):
    await _db.create_job("j1", "p.pdf", user_id=1)
    await _db.save_authored_deck("j1", _DECK, "[]", 1, _PAPER)

    call = _llm("셀룰로오스 238 MPa. Ryu et al. (2024)", ["연구"])
    with patch.object(capmod.llm_client, "call", call):
        r1 = await client.get("/api/deck/j1/caption")
        r2 = await client.get("/api/deck/j1/caption")

    assert r1.status_code == 200 and "238" in r1.json()["caption"]
    assert r2.json() == r1.json()
    assert call.call_count == 1                        # ★두 번째는 캐시 — LLM 재호출 없음(비용 방어)


@pytest.mark.asyncio
async def test_edit_invalidates_caption_cache(client):
    await _db.create_job("j2", "p.pdf", user_id=1)
    await _db.save_authored_deck("j2", _DECK, "[]", 1, _PAPER)
    await _db.set_deck_caption("j2", json.dumps({"caption": "old", "hashtags": []}))

    # 편집(save_authored_deck 재호출) → 캡션 무효화돼야 한다
    await _db.save_authored_deck("j2", _DECK.replace("238", "240"), "[]", 1)
    deck = await _db.get_authored_deck("j2")
    assert deck["caption_json"] is None                # 편집이 낡은 캡션을 지웠다


@pytest.mark.asyncio
async def test_endpoint_not_export_gated_for_free_user(client):
    """무료 유저도 캡션 미리보기는 봐야 한다(아하) — 402가 아니어야."""
    from backend.core.auth import get_current_user
    from backend.main import app
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "t@t", "role": "user", "plan": "free", "free_decks_used": 1}
    await _db.create_job("j3", "p.pdf", user_id=1)
    await _db.save_authored_deck("j3", _DECK, "[]", 1, _PAPER)

    with patch.object(capmod.llm_client, "call", _llm("요약. Ryu et al. (2024)", ["연구"])):
        r = await client.get("/api/deck/j3/caption")
    assert r.status_code != 402
