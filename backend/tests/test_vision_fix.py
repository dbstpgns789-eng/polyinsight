# -*- coding: utf-8 -*-
"""비전 자기수정 — 모델이 자기 카드의 '렌더 결과'를 보고 고친다.

왜 필요한가(실측 2026-07-12): 5편 전부 PI_SELFCHECK에 "전항 통과"라 자가신고했는데
저지는 5편 전부에서 결함을 찾았다. 모델은 자기 HTML이 어떻게 렌더되는지 볼 수 없다.
텍스트 체크리스트로는 원리적으로 못 잡는 결함(빈 공간·요소 겹침·형상 오독)이 남는다.
"""
import backend.agents.deck.vision_fix as V
from backend.agents.deck.vision_fix import apply_vision_fix

_HTML = ('<!DOCTYPE html><html><head><style>.x{}</style></head><body>'
         '<div data-screen-label="01" style="width:1080px">A</div>'
         '<div data-screen-label="02" style="width:1080px">B</div>'
         '</body></html>')
_FIXED = _HTML.replace(">A<", ">A-fixed<")


async def test_no_pngs_returns_original(monkeypatch):
    """렌더가 실패해 PNG가 없으면 원본을 그대로 — 수정 단계가 저작을 죽이면 안 된다(소프트)."""
    html, warns = await apply_vision_fix(_HTML, [])
    assert html == _HTML
    assert any("건너" in w for w in warns)


async def test_fix_replaces_html(monkeypatch):
    class _Fake:
        async def call(self, **kw):
            assert kw.get("images"), "카드 PNG가 모델에 전달돼야 한다"
            return _FIXED

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"png1", b"png2"])
    assert "A-fixed" in html
    assert warns == []


async def test_broken_output_falls_back_to_original(monkeypatch):
    """모델이 카드 없는 쓰레기를 뱉으면 원본 유지 — 멀쩡한 덱을 수정이 망가뜨리면 안 된다."""
    class _Fake:
        async def call(self, **kw):
            return "죄송합니다. 수정할 수 없습니다."

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"png"])
    assert html == _HTML
    assert any("무시" in w for w in warns)


async def test_card_count_drop_falls_back(monkeypatch):
    """카드가 줄어들면 거부 — 수정이 카드를 삼키는 사고를 막는다."""
    class _Fake:
        async def call(self, **kw):
            return ('<html><body><div data-screen-label="01">only one</div></body></html>')

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"p1", b"p2"])
    assert html == _HTML
    assert any("카드 수" in w for w in warns)


async def test_llm_failure_is_soft(monkeypatch):
    class _Fake:
        async def call(self, **kw):
            raise RuntimeError("api down")

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"p1"])
    assert html == _HTML
    assert any("실패" in w for w in warns)
