"""S6 멀티에이전트 내부 계약 타입 (Task 2)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import (
    ArchitectInput, ArchitectOutput, CardStorybeat, MismatchSignal,
    PaperMetadata, Storyboard, WriterInput, WriterOutput,
)


def test_storybeat_validates_without_content_shape_reason():
    # 기존 mock/테스트가 신규 필드 없이도 유효해야 한다(기본값 "").
    beat = CardStorybeat.model_validate(
        {"card_num": 1, "template_type": "cover_v2",
         "narrative_role": "표지", "key_message": "핵심"}
    )
    assert beat.content_shape_reason == ""


def test_mismatch_signal_defaults():
    sig = MismatchSignal(card_num=4, reason="수치 1개뿐", suggested_shape="bigstat_compare")
    assert sig.mismatch is True
    assert sig.card_num == 4


def test_architect_input_optional_revision_fields():
    ai = ArchitectInput(section_map={}, paper_metadata=PaperMetadata(title="t", year=2024, doi=None), card_count=5)
    assert ai.revise_beats is None
    assert ai.current_storyboard is None


def test_architect_output_shape():
    sb = Storyboard(story_arc="arc", beats=[])
    ao = ArchitectOutput(storyboard=sb, recommended_theme="forest_green")
    assert ao.recommended_theme == "forest_green"


def test_writer_io_shape():
    wi = WriterInput(
        section_map={}, paper_metadata=PaperMetadata(title="t", year=2024, doi=None),
        storyboard=Storyboard(story_arc="a", beats=[]),
    )
    assert wi.only_beats is None
    wo = WriterOutput(cards=[], meta=_min_meta())
    assert wo.mismatch_signals == []


def _min_meta():
    from backend.core.models import CardMeta, FieldValue
    fv = FieldValue(value="x")
    return CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv)
