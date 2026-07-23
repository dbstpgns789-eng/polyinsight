# -*- coding: utf-8 -*-
"""save_authored_deck 경계 위생 (2026-07-23).

저작 모델은 [검사 산문 → ```html → 문서]를 뱉는다. strip이 최초 저작 한 곳뿐이라
편집·vision-fix 재저장이 우회 → 산문이 덱 HTML에 저장돼 편집기가 카드 위에 렌더(셀룰로오스 덱).
경계(save_authored_deck)에서 막는다. clean·조각엔 무해(멱등).
"""
import pytest
import pytest_asyncio

from backend.core import db as _db
from backend.core.config import settings


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))
    await _db.migrate()
    yield


_POLLUTED = (
    "비접근성·렌더 검사를 진행한다. 수정 대상: 04. 아래는 전문이다.\n\n```html\n"
    '<!DOCTYPE html>\n<html><body><div data-screen-label="00">카드</div></body></html>\n```'
)


@pytest.mark.asyncio
async def test_save_strips_prose_and_fence():
    """편집/vision-fix 재저장이 산문+펜스를 남겨도 경계에서 걷힌다."""
    await _db.create_job("j1", "p.pdf", user_id=1)
    await _db.save_authored_deck("j1", _POLLUTED, "[]", 1, paper_text="x")
    h = (await _db.get_authored_deck("j1"))["html"]
    assert h.lstrip().lower().startswith("<!doctype"), "산문이 안 걷힘"
    assert "```" not in h, "코드펜스가 안 걷힘"
    assert "비접근성" not in h, "프로즈가 남음"


@pytest.mark.asyncio
async def test_save_leaves_clean_html_untouched():
    """clean 문서는 손대지 않는다(멱등 — 매 저장마다 돌아도 안전)."""
    clean = '<!DOCTYPE html>\n<html><head><style>x</style></head><body><div>ok</div></body></html>'
    await _db.create_job("j2", "p.pdf", user_id=1)
    await _db.save_authored_deck("j2", clean, "[]", 1, paper_text="x")
    assert (await _db.get_authored_deck("j2"))["html"].strip() == clean.strip()
