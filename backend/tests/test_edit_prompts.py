# -*- coding: utf-8 -*-
"""편집 프롬프트 target 앵커 유닛 테스트 (순수 함수, LLM 없음)."""
from backend.agents.deck.edit_prompts import build_user_prompt, EDIT_SYSTEM


def test_build_user_prompt_includes_target_block():
    p = build_user_prompt(
        "<html>x</html>", "짧게", "원문 텍스트", html_cap=1000,
        target={"eid": "e9", "quotedText": "긴 제목 텍스트"},
    )
    assert 'data-eid="e9"' in p
    assert "긴 제목 텍스트" in p
    assert "편집 대상 요소" in p


def test_build_user_prompt_no_target_omits_block():
    p = build_user_prompt("<html>x</html>", "짧게", None, html_cap=1000)
    assert "편집 대상 요소" not in p


def test_build_user_prompt_target_without_eid_omits_block():
    p = build_user_prompt("<html>x</html>", "짧게", None, html_cap=1000,
                          target={"eid": None, "quotedText": "x"})
    assert "편집 대상 요소" not in p


def test_edit_system_has_eid_preservation_rule():
    assert "data-eid" in EDIT_SYSTEM
