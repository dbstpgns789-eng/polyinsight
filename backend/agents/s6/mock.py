"""DEV_MOCK_LLM 결정적 mock — 설계팀/콘텐츠팀 두 단계로 분할(실 코디네이터 경로와 동형).

mock_storyboard() → ArchitectOutput, mock_cards() → WriterOutput.
코디네이터가 이 둘을 _assemble로 합쳐 실제 LLM 경로와 같은 조립·후처리를 탄다.
"""
from __future__ import annotations

from ...core.models import (
    ArchitectOutput, CardMeta, CardSlot, CardStorybeat, FieldValue,
    FieldSource, MatchQuality, MismatchSignal, RiskLevel, ClaimType,
    Storyboard, WriterOutput, THEME_PRESETS,
)


def _make_fv(value, *, section="abstract", page=1, risk="LOW",
             quality="exact", claim="qualitative", confidence="high") -> FieldValue:
    return FieldValue(
        value=value,
        confidence=confidence,       # type: ignore[arg-type]
        match_quality=MatchQuality(quality),
        claim_type=ClaimType(claim),
        source=FieldSource(section=section, page=page),
        risk_level=RiskLevel(risk),
    )


# card_count → 대표 시퀀스 (mock 결정적; 실제 LLM은 Architect가 storyboard로 선택).
_MOCK_SEQUENCES: dict[int, list[str]] = {
    3: ["cover_v2", "bigstat_compare", "closing_v2"],
    4: ["cover_v2", "feature", "bigstat_compare", "closing_v2"],
    5: ["cover_v2", "statement", "feature", "bigstat_compare", "closing_v2"],
    6: ["cover_v2", "statement", "feature", "bigstat_compare", "grid_v2", "closing_v2"],
    7: ["cover_v2", "statement", "feature", "process_v2", "bigstat_compare", "grid_v2", "closing_v2"],
}

_ROLE_MAP = {
    "cover_v2": "논문 주제 표지",
    "statement": "문제 제기 / 기존 한계",
    "feature": "핵심 혁신 소개",
    "process_v2": "제작 방법 단계",
    "bigstat_compare": "핵심 성능 + 기존 대비 + 출처",
    "reasons": "왜 이 소재인가",
    "grid_v2": "응용 분야",
    "closing_v2": "마무리 / 협력",
}


def _mock_sequence(card_count: int) -> list[str]:
    if card_count in _MOCK_SEQUENCES:
        return _MOCK_SEQUENCES[card_count]
    base = _MOCK_SEQUENCES[7]
    if card_count < 3:
        return _MOCK_SEQUENCES[3]
    if card_count <= 7:
        mid = base[1:-1][: card_count - 2]
        return ["cover_v2", *mid, "closing_v2"]
    return base


_MOCK_FIELDS: dict[str, dict[str, FieldValue]] = {
    "cover_v2": {
        "eyebrow":  _make_fv("KITECH Research Note · 2026", quality="normalized"),
        "headline": _make_fv("플라스틱을 *대체*하는 셀룰로스 미세구슬"),
        "subtitle": _make_fv("COF 복합화로 강도와 생분해성을 동시에", section="abstract", page=1),
        "org":      _make_fv("KITECH 친환경소재연구부문"),
    },
    "statement": {
        "eyebrow":  _make_fv("문제 제기"),
        "headline": _make_fv("왜 친환경 플라스틱은 *약할*까?", section="introduction", page=2),
        "body":     _make_fv(
            "생분해성 소재는 대개 강도가 낮아 구조재로 쓰기 어렵다. 이 한계가 상용화를 막아 왔다.",
            section="introduction", page=2, confidence="medium",
        ),
    },
    "feature": {
        "eyebrow":  _make_fv("핵심 혁신"),
        "headline": _make_fv("셀룰로스에 *COF*를 짜 넣다", section="methods", page=4),
        "body":     _make_fv(
            "공유결합 유기골격체(COF)를 셀룰로스 매트릭스에 복합해, 미세구슬 형태로 강도와 다공성을 함께 얻었다.",
            section="methods", page=4,
        ),
    },
    "process_v2": {
        "eyebrow":  _make_fv("제작 방법"),
        "headline": _make_fv("세 단계로 만든다", section="methods", page=5),
        "steps":    _make_fv(
            "셀룰로스 용액에 COF 전구체 분산|에멀전법으로 미세구슬 성형|동결건조로 다공 구조 고정",
            section="methods", page=5,
        ),
        "caption":  _make_fv("전 과정 무용매·저온 — 친환경 공정", confidence="medium"),
    },
    "bigstat_compare": {
        "eyebrow":      _make_fv("성능 검증"),
        "headline":     _make_fv("기존 플라스틱보다 *더 단단*하다"),
        "stat_value":   _make_fv("238", section="results", page=7,
                                 quality="exact", claim="quantitative"),
        "stat_unit":    _make_fv("MPa"),
        "stat_caption": _make_fv("셀룰로스–COF 복합 미세구슬의 압축 강도", section="results", page=7),
        "bars":         _make_fv(
            "우리 복합 구슬:238:1|폴리프로필렌(PP):199:0|무보강 셀룰로스:142:0",
            section="results", page=7, quality="exact", claim="quantitative",
        ),
        "source_ref":   _make_fv("출처: Cellulose (2024) · Results", section="results", page=7),
    },
    "reasons": {
        "eyebrow":  _make_fv("왜 이 소재인가"),
        "headline": _make_fv("셀룰로스를 고른 *세 가지* 이유"),
        "reasons":  _make_fv(
            "풍부함:지구상 가장 많은 천연 고분자, 원료 걱정이 없다"
            "|생분해성:토양·해양에서 완전 분해된다"
            "|기능화 용이:표면 -OH로 COF 결합이 쉽다",
            section="introduction", page=3,
        ),
    },
    "grid_v2": {
        "eyebrow":  _make_fv("응용 분야"),
        "headline": _make_fv("어디에 *쓰일까*?"),
        "items":    _make_fv(
            "포장재:일회용 플라스틱 대체|흡착소재:중금속·염료 제거"
            "|약물전달:다공성 캡슐|단열재:경량 구조재",
            section="discussion", page=10,
        ),
        "body":     _make_fv("강도·다공성·생분해성의 조합이 응용 폭을 넓힌다.", confidence="medium"),
    },
    "closing_v2": {
        "eyebrow":    _make_fv("맺음말"),
        "headline":   _make_fv("다음은 *대량 생산* 검증", section="conclusion", page=12),
        "body":       _make_fv(
            "실험실 성과를 파일럿 규모로 확장해 경제성과 균일도를 확인하는 후속 연구를 진행한다.",
            section="conclusion", page=12,
        ),
        "source_ref": _make_fv("출처: Cellulose (2024) · Conclusion", section="conclusion", page=12),
    },
}


def mock_storyboard(card_count: int, paper_metadata) -> ArchitectOutput:
    """설계팀 mock — 결정적 시퀀스로 Storyboard 생성."""
    title = getattr(paper_metadata, "title", "") or "연구 성과"
    sequence = _mock_sequence(card_count)
    beats = [
        CardStorybeat(
            card_num=i + 1,
            template_type=tmpl,
            narrative_role=_ROLE_MAP.get(tmpl, "내용 전달"),
            key_message=_MOCK_FIELDS.get(tmpl, {}).get("headline", _make_fv(title)).value,
            content_shape_reason="mock 결정적 시퀀스",
        )
        for i, tmpl in enumerate(sequence)
    ]
    storyboard = Storyboard(
        story_arc=f"{title}의 배경·혁신·성능·응용을 {len(beats)}장으로 구성",
        beats=beats,
    )
    return ArchitectOutput(storyboard=storyboard, recommended_theme="forest_green")


def mock_cards(
    storyboard: Storyboard, paper_metadata,
    *, inject_mismatch: list[MismatchSignal] | None = None,
    only_beats: list[int] | None = None,
) -> WriterOutput:
    """콘텐츠팀 mock — storyboard 비트별 결정적 fields. 루프 테스트용 inject_mismatch/only_beats 지원."""
    title = getattr(paper_metadata, "title", "") or "연구 성과"
    authors = getattr(paper_metadata, "authors", []) or []
    year = getattr(paper_metadata, "year", 2024) or 2024

    meta = CardMeta(
        org=_make_fv("한국생산기술연구원"),
        dept=_make_fv("친환경소재연구부문"),
        researcher=_make_fv(authors[0] if authors else "연구팀"),
        month=_make_fv(f"{year}-01", quality="normalized"),
        edition_number=_make_fv(f"{year}-01호", quality="normalized"),
    )

    only = set(only_beats or [])
    cards: list[CardSlot] = []
    for beat in storyboard.beats:
        if only and beat.card_num not in only:
            continue
        cards.append(CardSlot(
            card_num=beat.card_num,
            template_type=beat.template_type,
            fields=_MOCK_FIELDS.get(beat.template_type, {"headline": _make_fv(title)}),
        ))

    signals = list(inject_mismatch or [])
    if only:
        signals = [s for s in signals if s.card_num in only]
    return WriterOutput(cards=cards, meta=meta, mismatch_signals=signals)
