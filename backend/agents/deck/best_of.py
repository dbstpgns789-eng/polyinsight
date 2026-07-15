# -*- coding: utf-8 -*-
"""Best-of-N — 저작 분산을 통제하는 유일한 수단 (2026-07-13).

왜 이것이 '품질 기능'이 아니라 '측정의 전제조건'인가:
  같은 논문·같은 코드로 5번 저작한 실측 결과 — integrity 2↔4, finish 1~4.
  **출력 분산이 프롬프트 효과를 압도한다.** n=1로 프롬프트 A/B를 판정하면 노이즈를 읽는 것이다.
  게다가 Opus 4.8은 sampling 파라미터를 거부하므로(`_NO_SAMPLING_PREFIXES`) temperature로
  분산을 줄일 수도 없다. **N개를 뽑아 고르는 것 외에 방법이 없다.**

두 가지를 동시에 준다:
  품질 — 사용자는 상위 표본을 받는다(운을 통제한다)
  측정 — 우리는 분포를 본다(평균 vs 평균으로 비로소 프롬프트 효과가 보인다)
"""
from __future__ import annotations

import logging

from ...scripts.deck_judge import judge_score

logger = logging.getLogger(__name__)


def pick_best(candidates: list[dict]) -> tuple[dict, str]:
    """저지 점수가 가장 높은 후보를 고른다. (best, 선택 로그) 반환.

    candidates: [{"html": str, "pngs": list[bytes], "judge": dict|None}, …]
    저지가 전부 죽어도 덱은 나가야 한다 — 첫 후보로 폴백(소프트).
    """
    if not candidates:
        raise ValueError("후보가 없습니다")
    if len(candidates) == 1:
        return candidates[0], ""

    scored = [(judge_score(c.get("judge")), i, c) for i, c in enumerate(candidates)]
    scored.sort(key=lambda t: -t[0])
    best_score, best_i, best = scored[0]

    if best_score < 0:      # 저지가 전부 죽음
        logger.warning("best-of-N: 저지 전부 실패 — 첫 후보 채택")
        return candidates[0], f"후보 {len(candidates)}개 중 저지가 전부 실패해 1번을 채택했습니다."

    parts = []
    for sc, i, c in scored:
        j = c.get("judge") or {}
        bad = sum(1 for v in (j.get("defects") or {}).values() if v)
        parts.append(f"{i + 1}번 {sc:.1f}점(결함 {bad})")
    log = f"후보 {len(candidates)}개 중 {best_i + 1}번 채택 — " + " · ".join(parts)
    logger.info("best-of-N: %s", log)
    return best, log
