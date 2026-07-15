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


def test_source_paper_error_is_still_suspect():
    """★원문이 틀렸어도 suspect다 — 우리 채널로 오류를 전파하지 않는다.

    실측(2026-07-13): Cellulose 2024 논문 원문에 "142 → 238 MPa, an increase of approximately
    170%"라고 쓰여 있다(저자 오기 — 실제로는 68% 증가). V1(존재 대조)은 "170이 원문에 있다"며
    통과시킨다. V2는 카드 안 수치쌍과 검산해 **원문 저자의 산수 오류까지** 잡아야 한다.
    (이것이 '원문 추적 가능 ≠ 참'인 유일한 지점이고, 코드 검증이 유일한 방어선이다.)
    """
    html = _card("<p>CON 첨가로 강도 142 → 238 MPa, 원문 표현: 약 170% 증가</p>")
    claims = derived_claims(html, paper_text="an increase of approximately 170% (142 to 238 MPa)")
    pct = [c for c in claims if c["kind"] == "pct_change"][0]
    assert pct["verified"] is True      # 원문에 '170'이 실재한다(V1은 통과시킨다)
    assert pct["suspect"] is True       # 그러나 산수는 틀렸다 — V2가 잡는다


def test_mismatch_when_pair_exists_but_ratio_wrong():
    """실전 오류(2026-07-12 chitosan): 카드에 1.63→63.66이 있는데 '32.7배'라 씀(실제 39배).

    구 로직은 '어떤 쌍과도 안 맞으면 unresolved(모름)'이라 이걸 놓쳤다.
    쌍이 있는데 값이 틀린 것은 '모름'이 아니라 '오산'이다.
    """
    html = _card("<p>1.63 에서 63.66 μg/cm² 으로, 껍질을 입히니 32.7배 늘었다</p>")
    claims = derived_claims(html, paper_text="1.63 63.66")
    fold = [c for c in claims if c["kind"] == "fold"][0]
    assert fold["suspect"] is True
    assert fold["unresolved"] is False


def test_unrelated_numbers_stay_unresolved():
    """관련 쌍이 없으면(스케일이 전혀 다르면) 여전히 unresolved — 모르면 죄 아님."""
    html = _card("<p>실험은 24시간, pH 5.5 조건. 흡수량이 32.7배 늘었다</p>")
    claims = derived_claims(html, paper_text="24 5.5")
    fold = [c for c in claims if c["kind"] == "fold"][0]
    assert fold["unresolved"] is True
    assert fold["suspect"] is False


def test_pct_point_diff_tolerates_rounding():
    """'2.8% 더 정확' + 차트 표시 27.9/25.0(반올림) → 차이 2.9. 반올림 오차는 결함이 아니다.

    (저지는 이걸 오탐했다 — 원문 27.88→25.03=2.85라 2.8이 맞다.)
    """
    html = _card("<p>34층은 18층보다 2.8% 더 정확했다</p><p>27.9</p><p>25.0</p>")
    claims = derived_claims(html, paper_text="27.88 25.03 2.85")
    pp = [c for c in claims if c["kind"] == "pct_point"]
    assert pp and pp[0]["suspect"] is False


def test_pct_point_diff_catches_real_error():
    """같은 스케일의 쌍이 있는데 값이 틀리면 오산. (차이는 2.9인데 5%라 씀)

    반면 스케일이 아예 다른 주장(예: 10%)은 '관련 쌍 없음'으로 흘려보낸다 —
    카드 밖 근거일 수 있어 과잉 경고보다 침묵이 낫다(모르면 죄 아님).
    """
    html = _card("<p>5% 더 정확했다</p><p>27.9</p><p>25.0</p>")
    claims = derived_claims(html, paper_text="27.9 25.0")
    pp = [c for c in claims if c["kind"] == "pct_point"][0]
    assert pp["suspect"] is True


def test_year_pair_does_not_create_false_suspect():
    # 연도 2개(2020·2026)가 쌍이 되면 b/a*100≈100.3 → 정당한 '약 100% 향상'이 가짜 suspect가 된다.
    html = _card("<p>2020년 대비 2026년, 성능이 약 100% 향상</p>")
    claims = derived_claims(html, paper_text="2020 2026 성능 100% 향상")
    assert claims[0]["suspect"] is False
    assert claims[0]["unresolved"] is True      # 연도 제외 → 검산 불가
