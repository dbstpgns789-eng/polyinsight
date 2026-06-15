"""논문이해팀 Understand 모듈 (Task 3)."""
from __future__ import annotations
import json, pathlib, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))
from unittest.mock import AsyncMock
from backend.agents.s6 import understand as und_mod
from backend.core.config import settings
from backend.core.models import PaperDigest, UnderstandInput, PaperMetadata


def _meta():
    return PaperMetadata(title="셀룰로스 미세구슬", authors=["Lee"], year=2024, doi=None)


_RAW = json.dumps({
    "one_liner": "셀룰로스가 플라스틱보다 강하다",
    "numbers": [{"value": "238", "unit": "MPa", "label": "압축강도", "context": "우리",
                 "source": {"section": "Results", "page": 7}}],
    "comparisons": [], "terms": [{"term": "COF", "plain": "단단한 그물"}],
    "figures": [], "process_steps": [], "claims": [], "domain_hint": "재료",
})


@pytest.mark.asyncio
async def test_understand_parses_digest_and_routes_to_haiku(monkeypatch):
    call = AsyncMock(return_value=_RAW)
    monkeypatch.setattr(und_mod.llm_client, "call", call)
    out = await und_mod.understand.run(UnderstandInput(section_map={"Abstract": "x"}, paper_metadata=_meta()))
    assert isinstance(out, PaperDigest)
    assert out.numbers[0].value == "238"
    assert out.numbers[0].source.page == 7
    assert out.terms[0].term == "COF"
    assert call.call_args.kwargs.get("model") in (None, settings.LLM_MODEL)
