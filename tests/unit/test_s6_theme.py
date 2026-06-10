import pytest
from backend.agents.s6_card_json import S6CardJsonAgent
from backend.core.models import THEME_PRESETS


def _minimal_parsed(theme_key: str) -> dict:
    fv = {"value": "test", "confidence": "high", "match_quality": "exact",
          "claim_type": "qualitative", "source": {"section": "abstract", "page": 1},
          "risk_level": "LOW", "verified": False}
    return {
        "recommended_theme": theme_key,
        "storyboard": {
            "story_arc": "테스트 스토리",
            "beats": [{"card_num": 1, "template_type": "cover",
                       "narrative_role": "소개", "key_message": "핵심"}],
        },
        "meta": {
            "org": fv, "dept": fv, "researcher": fv,
            "month": fv, "edition_number": fv,
        },
        "cards": [{"card_num": 1, "template_type": "cover",
                   "fields": {"title": fv}}],
    }


agent = S6CardJsonAgent()


def test_forest_green_theme_applied():
    parsed = _minimal_parsed("forest_green")
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#16A34A"
    assert result.recommended_theme_key == "forest_green"


def test_tech_blue_theme_applied():
    parsed = _minimal_parsed("tech_blue")
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#2563EB"
    assert result.recommended_theme_key == "tech_blue"


def test_invalid_theme_key_falls_back_to_tech_blue():
    parsed = _minimal_parsed("nonexistent_key")
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#2563EB"
    assert result.recommended_theme_key == "tech_blue"


def test_missing_theme_key_falls_back_to_tech_blue():
    parsed = _minimal_parsed("tech_blue")
    del parsed["recommended_theme"]
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#2563EB"
    assert result.recommended_theme_key == "tech_blue"


def test_all_valid_preset_keys_resolve():
    for key in THEME_PRESETS:
        parsed = _minimal_parsed(key)
        result = agent._build_card_editor_data(parsed)
        assert result.theme == THEME_PRESETS[key]
        assert result.recommended_theme_key == key
