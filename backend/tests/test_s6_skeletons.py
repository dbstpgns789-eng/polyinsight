"""S6 DEV_MOCK 출력이 신규 8뼈대 계약을 따르는지 검증."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core import config
from backend.core.models import (
    S6Input, PaperMetadata, VALID_TEMPLATE_TYPES,
    FieldValue, FieldSource, MatchQuality, ClaimType, RiskLevel,
    CardEditorData, CardMeta, CardSlot,
)
from backend.agents.s6_card_json import s6_agent

NEW_SKELETONS = {
    "cover_v2", "statement", "feature", "process_v2",
    "reasons", "grid_v2", "closing_v2", "bigstat_compare",
}


def _mk_input(card_count: int) -> S6Input:
    return S6Input(
        job_id="test",
        section_map={"Abstract": "셀룰로스 COF 복합 미세구슬", "Results": "238 MPa"},
        page_map={1: "p1"},
        paper_metadata=PaperMetadata(title="셀룰로스 미세구슬", authors=["이호익"], year=2024, doi=None),
        card_count=card_count,
    )


@pytest.fixture(autouse=True)
def _force_mock(monkeypatch):
    monkeypatch.setattr(config.settings, "DEV_MOCK_LLM", True)


@pytest.mark.asyncio
async def test_mock_uses_new_skeletons():
    out = await s6_agent.execute(_mk_input(5))
    tts = [c.template_type for c in out.card_data.cards]
    assert all(t in NEW_SKELETONS for t in tts), f"구 템플릿 누출: {tts}"
    assert tts[0] == "cover_v2"
    assert tts[-1] == "closing_v2"
    assert "bigstat_compare" in tts


@pytest.mark.asyncio
@pytest.mark.parametrize("n", [3, 4, 5, 6, 7])
async def test_card_count_respected(n):
    out = await s6_agent.execute(_mk_input(n))
    assert len(out.card_data.cards) == n
    assert out.card_data.cards[0].template_type == "cover_v2"
    assert out.card_data.cards[-1].template_type == "closing_v2"


@pytest.mark.asyncio
async def test_field_formats():
    out = await s6_agent.execute(_mk_input(7))
    by_type = {c.template_type: c.fields for c in out.card_data.cards}

    bars = by_type["bigstat_compare"]["bars"].value
    rows = bars.split("|")
    assert len(rows) >= 2
    for r in rows:
        parts = r.split(":")
        assert len(parts) == 3 and parts[2] in ("0", "1"), f"bars 포맷 위반: {r}"
    assert any(r.split(":")[2] == "1" for r in rows), "강조행(1) 없음"

    assert "|" in by_type["process_v2"]["steps"].value

    for item in by_type["grid_v2"]["items"].value.split("|"):
        assert ":" in item, f"items 포맷 위반: {item}"

    assert "*" in by_type["bigstat_compare"]["headline"].value


@pytest.mark.asyncio
async def test_grounding_preserved():
    out = await s6_agent.execute(_mk_input(7))
    by_type = {c.template_type: c.fields for c in out.card_data.cards}
    stat = by_type["bigstat_compare"]["stat_value"]
    assert stat.source is not None
    assert stat.risk_level is not None
    for c in out.card_data.cards:
        for fv in c.fields.values():
            assert fv.verified is False


def _fv(claim: ClaimType, mq: MatchQuality) -> FieldValue:
    return FieldValue(
        value="x", confidence="high", match_quality=mq, claim_type=claim,
        source=FieldSource(section="s", page=1), risk_level=RiskLevel.LOW,
    )


def test_risk_taxonomy_post_process():
    """위험은 수치(정량)가 진다. 정성/인과 의역은 MEDIUM 상한."""
    Q, QL, C = ClaimType.QUANTITATIVE, ClaimType.QUALITATIVE, ClaimType.CAUSAL
    MQ = MatchQuality
    cases = {
        "q_failed":   (_fv(Q, MQ.FAILED),     RiskLevel.CRITICAL),
        "q_semantic": (_fv(Q, MQ.SEMANTIC),   RiskLevel.HIGH),
        "q_fuzzy":    (_fv(Q, MQ.FUZZY),      RiskLevel.HIGH),
        "q_norm":     (_fv(Q, MQ.NORMALIZED), RiskLevel.MEDIUM),
        "q_exact":    (_fv(Q, MQ.EXACT),      RiskLevel.LOW),
        "ql_semantic":(_fv(QL, MQ.SEMANTIC),  RiskLevel.MEDIUM),  # 의역 ≠ HIGH
        "ql_failed":  (_fv(QL, MQ.FAILED),    RiskLevel.MEDIUM),
        "ql_exact":   (_fv(QL, MQ.EXACT),     RiskLevel.LOW),
        "causal_fuzzy":(_fv(C, MQ.FUZZY),     RiskLevel.MEDIUM),  # 인과도 상한 MEDIUM
    }
    fields = {k: v for k, (v, _) in cases.items()}
    meta = CardMeta(
        org=_fv(QL, MQ.EXACT), dept=_fv(QL, MQ.EXACT), researcher=_fv(QL, MQ.EXACT),
        month=_fv(QL, MQ.EXACT), edition_number=_fv(QL, MQ.EXACT),
    )
    cd = CardEditorData(meta=meta, cards=[CardSlot(card_num=1, template_type="statement", fields=fields)])
    s6_agent._post_process(cd)
    for k, (fv, expected) in cases.items():
        assert fv.risk_level == expected, f"{k}: {fv.risk_level} != {expected}"
