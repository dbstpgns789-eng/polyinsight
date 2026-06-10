"""CardSlot.field_styles 라운드트립 — override가 검증·덤프에서 보존되는지."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import CardSlot, CardEditorData


def test_cardslot_preserves_field_styles():
    raw = {
        "card_num": 1,
        "template_type": "cover_v2",
        "fields": {"headline": {"value": "x"}},
        "field_styles": {"headline": {"size": "L", "color": "accent", "tracking": 0.02}},
    }
    slot = CardSlot.model_validate(raw)
    assert slot.field_styles is not None
    assert slot.field_styles["headline"].size == "L"
    assert slot.field_styles["headline"].color == "accent"
    dumped = slot.model_dump()
    assert dumped["field_styles"]["headline"]["color"] == "accent"


def test_cardslot_without_field_styles_defaults_none():
    slot = CardSlot.model_validate({
        "card_num": 1, "template_type": "cover_v2", "fields": {},
    })
    assert slot.field_styles is None


def _meta():
    fv = {"value": "x"}
    return {"org": fv, "dept": fv, "researcher": fv, "month": fv, "edition_number": fv}


def test_cardeditordata_accent_and_optional_bg():
    data = CardEditorData.model_validate({
        "meta": _meta(), "cards": [],
        "bg_color": "#0E5E60", "accent_color": "#FFC94A",
    })
    assert data.bg_color == "#0E5E60"
    assert data.accent_color == "#FFC94A"


def test_cardeditordata_color_defaults_none():
    d2 = CardEditorData.model_validate({"meta": _meta(), "cards": []})
    assert d2.bg_color is None
    assert d2.accent_color is None
