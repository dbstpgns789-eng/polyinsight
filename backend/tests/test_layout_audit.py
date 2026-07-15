# -*- coding: utf-8 -*-
"""레이아웃 감사 — 코드는 **측정**만, 판정은 저작자가(§1).

재캘리브레이션(2026-07-14):
  1차 기준("내부 공백 >18% = 구멍")은 **호흡을 결함으로 오인**했다. 실측이 반증:
    클로드 디자인 14장 — 내부 공백 8~20%로 흩어지지만 무게중심 0.43~0.57 (전부 균형, 발행급)
    우리 파이프라인   — 무게중심 0.27~0.70 (쏠림). 육안 확인: 본문과 차트 사이 24%가 통째로 비어
                        미완성으로 읽힘(authored_runs/cardnews_resnet/card_02)
  → 판정해야 할 것은 "빈 곳이 있나"가 아니라 **"잉크가 쏠렸나"**다.
"""
import io

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


def test_balanced_card_passes():
    a = audit_card(_card([(100, 400), (500, 850), (950, 1250)]), 1)
    assert a.ok
    assert 0.40 < a.center_of_mass < 0.60


def test_intentional_whitespace_is_not_a_defect():
    """헤드라인 → **큰 여백** → 초점 오브젝트 → 캡션. 균형 잡혀 있으면 결함이 아니다.

    이 케이스가 1차 기준에서 오검출됐다(공백 22% > 18%). 여백은 호흡일 수 있다.
    """
    a = audit_card(_card([(90, 330), (620, 980), (1150, 1270)]), 2)
    assert a.largest_gap > 0.18          # 큰 공백이 있는 건 맞다
    assert a.ok                          # 그러나 균형 잡혀 있으므로 결함이 아니다
    assert a.as_note() == ""


def test_top_heavy_is_flagged():
    """위에 몰리고 아래가 빈 카드 = 요소가 갈 곳을 못 찾은 미완성."""
    a = audit_card(_card([(80, 520)]), 3)
    assert not a.ok
    assert a.center_of_mass < 0.38
    assert "위쪽" in a.as_note()


def test_bottom_heavy_is_flagged():
    """실측 사례(우리 resnet 카드2): 본문 위 · 차트 아래 · 가운데 구멍 → 무게중심 0.69."""
    a = audit_card(_card([(60, 200), (900, 1300)]), 4)
    assert not a.ok
    assert a.center_of_mass > 0.62
    assert "아래쪽" in a.as_note()


def test_empty_third_is_flagged():
    a = audit_card(_card([(100, 400), (450, 880)]), 5)
    assert not a.ok
    assert 3 in a.dead_thirds
    assert "하단" in a.as_note()


def test_notes_only_for_bad_cards():
    good = _card([(100, 400), (500, 850), (950, 1250)])
    bad = _card([(80, 520)])
    audits, notes = audit_deck([good, bad, good])
    assert len(audits) == 3
    assert len(notes) == 1
    assert notes[0].startswith("카드 02")


def test_corrupt_png_is_soft():
    """감사는 보조 신호다 — 터져도 저작(비싼 것)을 죽이지 않는다."""
    audits, notes = audit_deck([b"not-a-png", _card([(100, 400), (500, 850), (950, 1250)])])
    assert len(audits) == 1          # 손상된 것만 건너뜀
    assert notes == []
