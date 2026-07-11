# -*- coding: utf-8 -*-
"""V2 파생수치 검증 — 170% 사건(142→238=68% 증가를 '170% 증가'로 오기) 재발 방지."""
from backend.core.fidelity import derived_claims


def _card(body: str) -> str:
    return f'<div data-screen-label="01" style="width:1080px">{body}</div>'


def test_pct_fold_confusion_is_suspect():
    # 142→238은 1.68배 = 68% 증가. "170% 증가"는 배·%증가 혼동 → suspect
    html = _card("<p>142 MPa에서 238 MPa로 약 170% 증가</p>")
    claims = derived_claims(html, paper_text="142 199 238 MPa")
    assert len(claims) == 1
    assert claims[0]["kind"] == "pct_change"
    assert claims[0]["suspect"] is True


def test_correct_pct_change_not_suspect():
    html = _card("<p>142 MPa에서 238 MPa로 약 68% 증가</p>")
    claims = derived_claims(html, paper_text="142 238")
    assert claims[0]["suspect"] is False


def test_correct_fold_not_suspect():
    html = _card("<p>142에서 238로 약 1.7배 강해졌다</p>")
    claims = derived_claims(html, paper_text="142 238")
    assert claims[0]["kind"] == "fold"
    assert claims[0]["suspect"] is False


def test_no_derived_expressions_empty():
    html = _card("<p>압축강도 238 MPa를 기록했다</p>")
    assert derived_claims(html, paper_text="238") == []


def test_derived_scoped_per_card():
    # 파생표현과 근거수치가 다른 카드에 있으면 그 카드 안에서만 대조(전역 오염 방지)
    html = (_card("<p>강도 142 MPa와 238 MPa</p>")
            + '<div data-screen-label="02"><p>효율이 약 30% 증가</p></div>')
    claims = derived_claims(html, paper_text="142 238")
    # 30% 증가 카드에는 비교쌍이 없음 → 검산 불가 → suspect=False(모르면 죄 아님), unresolved=True
    assert claims[0]["suspect"] is False
    assert claims[0]["unresolved"] is True


def test_page_footer_does_not_launder_wrong_claim():
    # 프롬프트가 페이지번호(01/07)를 전 카드에 강제한다 → (1,7) 쌍이 검산에 끼면
    # 근거 없는 '7배' 주장이 '정합'으로 세탁된다(false negative). 페이지 패턴은 제외돼야 함.
    html = _card('<span>06 / 07</span><p>효율이 7배 향상됐다</p>')
    claims = derived_claims(html, paper_text="효율 향상")
    assert claims[0]["unresolved"] is True      # 비교쌍 없음 — 세탁 금지
    assert claims[0]["suspect"] is False


def test_year_pair_does_not_create_false_suspect():
    # 연도 2개(2020·2026)가 쌍이 되면 b/a*100≈100.3 → 정당한 '약 100% 향상'이 가짜 suspect가 된다.
    html = _card("<p>2020년 대비 2026년, 성능이 약 100% 향상</p>")
    claims = derived_claims(html, paper_text="2020 2026 성능 100% 향상")
    assert claims[0]["suspect"] is False
    assert claims[0]["unresolved"] is True      # 연도 제외 → 검산 불가
