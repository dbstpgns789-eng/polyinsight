# -*- coding: utf-8 -*-
"""AI 디자이너 편집 프롬프트 유닛 테스트 (순수 함수, LLM 없음). ops 계약 + 인벤토리."""
from backend.agents.deck.edit_prompts import build_user_prompt, EDIT_SYSTEM

_INV = [{"eid": "e9", "kind": "text", "label": "긴 제목 텍스트",
         "styles": {"color": "#111", "fontSize": "40px"}}]


def test_prompt_renders_inventory():
    p = build_user_prompt(_INV, "짧게", "원문 텍스트")
    assert 'eid="e9"' in p          # 요소 목록에 eid 노출(LLM 타겟 근거)
    assert "긴 제목 텍스트" in p      # label
    assert "짧게" in p               # 지시
    assert "원문 텍스트" in p         # 원문 참고


def test_prompt_target_block_when_eid():
    p = build_user_prompt(_INV, "짧게", None, target={"eid": "e9", "quotedText": "x"})
    assert "지정한 대상" in p and 'eid="e9"' in p


def test_prompt_no_target_omits_block():
    assert "지정한 대상" not in build_user_prompt(_INV, "짧게", None)


def test_prompt_target_without_eid_omits_block():
    assert "지정한 대상" not in build_user_prompt(_INV, "짧게", None, target={"eid": None})


def test_edit_system_ops_contract():
    assert "data-eid" in EDIT_SYSTEM   # eid 계약
    assert "ops" in EDIT_SYSTEM        # ops JSON 계약(전체 HTML 재출력 아님)
