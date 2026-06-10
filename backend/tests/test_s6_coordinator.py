"""S6 코디네이터 배선 — Architect→Writer 조립 + 일관성 (Task 7)."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from unittest.mock import AsyncMock

from backend.agents import s6_card_json as s6mod
from backend.core.models import (
    ArchitectOutput, CardMeta, CardSlot, CardStorybeat, FieldValue,
    PaperMetadata, S6Input, Storyboard, WriterOutput,
)


def _sb(types_):
    return Storyboard(story_arc="arc", beats=[
        CardStorybeat(card_num=i + 1, template_type=t, narrative_role="r", key_message="m")
        for i, t in enumerate(types_)])


def _cards(types_):
    return [CardSlot(card_num=i + 1, template_type=t, fields={"headline": FieldValue(value="h")})
            for i, t in enumerate(types_)]


def _meta():
    fv = FieldValue(value="x")
    return CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv)


def _input(n=3):
    return S6Input(job_id="t", section_map={"Abstract": "x"}, page_map={1: "p"},
                   paper_metadata=PaperMetadata(title="t", year=2024, doi=None), card_count=n)


@pytest.mark.asyncio
async def test_coordinator_assembles_architect_and_writer(monkeypatch):
    types_ = ["cover_v2", "multistat", "closing_v2"]
    monkeypatch.setattr(s6mod.architect, "run", AsyncMock(
        return_value=ArchitectOutput(storyboard=_sb(types_), recommended_theme="forest_green")))
    monkeypatch.setattr(s6mod.writer, "run", AsyncMock(
        return_value=WriterOutput(cards=_cards(types_), meta=_meta(), mismatch_signals=[])))

    out = await s6mod.s6_agent.execute(_input(3))
    assert [c.template_type for c in out.card_data.cards] == types_          # cards = Writer
    assert out.card_data.recommended_theme_key == "forest_green"            # theme = Architect
    assert out.card_data.storyboard.story_arc == "arc"                      # storyboard = Architect
    # 일관성: 스토리보드 비트 ↔ 카드 번호 일치
    assert [b.card_num for b in out.card_data.storyboard.beats] == [c.card_num for c in out.card_data.cards]


@pytest.mark.asyncio
async def test_coordinator_coverage_mismatch_retries_then_raises(monkeypatch):
    # Writer가 비트(3)보다 적은 카드(2) 반환 → 커버리지 불일치 → 재시도 소진 → ERR-S6-001
    monkeypatch.setattr(s6mod.architect, "run", AsyncMock(
        return_value=ArchitectOutput(storyboard=_sb(["cover_v2", "multistat", "closing_v2"]),
                                     recommended_theme="forest_green")))
    monkeypatch.setattr(s6mod.writer, "run", AsyncMock(
        return_value=WriterOutput(cards=_cards(["cover_v2", "closing_v2"]), meta=_meta())))

    with pytest.raises(RuntimeError, match="ERR-S6-001"):
        await s6mod.s6_agent.execute(_input(3))
