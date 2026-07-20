# -*- coding: utf-8 -*-
"""V1 오탐 제거 (A1, 2026-07-15).

배경: 클로드 디자인 GPT-3 덱(수치 전부 정확)에 우리 검증기를 돌리니 미확인 5개.
전부 오탐이었고 발행 버튼 앞 "⚠ 확인 필요 N개"로 발행을 방해했다.
프롬프트는 "한국어로 자연스럽게 써라"라 하고 검증기는 그걸 벌준다 — 서로 배신.

네 부류:
  A. 서지 식별자(arXiv ID·DOI) — claim 아님
  B. 한국어 만/억 표기 — 정확한 값인데 원문은 영어/과학표기
  C. 파생값(1.7배) — V2가 산수로 확인하는 값을 V1이 겹쳐서 flag
  D. 과학표기 재표현(3,640 ← 3.64E+03)

2026-07-20 실측 추가 (덱 19개·claim 232건 전수 분석, 미확인 11건 중 ~7건이 오탐):
  E. HTML 주석 누출 — 주석 속 '->'의 '>'가 태그 정규식을 조기 종료시켜
     레이아웃 수치(막대 너비 83.6%)가 콘텐츠로 샌다. 원문에 있을 수 없는 유령 claim.
  F. 연도 오분류 — _UNIT에 '년'이 있어 '2017년'이 claim이 된다. 정작 맨정수 '2017'은
     정상 제외된다(★핵심 설계 2). 한국어 단위가 자기 서지 필터를 무력화한 사례.
"""
from backend.core.fidelity import verify_deck, compute_verify_unverified, derived_claims


def _card(*texts: str) -> str:
    return "".join(f'<div data-screen-label="{i:02d}">{t}</div>' for i, t in enumerate(texts))


# ── A. 서지 식별자 ────────────────────────────────────────────────
def test_arxiv_id_is_not_a_claim():
    html = _card("이 논문은 arXiv:2005.14165 입니다. 정확도 92.6%.")
    vals = {c.value for c in verify_deck(html, "정확도 92.6")}
    assert "2005.14165" not in vals
    assert "2009.03300" not in {c.value for c in verify_deck(_card("arXiv:2009.03300"), "")}


def test_doi_is_not_a_claim():
    html = _card("doi:10.1234/abcd.5678 참조")
    vals = {c.value for c in verify_deck(html, "")}
    assert not any("10.1234" in v for v in vals)


# ── B. 한국어 만/억 표기 ──────────────────────────────────────────
def test_korean_eok_matches_english_billion():
    # 1,750억 = 175 billion. 원문은 영어.
    html = _card("파라미터 1,750억 개짜리 모델")
    paper = "an autoregressive language model with 175 billion parameters"
    unv = [c for c in verify_deck(html, paper) if not c.verified]
    assert "1,750억" not in {c.value for c in unv}


def test_korean_eok_300():
    html = _card("훈련에 쓴 단어 3,000억 개")
    paper = "trained for a total of 300 billion tokens"
    unv = {c.value for c in verify_deck(html, paper) if not c.verified}
    assert "3,000억" not in unv


def test_korean_eok_no_false_match():
    # 원문에 175도 300도 없으면 여전히 미확인이어야 한다(과잉 억제 금지)
    html = _card("파라미터 9,999억 개")
    paper = "the model has some parameters"
    unv = {c.value for c in verify_deck(html, paper) if not c.verified}
    assert "9,999억" in unv


# ── C. 파생값(V2 확인) ────────────────────────────────────────────
def test_v2_confirmed_derived_not_counted_unverified():
    # 142→238 = 1.7배. V2가 산수로 확인 → V1이 "1.7 원문에 없음"으로 겹쳐 세면 안 된다.
    html = _card("강도가 142에서 238로, 1.7배 올랐다")
    paper = "strength increased from 142 to 238 MPa"
    assert compute_verify_unverified(html, paper) == 0


def test_wrong_derived_still_flagged_as_suspect():
    # 틀린 파생값(142→238인데 3배)은 V2 suspect(계산 불일치)로 잡힌다 — 오탐 억제가 이걸 가리면 안 된다.
    html = _card("강도가 142에서 238로, 3배 올랐다")
    paper = "strength increased from 142 to 238 MPa"
    suspects = [d for d in derived_claims(html, paper) if d["suspect"]]
    assert any("3배" in d["value"] for d in suspects)


# ── D. 과학표기 재표현 ────────────────────────────────────────────
def test_scientific_notation_in_paper_matches_plain():
    # 카드 "3,640" ← 원문 "3.64E+03"
    html = _card("총 연산 3,640 PF-days")
    paper = "GPT-3 175B  3.64E+03 PF-days  3.14E+23 flops"
    unv = {c.value for c in verify_deck(html, paper) if not c.verified}
    assert not any("3,640" in v for v in unv)


# ── E. HTML 주석 누출 ─────────────────────────────────────────────
def test_html_comment_with_arrow_does_not_leak_numbers():
    """★실측: <!-- PP 199 -> 83.6% --> 의 '->'가 <[^>]+> 를 조기 종료시켜
    막대그래프 너비(83.6%)가 콘텐츠 텍스트로 샜다. 레이아웃 값은 주장이 아니다."""
    html = _card('<!-- PP 199 -> 83.6% --><p>셀룰로오스 구슬 238 MPa</p>')
    vals = {c.value for c in verify_deck(html, "cellulose beads 238 MPa")}
    assert "83.6%" not in vals
    assert any("238" in v for v in vals)      # 진짜 수치는 그대로 잡혀야 한다


def test_plain_html_comment_also_stripped():
    html = _card('<!-- 디자인 메모: 여백 12% --><p>수율 88%</p>')
    vals = {c.value for c in verify_deck(html, "yield 88%")}
    assert "12%" not in vals


def test_comment_leak_does_not_inflate_unverified_count():
    html = _card('<!-- bar 199 -> 59.7% --><p>강도 199 MPa</p>')
    assert compute_verify_unverified(html, "strength 199 MPa") == 0


# ── F. 연도 오분류 ────────────────────────────────────────────────
def test_korean_year_is_not_a_claim():
    """'2017년'은 서지·시점 표기지 정량 주장이 아니다. 맨정수 '2017'은 이미 제외되는데
    '년'이 단위 목록에 있어서 한국어 표기만 필터를 뚫었다."""
    html = _card("2017년에 제안된 구조가 오늘의 AI를 만들었다")
    vals = {c.value for c in verify_deck(html, "proposed in 2017")}
    assert "2017년" not in vals


def test_korean_duration_is_still_a_claim():
    """과잉 억제 금지 — 기간 '3년'은 정당한 정량 수치다(연도가 아니다)."""
    html = _card("3년간 추적 관찰했다")
    vals = {c.value for c in verify_deck(html, "followed for 3 years")}
    assert "3년" in vals


def test_bare_year_still_excluded():
    html = _card("2017 Vaswani et al.")
    assert "2017" not in {c.value for c in verify_deck(html, "")}
