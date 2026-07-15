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
        publisher="p", card_count=5, art_direction="", history_block="", figure_block="",
    )
    assert "5장" in u          # card_count 치환 확인


def test_figure_block_is_the_papers_own_anchor():
    """논문이 곧 레퍼런스 — 앵커를 남의 덱에서 논문 자신으로 뒤집는다."""
    assert P.figure_block(0) == ""              # 그림 없는 논문은 조용히 생략(소프트)
    b = P.figure_block(3)
    assert "이 논문 안에 실제로 실린 그림" in b
    assert "스스로 입고 있는 옷" in b
    assert "다시 그려라" in b                    # 그대로 붙이기 금지(저작권·해상도)
    assert "{" not in b and "}" not in b        # .format() 대상이 아니지만 중괄호 혼입 방지


def test_refs_can_be_disabled():
    """AUTHOR_FEWSHOT_N=0이면 refs 주입이 사라진다 — refs 폐기 실험의 스위치."""
    assert P.few_shot_refs(0) == ""


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


def test_no_aesthetic_recipes():
    """미감은 모델 것이다 — 프롬프트는 '기준'을 말하고 '구현'은 지시하지 않는다(헌법 §1).

    2026-07-12 측정: 주입 refs의 색 이름·헥스가 산출물에 그대로 복사됐고, 프롬프트가 직접
    '키토산이면 아이보리' 같은 색 예시를 가르치고 있었다. 레시피 조항이 다시 기어들어오는 것을 막는다.
    """
    s = P.AUTHORING_SYSTEM
    for recipe in (
        "radial-gradient(circle at 36% 32%",   # 광원 위치까지 지정하던 레시피
        "box-shadow` 3겹",                     # 그림자 겹수 규정
        "본문=Pretendard",                     # 서체 고정
        "80px+",                               # 크기 규정
        "반투명 아이보리",                       # 색 예시 = 팔레트 앵커
    ):
        assert recipe not in s, f"미감 레시피가 프롬프트에 복귀함: {recipe!r}"


def test_quality_bars_kept():
    """레시피는 뺐지만 '도달할 기준'은 남아야 한다 — 자유는 방임이 아니다."""
    s = P.AUTHORING_SYSTEM
    assert "만져질 것 같은가" in s        # 표지 초점 오브젝트의 기준
    assert "평평하면 실패" in s           # 깊이의 기준
    assert "죽은 공간 금지" in s          # 1순위 결함(dead_zone 4/5)
    assert "길이가 실제 수치 비율과 일치" in s   # 정직 — 미감이 아니라 협상 불가


def test_output_contract_preserved():
    s = P.AUTHORING_SYSTEM
    assert "data-screen-label" in s
    assert "1080px" in s and "1350px" in s
