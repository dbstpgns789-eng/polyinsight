# -*- coding: utf-8 -*-
"""claim에 카드 위치(card 인덱스)가 붙는가 — 팩트 패널 '클릭→그 카드로 점프'의 전제."""
from backend.core.fidelity import derived_claims, verify_deck

DECK = """
<div data-screen-label="01" style="width:1080px">
  <h1>표면 전위는 49.3 mV 였다</h1>
</div>
<div data-screen-label="02" style="width:1080px">
  <p>인장강도가 142에서 238 MPa로, 약 1.7배 늘었다</p>
</div>
"""
PAPER = "surface potential 49.3 mV ... tensile strength 142 to 238 MPa (1.7-fold)"


def test_claim_carries_card_index():
    claims = verify_deck(DECK, PAPER)
    by_value = {c.value: c.card for c in claims}
    assert by_value["49.3 mV"] == 0
    assert by_value["238 MPa"] == 1


def test_duplicate_value_keeps_first_card_and_no_extra_claims():
    # 같은 수치가 두 카드에 나와도 claim은 한 번만(전역 dedup 유지) — 원장 카운트 회귀 방지
    deck = DECK + '<div data-screen-label="03"><p>다시 49.3 mV</p></div>'
    claims = verify_deck(deck, PAPER)
    hits = [c for c in claims if c.value == "49.3 mV"]
    assert len(hits) == 1
    assert hits[0].card == 0          # 첫 등장 카드


def test_derived_claim_carries_card_index():
    derived = derived_claims(DECK, PAPER)
    fold = [d for d in derived if d["kind"] == "fold"]
    assert fold and fold[0]["card"] == 1


def test_html_without_card_markers_yields_card_none():
    # 카드 분할 마커가 없는 HTML(구 저작물/조각) — 죽지 않고 card=None
    claims = verify_deck("<p>49.3 mV</p>", PAPER)
    assert claims and claims[0].card is None


def test_compute_verify_payload_includes_card():
    from backend.agents.deck.pipeline import compute_verify
    payload = compute_verify(DECK, PAPER)
    cards = {c["value"]: c["card"] for c in payload["claims"]}
    assert cards["49.3 mV"] == 0
    assert cards["238 MPa"] == 1
