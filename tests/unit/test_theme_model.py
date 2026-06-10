import pytest
from backend.core.models import CardEditorData, CardMeta, CardTheme, FieldValue, THEME_PRESETS


def _make_fv(v=""):
    return FieldValue(value=v)


def _minimal_meta():
    return CardMeta(
        org=_make_fv("KITECH"),
        dept=_make_fv("연구부"),
        researcher=_make_fv("홍길동"),
        month=_make_fv("2024-01"),
        edition_number=_make_fv("2024-01호"),
    )


def test_theme_presets_has_six_keys():
    assert set(THEME_PRESETS.keys()) == {
        "tech_blue", "forest_green", "sunset_orange",
        "royal_violet", "golden_yellow", "slate"
    }


def test_card_editor_data_default_theme():
    data = CardEditorData(meta=_minimal_meta(), cards=[])
    assert data.theme.primary == "#2563EB"
    assert data.theme.dark == "#1A4C96"


def test_card_editor_data_custom_theme():
    theme = THEME_PRESETS["forest_green"]
    data = CardEditorData(meta=_minimal_meta(), cards=[], theme=theme)
    assert data.theme.primary == "#16A34A"


def test_card_editor_data_recommended_key_default_none():
    data = CardEditorData(meta=_minimal_meta(), cards=[])
    assert data.recommended_theme_key is None


def test_card_editor_data_recommended_key_set():
    data = CardEditorData(
        meta=_minimal_meta(), cards=[],
        recommended_theme_key="forest_green"
    )
    assert data.recommended_theme_key == "forest_green"


def test_backward_compat_no_theme_in_dict():
    """기존 DB 레코드(theme 없음) → default_factory로 복원."""
    raw = {
        "meta": {
            "org": {"value": "KITECH"},
            "dept": {"value": "연구부"},
            "researcher": {"value": "홍길동"},
            "month": {"value": "2024-01"},
            "edition_number": {"value": "2024-01호"},
        },
        "cards": [],
    }
    data = CardEditorData.model_validate(raw)
    assert data.theme.primary == "#2563EB"  # default
    assert data.recommended_theme_key is None
