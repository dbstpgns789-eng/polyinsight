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


@pytest.fixture(autouse=True)
def _stub_understand(monkeypatch):
    """기본: Understand를 빈 다이제스트로 스텁(실 LLM 호출 방지). 개별 테스트가 덮어쓸 수 있음."""
    from backend.core.models import PaperDigest
    monkeypatch.setattr(s6mod.understand, "run", AsyncMock(return_value=PaperDigest(one_liner="mock")))


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


@pytest.mark.asyncio
async def test_coordinator_runs_understand_and_passes_digest(monkeypatch):
    from backend.core.models import PaperDigest, DigestNumber, FieldSource
    types_ = ["cover_v2", "multistat", "closing_v2"]
    digest = PaperDigest(one_liner="요약",
                         numbers=[DigestNumber(value="238", source=FieldSource(section="Results", page=7))])
    und = AsyncMock(return_value=digest)
    arch = AsyncMock(return_value=ArchitectOutput(storyboard=_sb(types_), recommended_theme="forest_green"))
    wr = AsyncMock(return_value=WriterOutput(cards=_cards(types_), meta=_meta(), mismatch_signals=[]))
    monkeypatch.setattr(s6mod.understand, "run", und)
    monkeypatch.setattr(s6mod.architect, "run", arch)
    monkeypatch.setattr(s6mod.writer, "run", wr)

    out = await s6mod.s6_agent.execute(_input(3))
    assert und.await_count == 1
    assert arch.call_args.args[0].digest is digest      # Architect가 digest 받음
    assert wr.call_args.args[0].digest is digest         # Writer도 digest 받음
    assert out.warnings == []


@pytest.mark.asyncio
async def test_coordinator_falls_back_when_understand_fails(monkeypatch):
    types_ = ["cover_v2", "feature", "closing_v2"]
    und = AsyncMock(side_effect=Exception("boom"))       # 항상 실패
    arch = AsyncMock(return_value=ArchitectOutput(storyboard=_sb(types_), recommended_theme="forest_green"))
    wr = AsyncMock(return_value=WriterOutput(cards=_cards(types_), meta=_meta(), mismatch_signals=[]))
    monkeypatch.setattr(s6mod.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(s6mod.understand, "run", und)
    monkeypatch.setattr(s6mod.architect, "run", arch)
    monkeypatch.setattr(s6mod.writer, "run", wr)

    out = await s6mod.s6_agent.execute(_input(3))
    assert arch.call_args.args[0].digest is None         # degraded: digest 없이 진행
    assert any("다이제스트 생략" in w for w in out.warnings)
    assert len(out.card_data.cards) == 3
