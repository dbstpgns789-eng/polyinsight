# -*- coding: utf-8 -*-
"""레이아웃 감사 — 죽은 공간을 **코드가** 판정한다 (2026-07-14).

왜 코드인가:
    비전 루프는 모델의 눈에 판정을 맡긴다. 그런데 실측(2026-07-12)에서 모델은 5편 전부
    자가검수 "전항 통과"를 신고했고, 저지는 5편 중 4편에서 dead_zone을 잡았다.
    **모델은 자기 결함을 못 본다** — 그래서 "빈 구획이 있나?"라는 질문은 픽셀로 답해야 한다.

    외부 벤치마크(클로드 디자인, 2026-07-14)가 같은 결론에 도달했다: 저작 후 카드를 캡처해
    "상단 3분의 1이 비었다"를 확인하고 3단 분배로 재작성했다. 우리는 그 확인을 코드로 한다.

무엇을 재는가 (전부 결정론적):
    1) 세로 3등분 구획별 잉크 비율 — 한 구획이 사실상 비면 dead zone
    2) 가장 긴 빈 가로 밴드 — 요소 사이가 아니라 '구멍'이면 미완성으로 읽힌다
    3) 잉크의 세로 분포 — 위쪽에 몰리고 아래가 빈 전형적 실패
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image

logger = logging.getLogger(__name__)

INK_TOLERANCE = 24        # 배경색과 이만큼 차이나면 '잉크'(안티에일리어싱 흡수)
DEAD_THIRD_INK = 0.004    # 한 구획 잉크 비율이 0.4% 미만 = 사실상 빈 구획
EDGE_MARGIN = 0.04        # 상하 4%는 여백으로 인정(크롬 바깥)

# ★공백의 '크기'는 결함이 아니다 — 쏠림이 결함이다 (2026-07-14 재캘리브레이션).
#   1차 기준(내부 공백 >18% = 구멍)은 **호흡을 결함으로 오인**했다. 실측이 그걸 반증했다:
#     클로드 디자인 14장: 내부 공백 8~20%로 흩어지지만 **무게중심 0.43~0.57**(전부 균형)
#     우리 파이프라인   : 무게중심 **0.27~0.70** — 위/아래로 쏠리고 가운데가 비어 미완성으로 읽힘
#   즉 판정해야 할 것은 "빈 곳이 있나"가 아니라 "잉크가 한쪽으로 쏠렸나"다.
#   여백이 호흡인지 구멍인지는 **저작자가 판단한다**(§1) — 코드는 쏠림만 신고한다.
BALANCE_TOLERANCE = 0.12  # |무게중심 - 0.5|가 이보다 크면 쏠림
GAP_NOTE_RATIO = 0.18     # 참고용으로만 알려주는 내부 공백(결함 아님)


@dataclass
class CardAudit:
    card_num: int
    thirds_ink: tuple[float, float, float]     # 구획별 잉크 비율
    dead_thirds: list[int]                     # 1=상단 2=중단 3=하단
    center_of_mass: float                      # 잉크 무게중심 (0=맨위, 0.5=균형, 1=맨아래)
    largest_gap: float                         # 가장 긴 빈 밴드(높이 비율) — 참고용
    gap_at: tuple[int, int] | None             # 그 밴드의 y범위(px)

    @property
    def imbalance(self) -> float:
        return abs(self.center_of_mass - 0.5)

    @property
    def ok(self) -> bool:
        """결함 = 빈 구획 또는 쏠림. **공백 크기 자체는 결함이 아니다**(호흡일 수 있다)."""
        return not self.dead_thirds and self.imbalance <= BALANCE_TOLERANCE

    def as_note(self) -> str:
        """비전 루프에 넘길 **관찰**. 판정(고칠지 말지)은 저작자가 한다 — 코드는 미감을 규정하지 않는다(§1)."""
        bits = []
        if self.dead_thirds:
            names = {1: "상단", 2: "중단", 3: "하단"}
            bits.append(f"{'·'.join(names[t] for t in self.dead_thirds)} 구획에 내용이 거의 없다")
        if self.imbalance > BALANCE_TOLERANCE:
            side = "위쪽" if self.center_of_mass < 0.5 else "아래쪽"
            bits.append(f"잉크가 {side}으로 쏠렸다(무게중심 {self.center_of_mass:.2f}, 균형=0.50)")
        if not bits:
            return ""
        if self.gap_at and self.largest_gap >= GAP_NOTE_RATIO:
            y0, y1 = self.gap_at
            bits.append(f"가장 큰 빈 구간은 y={y0}~{y1}px({self.largest_gap:.0%})")
        return f"카드 {self.card_num:02d}: " + " / ".join(bits)


def _ink_rows(img: Image.Image) -> list[float]:
    """행마다 '잉크 비율'(배경과 다른 픽셀의 비율)."""
    img = img.convert("RGB")
    w, h = img.size
    # 배경색 = 최빈색 (카드는 자기 배경을 스스로 칠한다 — 헌법 출력계약)
    bg = max(img.getcolors(w * h), key=lambda c: c[0])[1]
    px = img.load()
    rows = []
    step = max(1, w // 180)        # 가로 샘플링(속도)
    for y in range(h):
        ink = 0
        n = 0
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > INK_TOLERANCE:
                ink += 1
            n += 1
        rows.append(ink / n)
    return rows


def audit_card(png: bytes, card_num: int) -> CardAudit:
    rows = _ink_rows(Image.open(io.BytesIO(png)))
    h = len(rows)
    t = h // 3
    thirds = (
        sum(rows[:t]) / t,
        sum(rows[t:2 * t]) / t,
        sum(rows[2 * t:]) / (h - 2 * t),
    )
    dead = [i + 1 for i, v in enumerate(thirds) if v < DEAD_THIRD_INK]

    total = sum(rows)
    com = (sum(y * v for y, v in enumerate(rows)) / total / h) if total else 0.5

    # 가장 긴 빈 밴드 (상하 여백 제외 — 크롬 바깥은 원래 비어 있다)
    lo, hi = int(h * EDGE_MARGIN), int(h * (1 - EDGE_MARGIN))
    best = (0, None)
    run = 0
    for y in range(lo, hi):
        if rows[y] < 0.002:
            run += 1
            if run > best[0]:
                best = (run, (y - run + 1, y))
        else:
            run = 0

    return CardAudit(card_num, thirds, dead, com, best[0] / h, best[1])


def audit_deck(pngs: list[bytes]) -> tuple[list[CardAudit], list[str]]:
    """덱 전체 감사. (감사결과, 비전루프에 넘길 지시들)

    ★소프트다 — 읽을 수 없는 이미지는 건너뛴다. 감사는 **보조 신호**이지 관문이 아니다.
      감사가 터져서 저작(비싼 것)이 죽는 건 최악이다.
    """
    audits: list[CardAudit] = []
    for i, p in enumerate(pngs):
        try:
            audits.append(audit_card(p, i + 1))
        except Exception as exc:            # 손상된 PNG·예상 못한 포맷
            logger.warning("layout_audit: 카드 %d 감사 실패(%s) — 건너뜀", i + 1, type(exc).__name__)
    notes = [a.as_note() for a in audits if not a.ok]
    if notes:
        logger.info("layout_audit: %d/%d 카드에 레이아웃 결함", len(notes), len(audits))
    return audits, notes
