# -*- coding: utf-8 -*-
"""V — Fidelity Verify (헌법 v3.0 §2).

저작(S6)이 자유롭게 만든 덱 HTML의 모든 '콘텐츠 수치'를 원문과 대조한다.
해자의 핵심: 막지 않고 **출처를 분류·표면화**한다. 최종 판단은 사용자(헌법 3조).

분류:
  VERIFIED   — 수치가 원문에 존재 (논문 근거)
  UNVERIFIED — 원문에 없음 → 사용자 판단 필요 (AI가 더한 맥락 / 예시 / 오류 중 하나)

★ 핵심 설계: CSS(스타일·OKLCH 토큰)는 검증에서 제외한다. 콘텐츠 텍스트의 수치만 본다.
   (이전 순진한 grep이 oklch(95.5% ...) 같은 디자인 토큰을 오탐한 교훈.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NumberClaim:
    value: str          # 카드에 쓰인 수치 토큰 (예: "28.4", "175B", "2018")
    context: str        # 그 수치 주변 콘텐츠 한 토막 (사용자 판단용)
    verified: bool      # 원문에 존재?


_STYLE_BLOCK = re.compile(r"<style[^>]*>.*?</style>", re.S | re.I)
_STYLE_ATTR = re.compile(r'\sstyle="[^"]*"', re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# 의미 있는 수치: 소수, 2자리+ 정수, 단위 접미(%, B, M, 일, 배, 점 등) 포함 토큰.
# 단위 묶음은 '숫자 바로 뒤 한 칸까지'만, B/M/K는 뒤에 글자가 이어지면 단위 아님(예: "28.4 BLEU"의 B 제외).
_NUM = re.compile(
    r"\d[\d,]*\.?\d*(?:\s?(?:%p|%|일|시간|배|점|개|층|억|만|[BMK](?![A-Za-z])))?"
)


def _content_text(html: str) -> str:
    """HTML에서 CSS(스타일 블록·style 속성)를 걷어내고 콘텐츠 텍스트만 추출."""
    h = _STYLE_BLOCK.sub(" ", html)
    h = _STYLE_ATTR.sub(" ", h)          # 인라인 style="..." (OKLCH 토큰 등) 제거 — 오탐 차단
    h = _TAG.sub(" ", h)
    return _WS.sub(" ", h).strip()


def _flat(s: str) -> str:
    return _WS.sub("", s)


def _is_meaningful(tok: str) -> bool:
    """검증 대상 수치인가. 한 자리 정수·페이지번호성 토큰은 노이즈로 제외."""
    digits = re.sub(r"[^\d]", "", tok)
    if not digits:
        return False
    has_unit = bool(re.search(r"(%p|%|B|M|K|일|시간|배|점|개|층|억|만)$", tok.strip()))
    has_dot = "." in tok
    return has_unit or has_dot or len(digits) >= 2


def verify_deck(html: str, paper_text: str) -> list[NumberClaim]:
    """덱 HTML의 콘텐츠 수치를 원문과 대조해 NumberClaim 리스트 반환."""
    content = _content_text(html)
    paper_flat = _flat(paper_text)
    seen: set[str] = set()
    claims: list[NumberClaim] = []
    for m in _NUM.finditer(content):
        tok = m.group().strip()
        if not _is_meaningful(tok) or tok in seen:
            continue
        seen.add(tok)
        # 숫자 코어(단위·콤마 제거)로 원문 대조 — 단위 표기 차이에 견고
        core = re.sub(r"[,\s]", "", re.sub(r"(%p|%|B|M|K|일|시간|배|점|개|층|억|만)$", "", tok))
        verified = bool(core) and (core in paper_text or core in paper_flat)
        ctx = content[max(0, m.start() - 32): m.end() + 24].strip()
        claims.append(NumberClaim(value=tok, context=ctx, verified=verified))
    return claims


def report(claims: list[NumberClaim]) -> str:
    """사람이 읽는 검증 리포트. UNVERIFIED는 사용자 판단용으로 맥락과 함께 노출."""
    ok = [c for c in claims if c.verified]
    bad = [c for c in claims if not c.verified]
    lines = [f"검증됨(논문 근거) {len(ok)}건 / 사용자 판단 필요 {len(bad)}건", ""]
    if bad:
        lines.append("⚠️  원문에 없는 수치 — AI가 더한 맥락/예시인지, 오류인지 사용자가 판단:")
        for c in bad:
            lines.append(f"   · {c.value:>8}  …{c.context}…")
        lines.append("")
    lines.append("✅ 원문 추적된 수치: " + ", ".join(c.value for c in ok))
    return "\n".join(lines)
