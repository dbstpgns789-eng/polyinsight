# -*- coding: utf-8 -*-
"""DEV_MOCK_LLM 시 저작 대체 — 레퍼런스 HTML 덱을 반환(무비용 e2e 배관 검증용)."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]

# 네온 방향(SVG 포함)을 우선 — 렌더/검증 배관을 가장 빡세게 검증.
_MOCK_REFS = [
    "output/cardnews_attention_neon/cards.html",
    "output/cardnews_bert_design/cards.html",
    "output/cardnews_attention/cards.html",
]

_FALLBACK = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>'
    '<div data-screen-label="01" style="width:1080px;height:1350px;background:#0A0E1A;'
    'color:#EAF0FF;padding:80px;box-sizing:border-box;font-family:sans-serif;">'
    '<div style="font-size:80px;font-weight:800;">Mock Deck</div>'
    '<div style="margin-top:30px;font-size:32px;">BLEU 28.4 · 원문 기반</div></div>'
    '</body></html>'
)


def mock_deck_html(card_count: int = 7) -> str:
    for rel in _MOCK_REFS:
        p = _ROOT / rel
        if p.exists():
            return p.read_text(encoding="utf-8")
    return _FALLBACK
