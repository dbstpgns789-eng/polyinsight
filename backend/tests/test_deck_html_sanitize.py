# -*- coding: utf-8 -*-
"""저작·편집 출력 위생 — 모델의 수다가 덱에 박히면 안 된다.

실전 버그(2026-07-14, 사용자 제보):
  덱 094fe1e2의 HTML이 **모델의 검사 산문 796자**로 시작한다:
    "비접근성·렌더 검사를 진행한다. **1단계 (용어)** - 02: `0.1μm~5mm…`"
  편집기를 열면 그 산문이 카드 위에 그대로 렌더된다.

원인: `_strip_code_fence`는 출력이 ```로 **시작할 때만** 펜스를 벗긴다.
      모델이 [산문 → ```html → 문서] 순으로 뱉으면 산문도 펜스도 안 걷힌다.
      저작·편집(nl_patch) 두 경로가 같은 함수를 쓴다 — 편집은 라이브 경로다.
"""
from backend.agents.deck.authoring import _strip_code_fence

DOC = '<!DOCTYPE html>\n<html><body><div data-screen-label="01">카드</div></body></html>'


def test_plain_document_untouched():
    assert _strip_code_fence(DOC) == DOC


def test_leading_fence_stripped():
    assert _strip_code_fence(f"```html\n{DOC}\n```") == DOC


def test_prose_before_document_is_stripped():
    """★실전 버그: 모델이 자기 검사 과정을 먼저 서술하고 그 다음 문서를 뱉는다."""
    raw = (
        "비접근성·렌더 검사를 진행한다.\n\n"
        "**1단계 (용어)**\n- 02: `0.1μm~5mm` — 이미 앵커 있음. OK.\n\n"
        "수정 대상: **04, 05**. 아래는 수정한 전문이다.\n\n"
        f"```html\n{DOC}\n```"
    )
    out = _strip_code_fence(raw)
    assert out.startswith("<!DOCTYPE html>")
    assert "1단계" not in out
    assert "검사를 진행한다" not in out


def test_prose_without_fence_is_stripped():
    raw = f"수정했습니다. 아래가 결과입니다.\n\n{DOC}"
    out = _strip_code_fence(raw)
    assert out.startswith("<!DOCTYPE html>")
    assert "수정했습니다" not in out


def test_trailing_prose_is_stripped():
    raw = f"{DOC}\n\n이상입니다. 추가 수정이 필요하면 말씀해주세요."
    out = _strip_code_fence(raw)
    assert out.endswith("</html>")
    assert "이상입니다" not in out


def test_html_without_doctype_still_works():
    doc = '<html><body><div data-screen-label="01">카드</div></body></html>'
    assert _strip_code_fence(f"자, 여기 있습니다:\n\n{doc}").startswith("<html>")


def test_card_fragment_survives():
    """비전 국소 패치는 카드 조각만 온다 — 문서가 아니어도 버리면 안 된다."""
    frag = '<div data-screen-label="04">고친 카드</div>'
    assert _strip_code_fence(f"```html\n{frag}\n```") == frag
    assert _strip_code_fence(frag) == frag
