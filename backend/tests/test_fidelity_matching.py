# -*- coding: utf-8 -*-
"""V1 대조 계층 — 추출·정규화·수치동등 비교 (스펙 2026-07-20).

배경: 기존 대조는 `core in paper_text` 라는 정규화 없는 substring이었다.
관대해야 할 곳(단위 환산·반올림)에 엄격하고, 엄격해야 할 곳(작은 정수)에 관대했다.
  - 오탐: 0.0001mm ↔ 100nm, 1.63 ↔ 1.626, 99.7% ← 100−0.32
  - 미탐: "5배" 주장이 원문 아무 곳의 "5"에 걸려 통과

허용오차 원칙: **카드가 화면에 보여준 자릿수**가 밴드를 정한다.
  tol = 0.5 × 10^(-표시 소수자리)   "1.63" → [1.625, 1.635)
카드뉴스는 논문의 전사가 아니라 대중화 산출물이므로 이 관대함이 올바른 레지스터다.
"""
from backend.core.fidelity import verify_deck, compute_verify_unverified


def _card(*texts: str) -> str:
    return "".join(f'<div data-screen-label="{i:02d}">{t}</div>' for i, t in enumerate(texts))


def _unverified(html: str, paper: str) -> set[str]:
    return {c.value for c in verify_deck(html, paper) if not c.verified}


def _flagged(html: str, paper: str, needle: str) -> bool:
    """'확인 필요'로 잡힌 claim 중 이 수치를 담은 게 있나.

    claim 토큰엔 단위가 붙는다(63.66 → '63.66 μg/cm²'). 토큰 형태가 아니라
    동작을 검증하려고 포함 비교를 쓴다.
    """
    return any(needle in v for v in _unverified(html, paper))


# ── 단위 환산 ─────────────────────────────────────────────────────
def test_unit_conversion_mm_to_nm():
    """★실측 오탐: 카드가 일반 독자용으로 mm 환산했는데 원문은 nm. 같은 값이다."""
    html = _card("마이크로비드는 0.0001mm~5mm 크기다")
    paper = "microbeads ranging from 100 nm to 5 mm in diameter"
    assert not _flagged(html, paper, "0.0001mm")


def test_unit_conversion_um_to_nm():
    html = _card("입자 크기 0.5μm")
    paper = "particle size of 500 nm"
    assert not _flagged(html, paper, "0.5")


def test_unit_conversion_mpa_to_gpa():
    html = _card("탄성률 1.2GPa")
    paper = "modulus of 1200 MPa"
    assert not _flagged(html, paper, "1.2")


def test_different_dimension_does_not_match():
    """★차원 대조 = 새 방어선. 질량 주장이 압력 수치로 검증되면 안 된다."""
    html = _card("흡착량 238 mg")
    paper = "compressive strength of 238 MPa"
    assert _flagged(html, paper, "238")


# ── 반올림 (표시 정밀도 밴드) ─────────────────────────────────────
def test_rounding_within_displayed_precision():
    """★실측 오탐: 원문 1.626 ± 0.16 → 카드 1.63."""
    html = _card("흡착량이 1.63 μg/cm² 였다")
    paper = "adsorption of 1.626 ± 0.16 μg/cm2"
    assert not _flagged(html, paper, "1.63")


def test_rounding_two_decimals():
    html = _card("정확도 27.9%")
    paper = "accuracy of 27.88%"
    assert not _flagged(html, paper, "27.9")


def test_rounding_outside_band_still_flagged():
    """과잉 관대 금지 — 1.70은 1.63 밴드[1.625,1.635) 밖이다."""
    html = _card("흡착량이 1.63 μg/cm² 였다")
    paper = "adsorption of 1.70 μg/cm2"
    assert _flagged(html, paper, "1.63")


def test_integer_precision_band_is_tight():
    """정수 표시(238)는 밴드가 ±0.5 — 250이 근거가 되면 안 된다."""
    html = _card("강도 238 MPa")
    paper = "strength of 250 MPa"
    assert _flagged(html, paper, "238")


# ── 파생: 여집합 ──────────────────────────────────────────────────
def test_complement_derivation():
    """★실측 오탐: 0.32 wt% 섞었으니 나머지 99.7%(=100−0.32)는 원재료.
    같은 카드 안의 0.32에서 유도되므로 근거 있는 수치다."""
    html = _card("섞은 양은 겨우 0.32 wt%, 구슬의 99.7%는 여전히 셀룰로오스")
    paper = "0.32 wt% of covalent organic nanosheets were incorporated"
    assert not _flagged(html, paper, "99.7")


def test_complement_requires_same_card():
    """덱 전역 유도 금지 — 다른 카드의 0.32로 99.7%를 정당화하면 안 된다."""
    html = _card("혼합 비율은 0.32 wt%", "구슬의 99.7%는 셀룰로오스")
    paper = "0.32 wt% of nanosheets"
    assert _flagged(html, paper, "99.7")


# ── ★미탐 차단 (substring 시절의 구조적 구멍) ──────────────────────
def test_bare_small_number_does_not_match_anything():
    """★substring 시절: '5배'의 core '5'가 원문 아무 곳의 5에 걸려 통과했다.
    근거 없는 주장이 배지를 다는 게 오탐보다 해자에 더 치명적이다."""
    html = _card("흡착 성능이 5배 향상됐다")
    paper = "we tested 5 different samples over 5 days at pH 5"
    assert _flagged(html, paper, "5배")


# ── ★★정탐 유지 (해자 붕괴 감지) ─────────────────────────────────
def test_ai_added_analogy_still_flagged():
    """★수용기준: AI가 독자 이해용으로 더한 비유값(꿀 점도)은 계속 잡혀야 한다.
    이게 VERIFIED로 바뀌면 검증기가 도장 찍는 기계가 된 것이다."""
    html = _card("cP = 점도 단위. 물은 약 1, 꿀은 약 10,000. 8160 cP")
    paper = "the solution viscosity was 8160 cP at room temperature"
    assert _flagged(html, paper, "10,000")


def test_absent_measurement_still_flagged():
    """★수용기준: 원문에 없는 측정값(63.66)은 실제 오류일 수 있다. 계속 잡혀야 한다."""
    html = _card("껍질 구슬 63.66 μg/cm² 흡수")
    paper = "adsorption values were 20.847, 24.163 and 18.467 μg/cm2"
    assert _flagged(html, paper, "63.66")


# ── 기존 자산 회귀 (스펙 §4) ──────────────────────────────────────
def test_comma_formatted_paper_number_matches():
    """원문이 콤마 표기여도 매칭돼야 한다(substring 시절 실패하던 조합)."""
    html = _card("학습 토큰 3000억 개")
    paper = "trained on 300 billion tokens"
    assert not _flagged(html, paper, "3000억")


def test_scientific_notation_still_matches():
    html = _card("총 연산 3,640 PF-days")
    paper = "GPT-3 175B  3.64E+03 PF-days"
    assert not _flagged(html, paper, "3,640")


def test_clean_deck_has_zero_unverified():
    """정상 덱은 '확인 필요 0'이어야 발행을 방해하지 않는다."""
    html = _card("강도 238 MPa로 199 MPa인 플라스틱을 넘어섰다")
    paper = "cellulose beads reached 238 MPa, exceeding polypropylene at 199 MPa"
    assert compute_verify_unverified(html, paper) == 0
