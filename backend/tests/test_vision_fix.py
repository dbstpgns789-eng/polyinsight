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


async def test_only_patched_card_is_replaced(monkeypatch):
    """★국소 패치 계약: 고친 카드만 출력 → 그 카드만 교체, 나머지는 그대로.

    (전체 HTML 재출력이 최대 원가 드라이버였다 — 출력 15~18k 토큰 × $25/M.
     실제 덱 5개로 무손실 교체를 검증하고 전환했다.)
    """
    class _Fake:
        async def call(self, **kw):
            return '<div data-screen-label="01" style="width:1080px">A-fixed</div>'

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"p1", b"p2"])
    assert "A-fixed" in html
    assert 'data-screen-label="02"' in html and ">B<" in html    # 손 안 댄 카드 보존
    assert html.count("data-screen-label") == 2                  # 카드 수 불변
    assert warns == []


async def test_unknown_card_label_is_rejected(monkeypatch):
    """모델이 원본에 없는 카드를 만들면 무시 — 카드를 새로 만들 권한은 없다."""
    class _Fake:
        async def call(self, **kw):
            return '<div data-screen-label="09">유령 카드</div>'

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"p1"])
    assert html == _HTML
    assert "유령" not in html
    assert any("09" in w for w in warns)


async def test_no_changes_marker_converges(monkeypatch):
    """고칠 게 없으면 NO_CHANGES → 원본 유지 + 루프 조기 종료."""
    class _Fake:
        async def call(self, **kw):
            return "NO_CHANGES"

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"p1"])
    assert html == _HTML
    assert warns == []


async def test_number_change_is_rejected(monkeypatch):
    """★수치 불변 — 비전 수정은 표현을 고치는 단계지 사실을 바꾸는 단계가 아니다.

    프롬프트로 "수치를 바꾸지 마라"고 말해도 지켜진다는 보장이 없다(실측: L4 자가검수는 5/5 무력).
    코드가 확인한다. 레이아웃을 예쁘게 만드느라 238 MPa가 사라지면 그건 수정이 아니라 왜곡이다.
    """
    src = ('<div data-screen-label="01">압축강도 238 MPa</div>\n'
           '<div data-screen-label="02">0.32 wt%</div>')

    class _Fake:
        async def call(self, **kw):   # 카드 01만 출력하되 238 → 240으로 조작
            return '<div data-screen-label="01">압축강도 240 MPa</div>'

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(src, [b"p"])
    assert html == src                      # 원본 유지
    assert any("수치" in w for w in warns)


async def test_wording_fix_is_allowed(monkeypatch):
    """수치를 지키면서 용어를 쉽게 푸는 것은 허용 — 그게 이 단계의 목적이다."""
    src = '<div data-screen-label="01">약 100nm 크기</div>'
    better = '<div data-screen-label="01">약 100nm — 머리카락 굵기의 천분의 일 크기</div>'

    class _Fake:
        async def call(self, **kw):
            return better

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(src, [b"p"])
    assert html == better
    assert warns == []


async def test_round2_prompt_tells_model_it_is_reviewing_own_fix(monkeypatch):
    """2라운드는 '당신이 방금 수정한 결과'임을 알려야 한다 — 수정이 만든 새 결함을 잡기 위해.

    실측(2026-07-13): 1패스만 돌리자 접근성 수정으로 텍스트가 길어져 제목과 수치가 겹쳤다
    (finish 4→1). 수정 후 렌더를 다시 보지 않으면 루프가 아니라 그냥 1패스다.
    """
    seen = {}

    class _Fake:
        async def call(self, **kw):
            seen["prompt"] = kw["user_prompt"]
            return _HTML

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    await apply_vision_fix(_HTML, [b"p"], round_no=2)
    assert "방금 수정한 결과" in seen["prompt"]
    assert "억지로 더 고치지 마라" in seen["prompt"]


async def test_llm_failure_is_soft(monkeypatch):
    class _Fake:
        async def call(self, **kw):
            raise RuntimeError("api down")

    monkeypatch.setattr(V, "LLMClient", lambda: _Fake())
    html, warns = await apply_vision_fix(_HTML, [b"p1"])
    assert html == _HTML
    assert any("실패" in w for w in warns)
