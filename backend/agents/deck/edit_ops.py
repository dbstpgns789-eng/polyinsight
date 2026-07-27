# -*- coding: utf-8 -*-
"""AI 디자이너 편집 스펙(ops) 적용 — LLM이 뱉은 최소 편집 스펙을 결정적으로 html에 적용.

정본 정의 docs/contracts/25 + 스펙 docs/superpowers/specs/2026-07-24-ai-designer-edit-spec.md(§11).
LLM은 전체 HTML을 재출력하지 않는다. {summary, ops:[{eid, op, style|text}]}만 뱉고, 여기서
data-eid로 요소를 찾아 인라인 style 병합 / text 교체한다. 반환에 '적용 건수'를 담아 0건이면
호출자가 무과금 처리한다(스펙 §11-1: 실패/무변경도 과금되던 버그 차단).
"""
from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ★SVG 보호: bs4/html.parser는 SVG의 case-sensitive 속성(viewBox 등)을 소문자화해 그래픽을
# 깨뜨린다(적대적 검증 #6, 실측 확증). 파싱 전 <svg>…</svg>를 통째 치환보호하고 끝에 복원한다
# → SVG는 바이트 보존, HTML 부분만 bs4가 견고하게 처리. (SVG 루트 자체의 style op은 v1 미지원 —
# SVG 조작은 직접조작 편집기 담당, §25.6. 치환된 svg는 eid로 안 잡혀 graceful하게 무시된다.)
_SVG_RE = re.compile(r"<svg\b.*?</svg>", re.DOTALL | re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r'<pi-svg data-i="(\d+)"></pi-svg>')

# style op 허용 속성(화이트리스트, 스펙 §11-5). 색·서체·그림자·배경·정렬·간격·크기·투명도·모서리.
# 레이아웃 구조(position/display/transform/float/width/height 등)는 직접조작 편집기 담당이라 거부.
_STYLE_ALLOW = {
    "color", "background", "background-color", "background-image",
    "font-size", "font-weight", "font-style", "font-family",
    "text-align", "text-shadow", "letter-spacing", "line-height",
    "opacity", "border-radius", "text-decoration", "text-transform",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
}

# text op에서 '순수 텍스트 아님'으로 보는 블록 자식(있으면 텍스트 교체 거부). 인라인(span/b/i/em/br)은 허용.
_BLOCK_CHILDREN = ["div", "section", "svg", "img", "ul", "ol", "table",
                   "figure", "canvas", "p", "h1", "h2", "h3", "h4", "header", "footer"]

_FAIL_SUMMARY = "이해하지 못했어요. 조금 더 구체적으로 말해 주세요."


def parse_ops(raw: str) -> tuple[str, list[dict]]:
    """LLM 원문 → (summary, ops). JSON 파싱/구조 실패 시 graceful: (설명, []) → 무변경·무과금."""
    text = (raw or "").strip()
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        logger.warning("parse_ops: JSON 오브젝트 없음")
        return (_FAIL_SUMMARY, [])
    try:
        d = json.loads(text[a:b + 1])
    except Exception as e:
        logger.warning("parse_ops: JSON 파싱 실패 %s", e)
        return (_FAIL_SUMMARY, [])
    if not isinstance(d, dict):
        return (_FAIL_SUMMARY, [])
    summary = (str(d.get("summary") or "").strip()) or "편집 제안"
    ops = d.get("ops")
    return (summary, ops if isinstance(ops, list) else [])


def _parse_style(s: str) -> dict:
    out: dict[str, str] = {}
    for decl in (s or "").split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def _fmt_style(d: dict) -> str:
    body = "; ".join(f"{k}: {v}" for k, v in d.items() if v)
    return (body + ";") if body else ""


def apply_ops(html: str, ops: list[dict]) -> tuple[str, int]:
    """ops를 html에 적용 → (수정된 html, 적용 건수).

    - style op: [data-eid]의 인라인 style에 병합(같은 속성 덮어씀). 화이트리스트 밖 속성은 무시.
    - text op: 블록 자식이 없을 때만 텍스트 교체(인라인 span/b/i/em/br는 허용, innerText 통째 교체).
    - eid 없음/미발견/블록자식 text 등은 무시(적용 건수 미포함) → 호출자가 0건이면 무과금.
    """
    if not ops:
        return html, 0
    svgs: list[str] = []

    def _stash(m: "re.Match") -> str:
        svgs.append(m.group(0))
        return f'<pi-svg data-i="{len(svgs) - 1}"></pi-svg>'

    protected = _SVG_RE.sub(_stash, html)
    soup = BeautifulSoup(protected, "html.parser")
    applied = 0
    for op in ops:
        if not isinstance(op, dict):
            continue
        eid = op.get("eid")
        kind = op.get("op")
        if not eid:
            continue
        el = soup.find(attrs={"data-eid": str(eid)})
        if el is None:
            logger.info("apply_ops: eid=%s 미발견, skip", eid)
            continue
        if kind == "style":
            style = op.get("style")
            if not isinstance(style, dict) or not style:
                continue
            cur = _parse_style(el.get("style", ""))
            changed = False
            for prop, val in style.items():
                p = str(prop).strip().lower()
                if p in _STYLE_ALLOW and val is not None and str(val).strip():
                    cur[p] = str(val).strip()
                    changed = True
            if changed:
                el["style"] = _fmt_style(cur)
                applied += 1
        elif kind == "text":
            new_text = op.get("text")
            if new_text is None:
                continue
            if el.find(_BLOCK_CHILDREN):     # 블록 자식 있으면 텍스트 교체 위험 → 무시(스펙 §11-3)
                logger.info("apply_ops: text op가 순수 리프 아님(eid=%s), skip", eid)
                continue
            el.string = str(new_text)        # 인라인 자식 통째 교체(강조 소실 감수, v1)
            applied += 1
    out = str(soup)
    out = _PLACEHOLDER_RE.sub(lambda m: svgs[int(m.group(1))], out)   # SVG 원형 복원
    return (out, applied)
