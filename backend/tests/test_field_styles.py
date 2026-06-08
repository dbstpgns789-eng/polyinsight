"""CardSlot.field_styles 라운드트립 — override가 검증·덤프에서 보존되는지."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import CardSlot


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
