"""S6 코디네이터 재시도/503/truncation 가로지르기 (Task 10)."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from unittest.mock import AsyncMock

from backend.agents import s6_card_json as s6mod
from backend.core.llm_client import LLMTruncationError
from backend.core.models import (
    ArchitectOutput, CardMeta, CardSlot, CardStorybeat, FieldValue,
    PaperMetadata, S6Input, Storyboard, WriterOutput,
)


def _sb():
    return Storyboard(story_arc="arc", beats=[
        CardStorybeat(card_num=i + 1, template_type=t, narrative_role="r", key_message="m")
        for i, t in enumerate(["cover_v2", "feature", "closing_v2"])])


def _wr():
    fv = FieldValue(value="x")
    meta = CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv)
    cards = [CardSlot(card_num=i + 1, template_type=t, fields={"headline": FieldValue(value="h")})
             for i, t in enumerate(["cover_v2", "feature", "closing_v2"])]
    return WriterOutput(cards=cards, meta=meta, mismatch_signals=[])


def _input():
    return S6Input(job_id="t", section_map={"Abstract": "x"}, page_map={1: "p"},
                   paper_metadata=PaperMetadata(title="t", year=2024, doi=None), card_count=3)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(s6mod.asyncio, "sleep", AsyncMock())


@pytest.mark.asyncio
async def test_architect_503_then_success(monkeypatch):
    arch = AsyncMock(side_effect=[
        Exception("503 server overloaded"),
        ArchitectOutput(storyboard=_sb(), recommended_theme="forest_green"),
    ])
    monkeypatch.setattr(s6mod.architect, "run", arch)
    monkeypatch.setattr(s6mod.writer, "run", AsyncMock(return_value=_wr()))
    out = await s6mod.s6_agent.execute(_input())
    assert arch.await_count == 2
    assert len(out.card_data.cards) == 3


@pytest.mark.asyncio
async def test_writer_truncation_maps_to_err_s6_002(monkeypatch):
    monkeypatch.setattr(s6mod.architect, "run",
                        AsyncMock(return_value=ArchitectOutput(storyboard=_sb(), recommended_theme="forest_green")))
    monkeypatch.setattr(s6mod.writer, "run", AsyncMock(side_effect=LLMTruncationError(9000, 8192)))
    with pytest.raises(RuntimeError, match="ERR-S6-002"):
        await s6mod.s6_agent.execute(_input())


@pytest.mark.asyncio
async def test_exhausted_retries_map_to_err_s6_001(monkeypatch):
    arch = AsyncMock(side_effect=Exception("boom"))
    monkeypatch.setattr(s6mod.architect, "run", arch)
    monkeypatch.setattr(s6mod.writer, "run", AsyncMock(return_value=_wr()))
    with pytest.raises(RuntimeError, match="ERR-S6-001"):
        await s6mod.s6_agent.execute(_input())
    assert arch.await_count == s6mod.S6CardJsonAgent.MAX_RETRIES


@pytest.mark.asyncio
async def test_architect_truncation_maps_to_err_s6_003(monkeypatch):
    # Architect 출력 천장 = 프롬프트 버그(카드 과다 아님) → ERR-S6-003
    monkeypatch.setattr(s6mod.architect, "run", AsyncMock(side_effect=LLMTruncationError(3900, 4000)))
    monkeypatch.setattr(s6mod.writer, "run", AsyncMock(return_value=_wr()))
    with pytest.raises(RuntimeError, match="ERR-S6-003"):
        await s6mod.s6_agent.execute(_input())
