# -*- coding: utf-8 -*-
"""AI 디자이너 편집 스펙(ops) 적용 코어 테스트 — apply_ops / parse_ops.

정본 docs/contracts/25 + 스펙 §11. LLM 없이 순수 함수만(무비용).
"""
from backend.agents.deck.edit_ops import apply_ops, parse_ops


def _card(inner: str) -> str:
    return f'<!DOCTYPE html><html><body><div data-screen-label="01">{inner}</div></body></html>'


# ── apply_ops: style ──────────────────────────────────────────────────────
def test_style_merges_into_existing_inline():
    html = _card('<div data-eid="e1" style="color: #111; font-size: 40px">제목</div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "style", "style": {"text-shadow": "0 1px 3px rgba(0,0,0,.35)"}}])
    assert n == 1
    assert "text-shadow: 0 1px 3px rgba(0,0,0,.35)" in out
    assert "color: #111" in out and "font-size: 40px" in out   # 기존 보존


def test_style_same_prop_overwrites():
    html = _card('<div data-eid="e1" style="color: #111">제목</div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "style", "style": {"color": "#e33"}}])
    assert n == 1
    assert "color: #e33" in out and "#111" not in out


def test_style_whitelist_blocks_layout_props():
    html = _card('<div data-eid="e1" style="color: #111">제목</div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "style", "style": {"position": "fixed", "display": "none"}}])
    assert n == 0                       # 허용 밖 → 미적용 → 무과금
    assert "position: fixed" not in out and "display: none" not in out


def test_style_and_disallowed_mixed_applies_allowed_only():
    html = _card('<div data-eid="e1" style="">제목</div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "style", "style": {"color": "#e33", "position": "absolute"}}])
    assert n == 1
    assert "color: #e33" in out and "position" not in out


# ── apply_ops: text ───────────────────────────────────────────────────────
def test_text_replaces_pure_leaf():
    html = _card('<div data-eid="e1">긴 제목입니다</div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "text", "text": "짧은 제목"}])
    assert n == 1
    assert "짧은 제목" in out and "긴 제목입니다" not in out


def test_text_allows_inline_children_leaf():
    html = _card('<div data-eid="e1">코팅 하나로 <b>32.7배</b></div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "text", "text": "새 제목"}])
    assert n == 1                        # 인라인 자식은 리프로 허용(통째 교체)
    assert "새 제목" in out


def test_text_skips_block_children():
    html = _card('<div data-eid="e1"><div>자식블록</div></div>')
    out, n = apply_ops(html, [{"eid": "e1", "op": "text", "text": "덮어쓰기"}])
    assert n == 0                        # 블록 자식 있으면 거부 → 무과금
    assert "자식블록" in out and "덮어쓰기" not in out


# ── apply_ops: 카운트/안전 ──────────────────────────────────────────────────
def test_bad_eid_skipped_zero_applied():
    html = _card('<div data-eid="e1">제목</div>')
    out, n = apply_ops(html, [{"eid": "e999", "op": "style", "style": {"color": "#e33"}}])
    assert n == 0                        # 미발견 → 무과금(스펙 §11-1)
    assert out == html or "data-screen-label" in out


def test_empty_ops_no_change():
    html = _card('<div data-eid="e1">제목</div>')
    out, n = apply_ops(html, [])
    assert n == 0 and out == html


def test_partial_apply_counts_only_applied():
    html = _card('<div data-eid="e1">제목</div><span data-eid="e2">부제</span>')
    out, n = apply_ops(html, [
        {"eid": "e1", "op": "style", "style": {"color": "#e33"}},
        {"eid": "eX", "op": "style", "style": {"color": "#000"}},   # 미발견
    ])
    assert n == 1


# ── apply_ops: SVG 충실성 (적대적 검증 #6) ──────────────────────────────────
def test_inline_svg_survives_apply():
    svg = '<svg viewBox="0 0 100 100"><path d="M10 10 L90 90" stroke="#f80"/><circle cx="50" cy="50" r="8"/></svg>'
    html = _card(f'<div data-eid="e1">제목</div>{svg}')
    out, n = apply_ops(html, [{"eid": "e1", "op": "style", "style": {"color": "#e33"}}])
    assert n == 1
    # SVG 내부 도형·속성이 보존돼야(mangle 금지)
    assert 'd="M10 10 L90 90"' in out
    assert 'viewBox="0 0 100 100"' in out
    assert "<circle" in out and 'r="8"' in out


# ── parse_ops ─────────────────────────────────────────────────────────────
def test_parse_valid():
    raw = '{"summary": "그림자 추가", "ops": [{"eid": "e1", "op": "style", "style": {"text-shadow": "x"}}]}'
    summary, ops = parse_ops(raw)
    assert summary == "그림자 추가" and len(ops) == 1 and ops[0]["eid"] == "e1"


def test_parse_fenced_or_prefixed():
    raw = '설명 텍스트\n```json\n{"summary": "s", "ops": []}\n```'
    summary, ops = parse_ops(raw)
    assert summary == "s" and ops == []


def test_parse_broken_json_graceful():
    summary, ops = parse_ops("이건 JSON이 아니에요")
    assert ops == [] and "이해" in summary        # graceful → 무변경·무과금


def test_parse_missing_ops_key():
    summary, ops = parse_ops('{"summary": "s"}')
    assert ops == [] and summary == "s"
