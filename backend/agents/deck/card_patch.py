# -*- coding: utf-8 -*-
"""카드 단위 교체 — 비전 수정의 출력을 1/5로 줄인다 (2026-07-13, 원가 대응).

배경(CFO 실측): 비전 루프가 매 라운드 **HTML 전문(15~18k 토큰)을 재출력**한다.
출력 단가는 입력의 5배($25 vs $5) → 라운드당 $0.45, 2라운드 $0.90. **저작($0.51)보다 비싸다.**
이것이 덱 원가의 최대 드라이버였다.

"중첩 div라 오려붙이면 깨진다"고 판단해 전체 재출력을 택했는데, **그 판단이 틀렸다** —
실제 저작 덱으로 검증하니 무손실 분해된다(head + 카드 7개 → 재조립 시 원본과 완전 일치).
근거 없는 공포가 덱당 $0.60을 태우고 있었다.

고친 카드만 받아 교체하면 출력 15k → 3k. **덱당 $0.60 절감(원가의 31%).**
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_CARD_START = re.compile(r'(?=<div[^>]+data-screen-label=)', re.I)
_LABEL = re.compile(r'data-screen-label=["\'](\d+)["\']', re.I)
_DIV_TAG = re.compile(r"<div\b[^>]*>|</div\s*>", re.I)
NO_CHANGES = "NO_CHANGES"


def _card_end(chunk: str) -> int:
    """청크에서 카드 최상위 div가 닫히는 위치. div 열림/닫힘을 세어 균형점을 찾는다.

    (중첩 div가 있어도 정확하다 — 카드 div가 depth 0으로 돌아오는 지점이 끝이다.)
    """
    depth = 0
    for m in _DIV_TAG.finditer(chunk):
        if m.group().startswith("</"):
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
    return len(chunk)      # 균형이 안 맞으면 청크 전체를 카드로 본다


def split_cards(html: str) -> tuple[str, list[tuple[str, str, str]], str]:
    """(head, [(label, card_div, sep)], tail). head + Σ(card_div+sep) + tail = 원본(무손실).

    card_div = **순수 카드 div만**, sep = 카드 뒤 구분자(개행·공백).
    둘을 갈라야 교체가 안전하다 — 새 카드엔 sep이 없으므로, card_div에 붙여두면 교체 때 사라진다.
    """
    parts = _CARD_START.split(html)
    if len(parts) < 2:
        return html, [], ""
    head = parts[0]
    cards: list[tuple[str, str, str]] = []
    tail = ""
    last = len(parts) - 2
    for i, chunk in enumerate(parts[1:]):
        m = _LABEL.search(chunk)
        if not m:
            head += chunk          # 라벨 없는 조각은 head에 흡수(손실 방지)
            continue
        end = _card_end(chunk)
        rest = chunk[end:]
        if i == last:              # 마지막 청크의 나머지 = </body></html> 꼬리
            cards.append((m.group(1), chunk[:end], ""))
            tail = rest
        else:
            cards.append((m.group(1), chunk[:end], rest))
    return head, cards, tail


def apply_card_patch(html: str, patch: str) -> tuple[str, int, list[str]]:
    """모델이 준 '고친 카드들'을 원본에 교체. (새 html, 교체 수, warnings).

    - 원본에 없는 라벨은 무시한다(모델이 카드를 새로 만들면 안 된다).
    - 파싱 실패·NO_CHANGES면 원본을 그대로 반환(소프트).
    """
    warns: list[str] = []
    p = (patch or "").strip()
    if p.startswith("```"):                       # 코드펜스 제거
        nl = p.find("\n")
        p = p[nl + 1:] if nl != -1 else p
        end = p.rfind("```")
        if end != -1:
            p = p[:end]
        p = p.strip()

    if not p or NO_CHANGES in p[:40].upper():
        return html, 0, []
    if "data-screen-label" not in p:
        return html, 0, ["비전 수정 출력에 카드가 없어 무시했습니다 — 원본을 유지합니다."]

    _, new_cards, _ = split_cards(p)
    if not new_cards:
        return html, 0, ["비전 수정 출력을 카드로 파싱하지 못해 무시했습니다."]

    head, cards, tail = split_cards(html)
    if not cards:
        return html, 0, ["원본에서 카드를 찾지 못했습니다."]

    known = {lab for lab, _, _ in cards}
    replacement = {}
    n = 0
    for lab, card_div, _ in new_cards:
        if lab not in known:
            warns.append(f"비전 수정이 원본에 없는 카드({lab})를 만들어 무시했습니다.")
            continue
        replacement[lab] = card_div
        n += 1

    # 카드 div만 갈아끼우고 구분자(sep)·head·tail은 원본 그대로 — 무손실 교체
    out = head + "".join(replacement.get(lab, div) + sep for lab, div, sep in cards) + tail
    logger.info("card patch: %d/%d 카드 교체 (%d→%d chars)", n, len(cards), len(html), len(out))
    return out, n, warns
