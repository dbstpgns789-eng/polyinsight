# -*- coding: utf-8 -*-
"""Best-of-N — 저작 분산을 통제하는 유일한 수단.

왜 필요한가(실측 2026-07-13): 같은 논문·같은 코드로 5번 저작했더니 integrity가 2↔4를 오가고
finish가 1~4를 전부 찍었다. **출력 분산이 프롬프트 효과를 압도한다.**
게다가 Opus 4.8은 sampling 파라미터를 거부해(_NO_SAMPLING_PREFIXES) temperature로 분산을
줄일 수도 없다. N개를 뽑아 최고를 고르는 것이 유일한 통제 수단이다.

두 가지를 동시에 준다:
  품질 — 사용자는 상위 표본을 받는다
  측정 — 우리는 분포를 본다(n=1 판정은 노이즈를 읽는 것이었다)
"""
from backend.agents.deck.best_of import pick_best
from backend.scripts.deck_judge import judge_score


def _j(hook=3, narr=3, acc=3, integ=3, fin=3, **defects):
    return {
        "scores": {"hook": hook, "narrative": narr, "accessibility": acc,
                   "integrity": integ, "finish": fin},
        "defects": defects,
        "verdict": "pause",
    }


def test_judge_score_penalizes_defects_heavily():
    clean = judge_score(_j(4, 4, 4, 4, 4))                    # 20
    one_bad = judge_score(_j(4, 4, 4, 4, 4, emoji=True))      # 20 - 3 = 17
    assert clean > one_bad
    # 결함 1개는 축 하나가 2점 떨어지는 것보다 무겁다 — 결함은 발행 불가 사유이므로
    assert judge_score(_j(4, 4, 4, 4, 2)) > one_bad


def test_dead_judge_never_wins():
    assert judge_score(None) < judge_score(_j(1, 1, 1, 1, 1))


def test_pick_best_takes_highest_score():
    cands = [
        {"html": "A", "pngs": [b"a"], "judge": _j(3, 3, 3, 3, 3)},               # 15
        {"html": "B", "pngs": [b"b"], "judge": _j(4, 4, 4, 4, 4)},               # 20 ← 최고
        {"html": "C", "pngs": [b"c"], "judge": _j(5, 5, 5, 5, 5, dead_zone=True)},  # 25-3 = 22?
    ]
    # C는 25 - 3 = 22로 실제로 가장 높다 — 점수 그대로 뽑는지 확인
    best, log = pick_best(cands)
    assert best["html"] == "C"
    assert "22.0" in log or "22" in log


def test_pick_best_prefers_clean_over_flashy():
    """결함 있는 화려한 덱보다 결함 없는 덱 — 발행 가능성이 기준이다."""
    cands = [
        {"html": "flashy", "pngs": [b"f"], "judge": _j(5, 5, 5, 5, 5, dead_zone=True, emoji=True)},  # 25-6=19
        {"html": "clean", "pngs": [b"c"], "judge": _j(4, 4, 4, 4, 4)},                               # 20
    ]
    best, _ = pick_best(cands)
    assert best["html"] == "clean"


def test_pick_best_survives_all_judges_dead():
    """저지가 전부 죽어도 덱은 나가야 한다 — 첫 후보로 폴백(소프트)."""
    cands = [
        {"html": "A", "pngs": [b"a"], "judge": None},
        {"html": "B", "pngs": [b"b"], "judge": None},
    ]
    best, log = pick_best(cands)
    assert best["html"] == "A"
    assert "저지" in log


def test_pick_best_single_candidate_is_noop():
    cands = [{"html": "solo", "pngs": [b"s"], "judge": None}]
    best, log = pick_best(cands)
    assert best["html"] == "solo"
    assert log == ""          # 후보가 하나면 선택 로그도 없다
