"""S6 피드백 루프 (1회) + 안전 뼈대 fallback (Task 9)."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from unittest.mock import AsyncMock

from backend.agents import s6_card_json as s6mod
from backend.core.models import (
    ArchitectOutput, CardMeta, CardSlot, CardStorybeat, FieldValue,
    MismatchSignal, PaperMetadata, S6Input, Storyboard, WriterOutput,
)


def _sb(types_):
    return Storyboard(story_arc="arc", beats=[
        CardStorybeat(card_num=i + 1, template_type=t, narrative_role="r", key_message="m")
        for i, t in enumerate(types_)])


def _cards(pairs):
    # pairs: list of (card_num, template_type)
    return [CardSlot(card_num=n, template_type=t, fields={"headline": FieldValue(value=f"h{n}")})
            for n, t in pairs]


def _meta():
    fv = FieldValue(value="x")
    return CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv)


def _input(n=3):
    return S6Input(job_id="t", section_map={"Abstract": "x"}, page_map={1: "p"},
                   paper_metadata=PaperMetadata(title="t", year=2024, doi=None), card_count=n)


def _sig(n, shape="bigstat_compare"):
    return MismatchSignal(card_num=n, reason="숫자 1개뿐", suggested_shape=shape)


@pytest.mark.asyncio
async def test_loop_resolves_on_revision(monkeypatch):
    """Writer가 카드2 불일치 → Architect 재설계(bigstat) → Writer 부분재작성 → 해소(경고 없음)."""
    types0 = ["cover_v2", "multistat", "closing_v2"]
    types1 = ["cover_v2", "bigstat_compare", "closing_v2"]
    arch = AsyncMock(side_effect=[
        ArchitectOutput(storyboard=_sb(types0), recommended_theme="forest_green"),   # 초기
        ArchitectOutput(storyboard=_sb(types1), recommended_theme="forest_green"),   # 재설계
    ])
    writer_mock = AsyncMock(side_effect=[
        WriterOutput(cards=_cards([(1, "cover_v2"), (2, "multistat"), (3, "closing_v2")]),
                     meta=_meta(), mismatch_signals=[_sig(2)]),                       # 1차: 불일치
        WriterOutput(cards=_cards([(2, "bigstat_compare")]), meta=_meta(), mismatch_signals=[]),  # 부분 재작성
    ])
    monkeypatch.setattr(s6mod.architect, "run", arch)
    monkeypatch.setattr(s6mod.writer, "run", writer_mock)

    out = await s6mod.s6_agent.execute(_input(3))
    assert arch.await_count == 2          # 초기 + 재설계
    assert writer_mock.await_count == 2   # 전체 + 부분
    # 카드2가 재설계된 뼈대로 교체·병합됨
    tt = {c.card_num: c.template_type for c in out.card_data.cards}
    assert tt == {1: "cover_v2", 2: "bigstat_compare", 3: "closing_v2"}
    assert out.warnings == []             # 해소됨 → degraded 아님
    # storyboard↔cards 일관성
    assert [b.template_type for b in out.card_data.storyboard.beats] == \
           [c.template_type for c in out.card_data.cards]


@pytest.mark.asyncio
async def test_loop_persistent_mismatch_falls_back_to_safe_skeleton(monkeypatch):
    """재설계 후에도 카드2 불일치 → 안전 뼈대(callout) 대체 + degraded 경고."""
    arch = AsyncMock(side_effect=[
        ArchitectOutput(storyboard=_sb(["cover_v2", "multistat", "closing_v2"]), recommended_theme="forest_green"),
        ArchitectOutput(storyboard=_sb(["cover_v2", "compare_table", "closing_v2"]), recommended_theme="forest_green"),
    ])
    writer_mock = AsyncMock(side_effect=[
        WriterOutput(cards=_cards([(1, "cover_v2"), (2, "multistat"), (3, "closing_v2")]),
                     meta=_meta(), mismatch_signals=[_sig(2)]),
        WriterOutput(cards=_cards([(2, "compare_table")]), meta=_meta(),
                     mismatch_signals=[_sig(2, "compare_table")]),     # 여전히 불일치
    ])
    monkeypatch.setattr(s6mod.architect, "run", arch)
    monkeypatch.setattr(s6mod.writer, "run", writer_mock)

    out = await s6mod.s6_agent.execute(_input(3))
    tt = {c.card_num: c.template_type for c in out.card_data.cards}
    assert tt[2] == "callout"                                  # 안전 뼈대 대체
    assert any("카드2" in w and "안전 뼈대" in w for w in out.warnings)
    # 안전 뼈대 카드도 기존 headline 재사용(빈 카드 아님)
    assert out.card_data.cards[1].fields["headline"].value == "h2"
    # storyboard도 동기화
    assert out.card_data.storyboard.beats[1].template_type == "callout"
