# -*- coding: utf-8 -*-
"""프롬프트 계약 마커 테스트 — 5층 구조·매니페스트·자기검수·card_count 치환.

프롬프트는 코드처럼 회귀한다. 조항이 사라지거나 위치가 어긋나면 여기서 잡는다.
"""
from backend.agents.deck import authoring_prompts as P


def test_system_formats_without_error():
    s = P.AUTHORING_SYSTEM.format(persona="테스트 페르소나")
    assert "테스트 페르소나" in s


def test_user_formats_without_error():
    u = P.AUTHORING_USER.format(
        few_shot_refs="R", section_map_text="T", title="t", authors="a", year="2026",
        publisher="p", card_count=5, art_direction="", history_block="",
    )
    assert "5장" in u          # card_count 치환 확인


def test_system_has_layer_markers():
    s = P.AUTHORING_SYSTEM
    assert "PI_MANIFEST" in s                    # L3 선언 계약
    assert "이모지" in s                          # L1 신규 가드
    assert "새 아크를 발명" in s                   # 아키타입 탈출구(감옥 금지 — 헌법 §1)
    assert "rejected_arc" in s                   # 버린 아크 근거 — 1번 아크 디폴트 픽 방지


def test_selfcheck_lives_at_the_very_end_of_user_prompt():
    """시스템 끝 ≠ 컨텍스트 끝.

    API 순서상 시스템 뒤에 유저 프롬프트(refs 2덱 + 논문 60k자 ≈ 40k+ 토큰)가 붙는다.
    체크리스트를 시스템 말미에 두면 생성 시점 기준 컨텍스트 한가운데라 recency 이득이 0이다.
    """
    u = P.AUTHORING_USER
    assert "자기검수" in u
    assert u.rindex("자기검수") > u.index("## 지시")


def test_no_hardcoded_seven():
    assert "7장" not in P.AUTHORING_SYSTEM
    assert "7장" not in P.AUTHORING_USER
    assert "7장" not in P.art_direction_block("지브리풍")   # 상수 밖 함수 문자열까지 그물에
    assert "{card_count}" in P.AUTHORING_USER


def test_user_prompt_has_history_slot():
    assert "{history_block}" in P.AUTHORING_USER


def test_refs_header_declares_used_directions():
    """고정 refs(수만 토큰 시연)가 이력(3줄 텍스트)을 이긴다 — refs가 쓴 방향을 명시해 반복을 막는다."""
    refs = P.few_shot_refs(2)
    assert "이미 보여준 방향" in refs


def test_output_contract_preserved():
    s = P.AUTHORING_SYSTEM
    assert "data-screen-label" in s
    assert "1080px" in s and "1350px" in s
