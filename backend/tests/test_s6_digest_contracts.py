"""다이제스트 계약 타입 (Task 1)."""
from __future__ import annotations
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import (
    PaperDigest, DigestNumber, DigestComparison, DigestTerm, DigestFigure, DigestClaim,
    UnderstandInput, ArchitectInput, WriterInput, PaperMetadata, FieldSource, Storyboard,
)


def test_empty_digest_defaults():
    d = PaperDigest(one_liner="요약")
    assert d.numbers == [] and d.comparisons == [] and d.terms == []
    assert d.figures == [] and d.process_steps == [] and d.claims == []
    assert d.domain_hint == ""


def test_digest_number_carries_source():
    n = DigestNumber(value="238", unit="MPa", label="압축강도", context="우리 소재",
                     source=FieldSource(section="Results", page=7))
    assert n.source.page == 7


def test_understand_input():
    ui = UnderstandInput(section_map={"Abstract": "x"},
                         paper_metadata=PaperMetadata(title="t", year=2024, doi=None))
    assert ui.section_map["Abstract"] == "x"


def test_architect_writer_input_digest_optional():
    meta = PaperMetadata(title="t", year=2024, doi=None)
    ai = ArchitectInput(section_map={}, paper_metadata=meta, card_count=5)
    assert ai.digest is None
    wi = WriterInput(section_map={}, paper_metadata=meta, storyboard=Storyboard(story_arc="a", beats=[]))
    assert wi.digest is None
    d = PaperDigest(one_liner="요약")
    assert ArchitectInput(section_map={}, paper_metadata=meta, card_count=5, digest=d).digest is d
