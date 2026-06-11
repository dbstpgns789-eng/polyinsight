"""다이제스트 직렬화 + 프롬프트 (Task 2)."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.agents.s6._util import format_digest
from backend.agents.s6 import prompts
from backend.core.models import (
    PaperDigest, DigestNumber, DigestComparison, DigestTerm, DigestClaim, FieldSource,
)


def _digest():
    return PaperDigest(
        one_liner="셀룰로스 미세구슬이 플라스틱보다 강하다",
        numbers=[DigestNumber(value="238", unit="MPa", label="압축강도", context="우리 소재",
                              source=FieldSource(section="Results", page=7))],
        comparisons=[DigestComparison(attribute="압축강도", items=["우리", "PP"], values=["238", "199"],
                                      source=FieldSource(section="Results", page=7))],
        terms=[DigestTerm(term="COF", plain="구멍 많은 단단한 그물")],
        claims=[DigestClaim(role="result", text="플라스틱보다 단단", source=FieldSource(section="Results", page=7))],
        domain_hint="재료/환경",
    )


def test_format_digest_includes_sections_and_sources():
    out = format_digest(_digest())
    assert "238" in out and "MPa" in out
    assert "압축강도" in out
    assert "COF" in out
    assert "Results" in out and "7" in out
    assert "셀룰로스 미세구슬" in out


def test_format_digest_empty_sections_omitted():
    out = format_digest(PaperDigest(one_liner="요약만"))
    assert "요약만" in out
    assert "numbers" not in out.lower()


def test_prompts_understand_and_writer_digest_slot():
    assert "지어내지" in prompts.UNDERSTAND_SYSTEM
    assert "{digest_hints}" in prompts.WRITER_USER
