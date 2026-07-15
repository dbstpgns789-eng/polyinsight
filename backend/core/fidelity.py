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
    card: int | None = None   # 이 수치가 처음 등장한 카드 인덱스(0-기반). 분할 마커 없으면 None


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
_CARD_SPLIT = re.compile(r'(?=<div[^>]+data-screen-label=)', re.I)

# 서지 식별자 — 수치 주장이 아니다(arXiv ID·DOI). "소수점=수치"라는 순진한 규칙에 뚫린다.
_IDENTIFIER = re.compile(r"^(?:\d{4}\.\d{4,5}|10\.\d{4,}(?:/|$))")   # 2005.14165 / 10.1234/...
# 과학표기(3.64E+03) — 원문이 이렇게 쓰면 카드의 "3,640"과 문자열이 안 맞는다.
_SCI = re.compile(r"(\d(?:\.\d+)?)\s*[eE]\s*([+\-]?\d+)")
# 한국어 큰수 접미사 → 10의 지수. "1,750억"=175 billion을 영어 원문과 잇는다.
_KO_MAG = {"조": 12, "억": 8, "만": 4}


def _expand_scientific(text: str) -> str:
    """원문의 과학표기를 평문 정수로 확장해 붙인다(원본은 유지, 확장본을 뒤에 이어 검색 대상 확대).

    3.64E+03 → 3640. 카드가 재표현한 '3,640'이 문자열 대조로 잡히게 한다.
    """
    extra: list[str] = []
    for m in _SCI.finditer(text):
        try:
            v = float(m.group(1)) * (10 ** int(m.group(2)))
            if v == int(v):
                extra.append(str(int(v)))
        except (ValueError, OverflowError):
            continue
    return text + (" " + " ".join(extra) if extra else "")


def _korean_magnitude_reprs(tok: str) -> list[str]:
    """'1,750억' → 원문에 나타날 법한 후보 표현들. 없으면 빈 리스트.

    영어 논문은 "175 billion"으로 쓴다 → 175000000000을 10^9·10^8·10^6·10^4로 나눈
    유효숫자 후보를 만들어 어느 하나가 원문에 있으면 매칭으로 본다.
    """
    exp = next((e for s, e in _KO_MAG.items() if tok.endswith(s)), None)
    if exp is None:
        return []
    cm = _CORE.search(tok)
    if not cm:
        return []
    try:
        base = float(cm.group().replace(",", ""))
    except ValueError:
        return []
    full = int(base * (10 ** exp))
    reprs = {str(full)}
    for div in (10 ** 9, 10 ** 8, 10 ** 6, 10 ** 4):     # billions / 억 / millions / 만
        if full % div == 0 and full // div >= 1:
            reprs.add(str(full // div))
    return list(reprs)


def _content_text(html: str) -> str:
    """HTML에서 CSS(스타일 블록·style 속성)를 걷어내고 콘텐츠 텍스트만 추출."""
    h = _STYLE_BLOCK.sub(" ", html)
    h = _STYLE_ATTR.sub(" ", h)          # 인라인 style="..." (OKLCH 토큰 등) 제거 — 오탐 차단
    h = _TAG.sub(" ", h)
    return _WS.sub(" ", h).strip()


def _card_contents(html: str) -> list[tuple[int | None, str]]:
    """덱 HTML → [(카드 인덱스, 그 카드의 콘텐츠 텍스트)].

    분할 마커(data-screen-label)가 없으면 [(None, 전체 텍스트)] — 구 저작물/조각에서도 죽지 않는다.
    """
    chunks = [c for c in _CARD_SPLIT.split(html) if "data-screen-label" in c]
    if not chunks:
        return [(None, _content_text(html))]
    return [(i, _content_text(c)) for i, c in enumerate(chunks)]


def _flat(s: str) -> str:
    return _WS.sub("", s)


def _is_meaningful(tok: str) -> bool:
    """정량 수치(단위 또는 소수점 동반)인가. 맨정수·서지식별자(권/연도/페이지/arXiv/DOI)는 제외."""
    t = tok.strip()
    if _IDENTIFIER.match(t):        # arXiv ID·DOI — 소수점이 있어도 수치 주장이 아니다
        return False
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
    """덱 HTML의 정량 수치를 원문과 대조해 NumberClaim 리스트 반환.

    카드(data-screen-label) 단위로 순회해 각 claim에 첫 등장 카드 인덱스를 붙인다 —
    팩트 패널이 '이 수치가 쓰인 카드'로 사용자를 데려갈 수 있게 하는 좌표다.
    dedup은 덱 전역(seen)으로 유지한다 — 원장 카운트를 바꾸지 않는다(위치만 덧붙이는 작업).
    """
    paper_exp = _expand_scientific(paper_text)      # 3.64E+03 → 3640 도 검색 대상에 포함
    paper_flat = _flat(paper_exp)
    seen: set[str] = set()
    claims: list[NumberClaim] = []

    for card_idx, content in _card_contents(html):
        for m in _NUM.finditer(content):
            tok = m.group().strip()
            if not _is_meaningful(tok) or tok in seen:
                continue
            seen.add(tok)
            cm = _CORE.search(tok)
            core = cm.group().replace(",", "") if cm else ""
            verified = bool(core) and (core in paper_exp or core in paper_flat)
            if not verified:                        # 한국어 만/억 표기 → 영어/과학표기 원문과 대조
                verified = any(r in paper_flat for r in _korean_magnitude_reprs(tok))
            claims.append(NumberClaim(
                value=tok,
                context=_clean_context(content, m.start(), m.end()),
                verified=verified,
                card=card_idx,
            ))
    return claims


# ── V2: 파생수치 산수 정합 (2026-07-11) ──────────────────────────────────────
# 배경: 저작이 "142→238"을 '약 170% 증가'로 오기(1.7배와 %증가 혼동) — 원문 대조(존재)로는
# 못 잡는 내부 모순이다(142·238·170 다 원문에 있으면 V1은 전부 VERIFIED로 통과시킨다).
# 카드 단위로 파생표현(N% 증가·N배)을 찾아 같은 카드의 수치쌍과 검산한다.

_PCT_CHANGE = re.compile(r"(\d[\d,]*\.?\d*)\s*%\s*(증가|감소|향상|개선|절감|상승|하락)")
_FOLD = re.compile(r"(\d[\d,]*\.?\d*)\s*배")
# 퍼센트 '차이'(%p) — "2.8% 더 정확", "3.5% 낮췄다". 증가율이 아니라 뺄셈이다.
_PCT_POINT = re.compile(r"(\d[\d,]*\.?\d*)\s*%\s*(?:더|덜|만큼)?\s*(정확|낮|높|줄|늘|개선|앞서|우수|나빠)")
_PCT_TOL = 5.0      # % 스케일 절대 오차 허용
_FOLD_TOL = 0.15    # 배 스케일 절대 오차 허용
_PP_TOL = 0.5       # %p 차이 — 표시값이 반올림돼 있으므로 관대하게(27.9/25.0 표시, 원문 27.88/25.03)

# "쌍이 있는데 값이 안 맞는다" = 오산. "관련 쌍 자체가 없다" = 모름(unresolved).
# 이 둘을 가르는 기준: 후보 비율이 주장값과 같은 스케일(0.4~2.5배)이면 '관련 쌍'으로 본다.
# (2026-07-12 실전: 카드에 1.63→63.66이 있는데 '32.7배'라 씀. 실제 39배 — 구 로직은 이걸
#  '어떤 쌍과도 안 맞으니 모름'으로 흘려보냈다. 쌍이 있는데 틀린 건 모름이 아니라 오산이다.)
_RELATED_LO, _RELATED_HI = 0.4, 2.5

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
    """(suspect, unresolved). 같은 카드 수치쌍 (a<b)에서 주장값을 검산.

    - fold:       b/a ≈ claimed
    - pct_change: (b/a-1)*100 ≈ claimed  (b/a*100 과 혼동하면 '배↔%증가' 오류)
    - pct_point:  b-a ≈ claimed          (증가율이 아니라 차이)

    판정 3분기:
      정합             → (False, False)
      쌍이 있는데 불일치 → (True,  False)   ← 오산. 구 로직이 놓치던 지점
      관련 쌍 자체 없음  → (False, True)    ← 모르면 죄 아님(막지 않는다)
    """
    pairs = [(min(a, b), max(a, b))
             for i, a in enumerate(nums) for b in nums[i + 1:] if a != b]
    # 주장값 자신은 비교쌍에서 제외 (170이 카드 안 숫자로 다시 잡히는 자기참조 방지)
    pairs = [(a, b) for a, b in pairs if a != claimed and b != claimed]
    if not pairs or claimed <= 0:
        return False, True

    if kind == "fold":
        cands = [b / a for a, b in pairs]
        tol = max(_FOLD_TOL, claimed * 0.03)      # 큰 배율일수록 표기 반올림 여지가 크다
    elif kind == "pct_point":
        cands = [b - a for a, b in pairs]
        tol = _PP_TOL
    else:  # pct_change
        cands = [(b / a - 1) * 100 for a, b in pairs]
        tol = _PCT_TOL

    if any(abs(c - claimed) <= tol for c in cands):
        return False, False

    # 혼동 패턴: '배'와 '% 증가'를 뒤바꿔 쓴 경우 (170% 증가 ↔ 1.7배)
    if kind == "pct_change" and any(abs(b / a * 100 - claimed) <= _PCT_TOL for a, b in pairs):
        return True, False
    if kind == "fold" and any(abs((b / a - 1) - claimed) <= _FOLD_TOL for a, b in pairs):
        return True, False

    # 관련 쌍(주장값과 같은 스케일의 후보)이 존재하는데 값이 안 맞으면 → 오산
    related = [c for c in cands if c > 0 and _RELATED_LO <= c / claimed <= _RELATED_HI]
    if related:
        return True, False
    return False, True


def derived_claims(html: str, paper_text: str) -> list[dict]:
    """카드별 파생수치(N% 증가·N배)를 같은 카드 수치쌍과 검산.

    반환: [{value, kind, suspect, unresolved, verified, context, card}]
    suspect=True → 사용자에게 '계산 불일치' 표면화(막지 않음, 헌법 3조).
    """
    results: list[dict] = []
    for card_idx, content in _card_contents(html):
        if card_idx is None:
            continue                       # 카드 경계가 없으면 '같은 카드 수치쌍' 검산이 성립 안 함
        nums = _card_numbers(content)
        for pat, kind in ((_PCT_CHANGE, "pct_change"), (_FOLD, "fold"), (_PCT_POINT, "pct_point")):
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
                    "card": card_idx,
                })
    return results


def _core_of(v: str) -> str:
    m = _CORE.search(v)
    return m.group().replace(",", "") if m else ""


def verify_claims_with_derived(html: str, paper_text: str) -> list[NumberClaim]:
    """V1 claims에 V2 확인을 반영한다 — 산수로 검증된 파생값은 verified로 승격.

    파생값(1.7배)은 정의상 원문에 문자열로 없다(142·238에서 유도). V1이 "1.7 원문에 없음"으로
    이걸 '확인 필요'로 세면 완벽한 덱에도 늑대야를 외친다. V2가 산수로 확인(suspect·unresolved
    모두 아님)한 값은 확인 필요가 아니라 **우리가 검증한 값**이다.
    """
    confirmed_cores = {
        _core_of(str(d["value"]))
        for d in derived_claims(html, paper_text)
        if not d["suspect"] and not d["unresolved"]
    }
    claims = verify_deck(html, paper_text)
    for c in claims:
        if not c.verified and _core_of(c.value) in confirmed_cores:
            c.verified = True
    return claims


def compute_verify_unverified(html: str, paper_text: str) -> int:
    """사용자에게 보일 '확인 필요' 카운트 (V2 확인 파생값 제외)."""
    return sum(not c.verified for c in verify_claims_with_derived(html, paper_text))


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
