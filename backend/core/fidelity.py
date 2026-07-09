# -*- coding: utf-8 -*-
"""V — Fidelity Verify (헌법 v3.0 §2).

저작(S6)이 자유롭게 만든 덱 HTML의 모든 '콘텐츠 수치'를 원문과 대조한다.
해자의 핵심: 막지 않고 **출처를 분류·표면화**한다. 최종 판단은 사용자(헌법 3조).

분류:
  VERIFIED   — 수치가 원문에 존재 (논문 근거)
  UNVERIFIED — 원문에 없음 → 사용자 판단 필요 (AI가 더한 맥락 / 예시 / 오류 중 하나)

★ 핵심 설계 1: CSS(스타일·OKLCH 토큰)는 검증에서 제외한다. 콘텐츠 텍스트의 수치만 본다.
   (이전 순진한 grep이 oklch(95.5% ...) 같은 디자인 토큰을 오탐한 교훈.)

★ 핵심 설계 2 (2026-07-09): 해자는 **정량 수치(quantity)**만 추적한다.
   = 단위(%, mV, μm, M, h, mg, 배 …) 또는 소수점을 동반한 측정값.
   맨정수(단위·소수 없음)는 저널 권번호(372)·연도(2026)·페이지번호(01/07)·아티클id(124526)
   같은 서지/네비게이션 노이즈라 claim에서 제외한다. 헌법 §1 "numbers and statistics"와 정합.
   → "숫자 다 긁는 정규식"처럼 보이던 문제 시정. 신뢰 가는 원장(ledger)만 남긴다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NumberClaim:
    value: str          # 카드에 쓰인 정량 수치 토큰 (예: "28.4", "19.36 ± 0.96 %", "+49.3 mV")
    context: str        # 그 수치 주변 콘텐츠 한 토막 (사용자 판단용, 단어 경계로 정리)
    verified: bool      # 원문에 존재?


_STYLE_BLOCK = re.compile(r"<style[^>]*>.*?</style>", re.S | re.I)
_STYLE_ATTR = re.compile(r'\sstyle="[^"]*"', re.I)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")

# 과학·정량 단위 (분야: 고분자·화학·생물·물리). ASCII 단위는 뒤에 글자가 이어지면 단위 아님(예: "28.4 BLEU").
_UNIT = (
    r"%p|%|‰|"
    r"mV|kV|μV|µV|V|mA|μA|µA|nA|A|Ω|"
    r"nm|μm|µm|um|mm|cm|km|Å|"
    r"mM|μM|µM|nM|pM|mmol|μmol|µmol|mol|M|"
    r"mg|μg|µg|ng|pg|kg|g|"
    r"mL|ml|μL|µL|dL|L|"
    r"kPa|MPa|GPa|Pa|bar|"
    r"℃|°C|"
    r"kDa|Da|rpm|kHz|MHz|Hz|"
    r"ms|μs|µs|ns|min|h|"
    r"배|점|개|층|일|시간|주|개월|년|억|만"
)
# 정량 수치: 숫자(부호·콤마) + 선택적 ±오차(한 claim으로) + 선택적 단위(복합 /cm² 허용).
_NUM = re.compile(
    r"[+\-−]?\d[\d,]*\.?\d*"
    r"(?:\s*±\s*\d[\d,]*\.?\d*)?"
    r"(?:\s?(?:" + _UNIT + r")(?:\s?/\s?[A-Za-zμµ²³]+|[²³])?(?![A-Za-z]))?"
)
_CORE = re.compile(r"\d[\d,]*\.?\d*")


def _content_text(html: str) -> str:
    """HTML에서 CSS(스타일 블록·style 속성)를 걷어내고 콘텐츠 텍스트만 추출."""
    h = _STYLE_BLOCK.sub(" ", html)
    h = _STYLE_ATTR.sub(" ", h)          # 인라인 style="..." (OKLCH 토큰 등) 제거 — 오탐 차단
    h = _TAG.sub(" ", h)
    return _WS.sub(" ", h).strip()


def _flat(s: str) -> str:
    return _WS.sub("", s)


def _is_meaningful(tok: str) -> bool:
    """정량 수치(단위 또는 소수점 동반)인가. 맨정수(권/연도/페이지/id 노이즈)는 제외."""
    t = tok.strip()
    if "." in t:
        return True
    # 숫자·부호·콤마·±·공백을 뺀 나머지 문자 = 단위. 남으면 정량 수치.
    return bool(re.sub(r"[\d,.\s±+\-−]", "", t))


def _clean_context(content: str, start: int, end: int) -> str:
    """수치 주변 한 토막을 단어 경계로 정리(부분단어 잘림 방지)."""
    lo, hi = max(0, start - 40), min(len(content), end + 40)
    ctx = content[lo:hi]
    if lo > 0:
        ctx = re.sub(r"^\S*\s", "", ctx, count=1)        # 앞 부분단어 제거
    if hi < len(content):
        ctx = re.sub(r"\s\S*$", "", ctx, count=1)        # 뒤 부분단어 제거
    return _WS.sub(" ", ctx).strip()


def verify_deck(html: str, paper_text: str) -> list[NumberClaim]:
    """덱 HTML의 정량 수치를 원문과 대조해 NumberClaim 리스트 반환."""
    content = _content_text(html)
    paper_flat = _flat(paper_text)
    seen: set[str] = set()
    claims: list[NumberClaim] = []
    for m in _NUM.finditer(content):
        tok = m.group().strip()
        if not _is_meaningful(tok) or tok in seen:
            continue
        seen.add(tok)
        # 주 수치 코어(첫 숫자 런, 콤마 제거)로 원문 대조 — 단위 표기 차이에 견고
        cm = _CORE.search(tok)
        core = cm.group().replace(",", "") if cm else ""
        verified = bool(core) and (core in paper_text or core in paper_flat)
        claims.append(NumberClaim(value=tok, context=_clean_context(content, m.start(), m.end()), verified=verified))
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
