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


# ── V2: 파생수치 산수 정합 (2026-07-11) ──────────────────────────────────────
# 배경: 저작이 "142→238"을 '약 170% 증가'로 오기(1.7배와 %증가 혼동) — 원문 대조(존재)로는
# 못 잡는 내부 모순이다(142·238·170 다 원문에 있으면 V1은 전부 VERIFIED로 통과시킨다).
# 카드 단위로 파생표현(N% 증가·N배)을 찾아 같은 카드의 수치쌍과 검산한다.

_CARD_SPLIT = re.compile(r'(?=<div[^>]+data-screen-label=)', re.I)
_PCT_CHANGE = re.compile(r"(\d[\d,]*\.?\d*)\s*%\s*(증가|감소|향상|개선|절감|상승|하락)")
_FOLD = re.compile(r"(\d[\d,]*\.?\d*)\s*배")
_PCT_TOL = 5.0      # % 스케일 절대 오차 허용
_FOLD_TOL = 0.15    # 배 스케일 절대 오차 허용

# 검산쌍에서 뺄 크롬 노이즈. 프롬프트가 페이지번호(01/07)를 전 카드에 강제하므로 (1,7) 같은
# 가짜 쌍이 상시 생긴다 → 틀린 주장을 '정합'으로 세탁하거나 정당한 주장을 suspect로 만든다.
# (verify_deck이 맨정수를 노이즈로 제외한 ★핵심 설계 2와 같은 이유. 단 여기선 맨정수를 전면
#  제외할 수 없다 — 142/238처럼 단위 없는 맨정수가 정당한 근거쌍인 경우가 있다. 표적 제외만.)
_PAGINATION = re.compile(r"\b\d{1,2}\s*/\s*\d{1,2}\b")


def _card_numbers(text: str) -> list[float]:
    """카드 본문의 검산 가능한 숫자. 페이지네이션·연도(1900~2100)는 제외."""
    cleaned = _PAGINATION.sub(" ", text)
    out: list[float] = []
    for m in _CORE.finditer(cleaned):
        raw = m.group()
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if v <= 0:
            continue
        if "." not in raw and 1900 <= v <= 2100:   # 연도 — 쌍이 되면 비율이 ≈100%라 오탐 유발
            continue
        out.append(v)
    return out


def _check_pairs(nums: list[float], claimed: float, kind: str) -> tuple[bool, bool]:
    """(suspect, unresolved). 같은 카드 수치쌍 (a<b)의 비율과 주장값을 대조.

    - pct_change: (b/a-1)*100 ≈ claimed 면 정합. b/a*100 ≈ claimed 인데 위가 아니면 혼동 의심.
    - fold: b/a ≈ claimed 면 정합.
    비교쌍이 하나도 없으면 unresolved=True — 모르면 죄 아님(막지 않는다).
    """
    pairs = [(min(a, b), max(a, b))
             for i, a in enumerate(nums) for b in nums[i + 1:] if a != b]
    # 주장값 자신은 비교쌍에서 제외 (170이 카드 안 숫자로 다시 잡히는 자기참조 방지)
    pairs = [(a, b) for a, b in pairs if a != claimed and b != claimed]
    if not pairs:
        return False, True
    if kind == "fold":
        ok = any(abs(b / a - claimed) <= _FOLD_TOL for a, b in pairs)
        if ok:
            return False, False
        confusion = any(abs((b / a - 1) - claimed) <= _FOLD_TOL for a, b in pairs)
        return confusion, not confusion
    # pct_change
    if any(abs((b / a - 1) * 100 - claimed) <= _PCT_TOL for a, b in pairs):
        return False, False
    confusion = any(abs(b / a * 100 - claimed) <= _PCT_TOL for a, b in pairs)
    return confusion, not confusion


def derived_claims(html: str, paper_text: str) -> list[dict]:
    """카드별 파생수치(N% 증가·N배)를 같은 카드 수치쌍과 검산.

    반환: [{value, kind, suspect, unresolved, verified, context}]
    suspect=True → 사용자에게 '계산 불일치' 표면화(막지 않음, 헌법 3조).
    """
    results: list[dict] = []
    for chunk in _CARD_SPLIT.split(html):
        if "data-screen-label" not in chunk:
            continue
        content = _content_text(chunk)
        nums = _card_numbers(content)
        for pat, kind in ((_PCT_CHANGE, "pct_change"), (_FOLD, "fold")):
            for m in pat.finditer(content):
                claimed = float(m.group(1).replace(",", ""))
                suspect, unresolved = _check_pairs(nums, claimed, kind)
                core = m.group(1).replace(",", "")
                results.append({
                    "value": m.group().strip(),
                    "kind": kind,
                    "suspect": suspect,
                    "unresolved": unresolved,
                    "verified": core in _flat(paper_text),
                    "context": _clean_context(content, m.start(), m.end()),
                })
    return results


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
