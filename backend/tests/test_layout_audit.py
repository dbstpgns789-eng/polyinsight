# -*- coding: utf-8 -*-
"""레이아웃 감사 — 죽은 공간을 코드가 판정한다.

캘리브레이션(2026-07-14, 클로드 디자인 덱 2편 실측):
  GPT-3 카드6  → 검출 ✓ (사람 심사와 일치: 헤드라인과 불릿 사이 18% 구멍)
  MMLU 카드3·7 → 검출 ✓ (저작 모델의 자체 루프가 놓친 것 — 그 루프의 규칙은
                        '세로 3등분에 내용이 있나'였고, 요소 사이 구멍은 안 봤다)
"""
import io

import pytest
from PIL import Image, ImageDraw

from backend.agents.deck.layout_audit import audit_card, audit_deck


def _card(bands: list[tuple[int, int]], size=(1080, 1350)) -> bytes:
    """지정한 y구간에만 잉크가 있는 카드 PNG."""
    img = Image.new("RGB", size, (20, 16, 9))       # 카드가 자기 배경을 소유(출력 계약)
    d = ImageDraw.Draw(img)
    for y0, y1 in bands:
        d.rectangle([80, y0, size[0] - 80, y1], fill=(241, 231, 214))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_full_card_passes():
    """세 구획 모두 채워지고 큰 구멍이 없으면 통과."""
    png = _card([(100, 400), (500, 850), (950, 1250)])
    a = audit_card(png, 1)
    assert a.ok
    assert a.as_note() == ""


def test_empty_bottom_third_is_dead_zone():
    """하단 구획이 통째로 비면 잡는다 — 실측 1순위 결함."""
    png = _card([(100, 400), (450, 880)])
    a = audit_card(png, 3)
    assert not a.ok
    assert 3 in a.dead_thirds
    assert "하단" in a.as_note()


def test_hole_between_elements_is_caught():
    """구획은 다 찼지만 요소 사이가 통째로 빈 경우(클로드 디자인 자체 루프가 놓친 유형)."""
    png = _card([(80, 300), (760, 900), (1150, 1280)])   # 300~760 = 34% 구멍
    a = audit_card(png, 6)
    assert not a.ok
    assert a.largest_gap > 0.18
    assert a.gap_at is not None
    assert "구멍" in a.as_note()


def test_notes_only_for_bad_cards():
    good = _card([(100, 400), (500, 850), (950, 1250)])
    bad = _card([(100, 400)])
    audits, notes = audit_deck([good, bad, good])
    assert len(audits) == 3
    assert len(notes) == 1
    assert notes[0].startswith("카드 02")
