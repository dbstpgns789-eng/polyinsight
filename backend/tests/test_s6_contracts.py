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


# ── 경계 강건화: LLM이 source를 못 채울 때 전체 덱이 죽지 않아야 한다 ──────────
# 실 호출 job f666b539: 논문에 없는 dept/month/edition_number를 모델이 source:{}로
# 내보내 FieldSource.section 필수 검증이 깨지며 덱 전체가 ERR-S6-001로 사망했다.

def test_fieldvalue_tolerates_empty_source_dict():
    from backend.core.models import FieldValue
    fv = FieldValue.model_validate({"value": "3월호", "source": {}})
    assert fv.value == "3월호"
    assert fv.source.section  # 빈 객체 → 기본 sentinel, 크래시 없음


def test_fieldvalue_tolerates_string_source():
    from backend.core.models import FieldValue
    fv = FieldValue.model_validate({"value": "x", "source": "Results"})
    assert fv.source.section == "Results"


def test_fieldvalue_tolerates_null_source():
    from backend.core.models import FieldValue
    fv = FieldValue.model_validate({"value": "x", "source": None})
    assert fv.source.section  # None → 기본값, 크래시 없음


def test_cardmeta_tolerates_ungroundable_fields():
    # 논문에 없는 메타(부서/발행월/호수)를 source:{} 로 내보내도 덱이 살아남는다.
    from backend.core.models import CardMeta
    blank = {"value": "", "source": {}}
    meta = CardMeta.model_validate(
        {"org": blank, "dept": blank, "researcher": blank, "month": blank, "edition_number": blank}
    )
    assert meta.dept.source.section
