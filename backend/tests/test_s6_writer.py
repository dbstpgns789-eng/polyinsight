"""콘텐츠팀 Writer 모듈 (Task 5)."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from unittest.mock import AsyncMock

from backend.agents.s6 import writer as wr_mod
from backend.core.config import settings
from backend.core.models import CardStorybeat, PaperMetadata, Storyboard, WriterInput


def _meta():
    return PaperMetadata(title="t", authors=["Lee"], year=2024, doi=None)


def _sb(types_):
    return Storyboard(story_arc="arc", beats=[
        CardStorybeat(card_num=i + 1, template_type=t, narrative_role="r", key_message="m")
        for i, t in enumerate(types_)
    ])


def _fv(v):
    return {"value": v, "confidence": "high", "match_quality": "exact",
            "claim_type": "qualitative", "source": {"section": "Abstract", "page": 1}}


def _meta_json():
    return {k: _fv("x") for k in ("org", "dept", "researcher", "month", "edition_number")}


def _cards_json(types_, signals=None):
    cards = [{"card_num": i + 1, "template_type": t, "fields": {"headline": _fv(f"h{i+1}")}}
             for i, t in enumerate(types_)]
    return json.dumps({"meta": _meta_json(), "cards": cards,
                       "mismatch_signals": signals or []})


def _patch(monkeypatch, raw):
    call = AsyncMock(return_value=raw)
    monkeypatch.setattr(wr_mod.llm_client, "call", call)
    return call


@pytest.mark.asyncio
async def test_writer_parses_cards_meta_and_routes_to_haiku(monkeypatch):
    call = _patch(monkeypatch, _cards_json(["cover_v2", "multistat", "closing_v2"]))
    out = await wr_mod.writer.run(WriterInput(
        section_map={"Abstract": "x"}, paper_metadata=_meta(),
        storyboard=_sb(["cover_v2", "multistat", "closing_v2"])))
    assert [c.template_type for c in out.cards] == ["cover_v2", "multistat", "closing_v2"]
    assert out.meta.org.value == "x"
    assert out.mismatch_signals == []
    # 라우팅 증명: Writer는 Haiku(기본). model 미지정 또는 LLM_MODEL.
    model_kw = call.call_args.kwargs.get("model")
    assert model_kw in (None, settings.LLM_MODEL)


@pytest.mark.asyncio
async def test_writer_coerces_template_type_to_storyboard(monkeypatch):
    # 모델이 2번을 bigstat로 잘못 썼지만 스토리보드는 multistat → 스토리보드가 진실.
    _patch(monkeypatch, _cards_json(["cover_v2", "bigstat_compare", "closing_v2"]))
    out = await wr_mod.writer.run(WriterInput(
        section_map={}, paper_metadata=_meta(),
        storyboard=_sb(["cover_v2", "multistat", "closing_v2"])))
    assert out.cards[1].template_type == "multistat"


@pytest.mark.asyncio
async def test_writer_parses_mismatch_signals(monkeypatch):
    sig = [{"card_num": 2, "mismatch": True, "reason": "숫자 1개뿐", "suggested_shape": "bigstat_compare"}]
    _patch(monkeypatch, _cards_json(["cover_v2", "multistat", "closing_v2"], signals=sig))
    out = await wr_mod.writer.run(WriterInput(
        section_map={}, paper_metadata=_meta(),
        storyboard=_sb(["cover_v2", "multistat", "closing_v2"])))
    assert len(out.mismatch_signals) == 1
    assert out.mismatch_signals[0].card_num == 2


@pytest.mark.asyncio
async def test_writer_only_beats_filters_to_targets(monkeypatch):
    # 모델이 전부 돌려줘도 only_beats=[2]면 카드2만 반환.
    _patch(monkeypatch, _cards_json(["cover_v2", "multistat", "closing_v2"]))
    out = await wr_mod.writer.run(WriterInput(
        section_map={}, paper_metadata=_meta(),
        storyboard=_sb(["cover_v2", "multistat", "closing_v2"]), only_beats=[2]))
    assert [c.card_num for c in out.cards] == [2]
