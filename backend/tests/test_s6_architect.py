"""설계팀 Architect 모듈 (Task 4)."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from unittest.mock import AsyncMock

from backend.agents.s6 import architect as arch_mod
from backend.core.config import settings
from backend.core.models import ArchitectInput, MismatchSignal, PaperMetadata, Storyboard, CardStorybeat


def _meta():
    return PaperMetadata(title="키토산 셀룰로스 복합 미세구슬", authors=["Lee"], year=2024, doi=None)


def _beat(n, tt, role="역할", msg="메시지", reason="근거"):
    return {"card_num": n, "template_type": tt, "narrative_role": role,
            "key_message": msg, "content_shape_reason": reason}


def _storyboard_json(beats):
    return json.dumps({"recommended_theme": "forest_green",
                       "storyboard": {"story_arc": "arc", "beats": beats}})


def _patch_llm(monkeypatch, raw: str):
    call = AsyncMock(return_value=raw)
    monkeypatch.setattr(arch_mod.llm_client, "call", call)
    return call


@pytest.mark.asyncio
async def test_architect_parses_storyboard_and_routes_to_sonnet(monkeypatch):
    beats = [_beat(1, "cover_v2"), _beat(2, "multistat"), _beat(3, "closing_v2")]
    call = _patch_llm(monkeypatch, _storyboard_json(beats))
    out = await arch_mod.architect.run(ArchitectInput(section_map={"Abstract": "x"}, paper_metadata=_meta(), card_count=3))
    assert isinstance(out.storyboard, Storyboard)
    assert [b.template_type for b in out.storyboard.beats] == ["cover_v2", "multistat", "closing_v2"]
    assert out.recommended_theme == "forest_green"
    # 라우팅 증명: Architect는 Sonnet으로 호출
    assert call.call_args.kwargs["model"] == settings.LLM_MODEL_ARCHITECT


@pytest.mark.asyncio
async def test_architect_rejects_invalid_template_type(monkeypatch):
    beats = [_beat(1, "cover_v2"), _beat(2, "NONSENSE"), _beat(3, "closing_v2")]
    _patch_llm(monkeypatch, _storyboard_json(beats))
    with pytest.raises(ValueError):
        await arch_mod.architect.run(ArchitectInput(section_map={}, paper_metadata=_meta(), card_count=3))


@pytest.mark.asyncio
async def test_architect_coerces_first_and_last(monkeypatch):
    # 모델이 첫/끝을 어기면 코디네이터가 믿을 수 있게 강제 교정.
    beats = [_beat(1, "feature"), _beat(2, "multistat"), _beat(3, "grid_v2")]
    _patch_llm(monkeypatch, _storyboard_json(beats))
    out = await arch_mod.architect.run(ArchitectInput(section_map={}, paper_metadata=_meta(), card_count=3))
    assert out.storyboard.beats[0].template_type == "cover_v2"
    assert out.storyboard.beats[-1].template_type == "closing_v2"


@pytest.mark.asyncio
async def test_architect_revise_only_changes_targeted_beat(monkeypatch):
    # 1차 스토리보드
    current = Storyboard(story_arc="arc", beats=[
        CardStorybeat(**_beat(1, "cover_v2")),
        CardStorybeat(**_beat(2, "multistat")),
        CardStorybeat(**_beat(3, "closing_v2")),
    ])
    # 모델이 2번을 bigstat_compare로 바꿔 반환(나머지는 동일하게 반환했다고 가정)
    revised = [_beat(1, "cover_v2"), _beat(2, "bigstat_compare"), _beat(3, "closing_v2")]
    _patch_llm(monkeypatch, _storyboard_json(revised))
    sig = MismatchSignal(card_num=2, reason="숫자 1개뿐", suggested_shape="bigstat_compare")
    out = await arch_mod.architect.run(ArchitectInput(
        section_map={}, paper_metadata=_meta(), card_count=3,
        revise_beats=[sig], current_storyboard=current,
    ))
    assert out.storyboard.beats[1].template_type == "bigstat_compare"
    # 비지목 비트는 원본 유지
    assert out.storyboard.beats[0].template_type == "cover_v2"
    assert out.storyboard.beats[2].template_type == "closing_v2"
