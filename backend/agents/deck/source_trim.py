# -*- coding: utf-8 -*-
"""저작 입력 정리 — 참고문헌을 버리고 결론을 살린다 (2026-07-13).

실측 사고(chitosan, 81,518자):
    Results     58,027자 (71%)   겨우 들어감
    ──── MAX_SOURCE_CHARS=60,000에서 절단 ────
    Conclusion  60,175자 (74%)   ✂ 잘림!!   ← 논문의 핵심 메시지
    References  63,697자 (78%)   ✂ 잘림     ← 이건 버려도 됨

**175자 차이로 결론을 버리고 있었다.** 그리고 참고문헌이 원문의 22%(18,198자)를 차지한다 —
아무 쓸모없는 그것 때문에 결론을 못 봤다.

논문은 뒤로 갈수록 중요하다(Results → Discussion → Conclusion). 앞에서부터 자르는 건
**가장 중요한 것부터 버리는 짓**이다. 참고문헌·감사말을 먼저 걷어내면, 같은 상한 안에
본문이 더 들어온다 — 비용은 그대로인데 품질이 오른다.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# 참고문헌·감사말 '헤딩'. 본문 중 "previous references suggest" 같은 언급과 구분하려면
# 줄머리(+선택적 마크다운 #/번호/굵게)에서만 매치해야 한다.
_HEADING_PREFIX = (
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?[ \t]*"           # 마크다운 헤딩(선택)
    r"(?:\d+[.)]?[ \t]*)?"                                # "4." 같은 번호(선택)
)
_HEADING_SUFFIX = r"[ \t]*:?[ \t]*(?:\*\*)?[ \t]*$"      # 줄 끝까지(제목 줄이어야 함)

# ★참고문헌과 감사말을 **분리**한다 (2026-07-14 사고).
#   섞어놓고 "가장 이른 매치 이후 전부 버리기"를 했더니, GPT-3에서
#   Acknowledgements(59%) → 부록 A~D(66%) → References(89%) 구조를 만나
#   **감사말을 참고문헌으로 오인해 부록을 통째로 버렸다**(64,339자, 그 안에 3,640 PF-days).
_BIB_HEADING = re.compile(
    _HEADING_PREFIX + r"(?:References?|Bibliography|참고\s*문헌)" + _HEADING_SUFFIX, re.M | re.I,
)
_TAIL_HEADING = re.compile(
    _HEADING_PREFIX +
    r"(?:Acknowledge?ments?|Author\s+Contributions?|Declaration\s+of|"
    r"Conflicts?\s+of\s+Interest|Supplementary|감사의?\s*글|사사)" + _HEADING_SUFFIX,
    re.M | re.I,
)
_ACK_MAX_GAP = 4_000    # 감사말은 참고문헌 **바로 앞**일 때만 함께 버린다.
                        # 사이에 부록이 끼어 있으면(GPT-3: 64k) 감사말만 남기고 부록을 살린다.
_MAX_BIB_FRACTION = 0.30    # 참고문헌이 문서의 30%를 넘을 리 없다 — 넘으면 부록을 삼킨 것이다(자르지 않는다)
_MIN_UNCLASSIFIED = 20_000  # 단 절대 크기도 본다 — 짧은 꼬리는 진짜 참고문헌이다(부록은 크다)


# ── 폴백: 언어·형식 무관 구조 휴리스틱 ────────────────────────────────────
# 헤딩 단어("References"·"참고문헌")에 의존하면 언어·저널·추출기가 바뀔 때 깨진다.
# 참고문헌의 본질은 단어가 아니라 **서지 마커의 밀도**다 — 연도·DOI·et al.·[1]·pp.
# 이건 독일어 논문이든 헤딩 없는 arXiv preprint든 똑같이 나타난다.
_BIB_MARKERS = re.compile(
    r"\b(?:19|20)\d{2}\b"          # 연도
    r"|\bdoi\b|10\.\d{4,}/"        # DOI
    r"|\bet\s+al\b"                # et al.
    r"|^\s*\[\d{1,3}\]"            # [1] 번호 인용
    r"|\bpp?\.\s*\d"               # p. 12 / pp. 12-34
    r"|\bvol\.?\s*\d"              # vol. 5
    r"|[A-Z][a-z]+,\s+[A-Z]\.",    # "Kim, S." 저자 표기
    re.M | re.I,
)
_WINDOW = 1200          # 밀도 측정 창
# 실측(chitosan 논문, 1200자 창당 마커 수):
#   본문      0~6개    ▏
#   참고문헌  22~44개  ████████████████████
# 경계가 뚜렷하다. 임계 6은 본문의 인용 밀집(Discussion)에 걸려 65%를 날렸다 → 15로.
_BIB_THRESHOLD = 15
_BIB_LOW = 10           # 참고문헌 '끝' 판정은 더 낮은 문턱으로(히스테리시스) — 줄바꿈된 서지에서 튀지 않게


_MIN_BIB_RUN = 3        # 참고문헌은 최소 3창(≈3,600자) 연속 고밀도다(본문의 인용 밀집과 구분)
_MIN_TAIL = 40          # 이보다 짧은 꼬리만 잔여물(페이지번호)로 버린다.
                        # 낮게 잡는다 — 부록 표 한 줄이 킬러 수치를 담는다(GPT-3 부록 D = 3,640 PF-days)

# 참고문헌이 끝나는 지점 = 부록 헤딩. 밀도로 찾으면 줄바꿈된 서지에서 흔들린다(실측: refs 제거 실패).
_APPENDIX_HEADING = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?[ \t]*"
    r"(?:[A-Z][.)]?[ \t]+)?"                      # "A Appendix" / "A. Appendix"
    r"(?:Appendix|Appendices|Supplementary\s+Material|부록)\b",
    re.M | re.I,
)
BIB_ELLIPSIS = "\n\n[⋯ 참고문헌 생략 ⋯]\n\n"

# 상한 초과 시 앞머리에 줄 비율. 나머지는 꼬리(Results·Conclusion)에 준다.
# 논문은 뒤가 중요하다 — 앞에서 자르면 결론부터 버린다.
HEAD_RATIO = 0.35
ELLIPSIS = "\n\n[⋯ 중략: 본문 중간부(주로 실험 상세)가 길이 제한으로 생략됨 ⋯]\n\n"


def _find_bib_start(text: str) -> int | None:
    """서지 마커가 **연속으로 밀집한 구간**의 시작 = 참고문헌. 못 찾으면 None.

    ★"문서 끝 = 참고문헌"이라는 가정은 틀렸다 — Attention 논문은 참고문헌 뒤에 부록이 있다.
      그래서 뒤에서부터 창을 훑되, 저밀도 꼬리(부록·부록그림)는 건너뛴다.
    ★본문의 인용 밀집(Related Work)과 구분하려면 **연속 길이**를 봐야 한다.
      참고문헌은 수천 자가 통째로 고밀도지만, 본문은 한두 창에 그친다.
    """
    n = len(text)
    if n < _WINDOW * _MIN_BIB_RUN:
        return None

    floor = int(n * 0.3)          # 안전장치: 본문 30% 아래로는 절대 안 내려간다

    def dense(lo: int) -> bool:
        return len(_BIB_MARKERS.findall(text[lo:lo + _WINDOW])) >= _BIB_THRESHOLD

    # 뒤에서부터 창을 훑으며 고밀도 런(run)을 찾는다. 각 런의 시작을 후보로 모은다.
    best: int | None = None
    pos = n - _WINDOW
    while pos > floor:
        if dense(pos):
            run_start = pos
            while run_start - _WINDOW > floor and dense(run_start - _WINDOW):
                run_start -= _WINDOW
            run_len = (pos - run_start) // _WINDOW + 1
            if run_len >= _MIN_BIB_RUN:
                best = run_start           # 더 앞선(=더 이른) 런을 계속 찾는다
            pos = run_start - _WINDOW      # 이 런 이전으로 점프
        else:
            pos -= _WINDOW

    return best


def _find_bib_end(text: str, start: int) -> int | None:
    """참고문헌 블록이 **끝나는** 지점. 못 찾으면(문서 끝까지 고밀도) None.

    ★arXiv 관례: References 뒤에 부록이 온다(GPT-3 부록 D에 컴퓨트 표가 있다).
      참고문헌 '이후 전부'를 버리면 부록까지 버린다 — 실측 사고(2026-07-14): GPT-3 논문에서
      88,323자(41%)가 사라졌고 그 안에 카드가 쓸 수치(3,640 PF-days)가 있었다.
    ★경계는 **줄 단위**로 찾는다. 1,200자 창은 너무 굵어서 짧은 부록이 참고문헌 창에 먹힌다.
      참고문헌은 **줄마다** 서지 마커를 갖는다(연도·doi·et al.·[n]). 부록은 거의 없다.
    """
    m = _APPENDIX_HEADING.search(text, start)
    if m:
        return m.start()

    # 부록 헤딩이 "Appendix" 단어를 안 쓰는 경우가 흔하다("A Broader Impacts").
    # → 서지 마커 밀도로 되돌아간다. 히스테리시스: 밀집을 본 뒤, 저밀도 2창 연속이면 끝난 것.
    n = len(text)
    dense_seen = False
    low_start: int | None = None
    low = 0
    pos = start
    while pos < n:
        win = text[pos:pos + _WINDOW]
        density = len(_BIB_MARKERS.findall(win)) * _WINDOW / max(len(win), 1)   # 부분창 보정
        if density >= _BIB_THRESHOLD:
            dense_seen, low, low_start = True, 0, None
        elif density < _BIB_LOW:
            if low == 0:
                low_start = pos
            low += 1
            if dense_seen and low >= 2:
                return low_start
        pos += _WINDOW

    # 문서가 저밀도로 끝났고(부록이 짧아 2창을 못 채움) 앞에 밀집이 있었다면 그 지점이 경계다
    return low_start if (dense_seen and low) else None


def trim_source(text: str, limit: int) -> tuple[str, int]:
    """참고문헌 이후를 버리고, 남은 본문을 limit로 자른다. (본문, 버린 글자수).

    2단 방어:
      1) 헤딩 정규식 — 빠르고 정확하다(우리 코퍼스 5/5 적중)
      2) 서지 밀도 휴리스틱 — 헤딩이 없거나 다른 언어일 때(언어·형식 무관)
    안전장치: 본문의 30% 아래로는 절대 자르지 않는다(오탐으로 논문을 날리지 않는다).
    """
    if not text:
        return text, 0

    original = len(text)
    body = text

    # 1) 참고문헌 헤딩 — 본문 30% 이전 매치는 오탐으로 무시
    hits = [m.start() for m in _BIB_HEADING.finditer(text) if m.start() > original * 0.3]
    bib_start = min(hits) if hits else None

    # 2) 폴백 — 헤딩을 못 찾으면 서지 마커 밀도로
    if bib_start is None:
        bib_start = _find_bib_start(text)
        if bib_start is not None:
            logger.info("source_trim: 헤딩 없음 → 서지 밀도로 참고문헌 추정(%d자 지점)", bib_start)

    if bib_start is not None:
        # 감사말·기여·이해충돌은 참고문헌 **바로 앞**일 때만 함께 버린다.
        # (사이에 부록이 끼면 안 버린다 — GPT-3에서 부록 64k를 날린 사고의 교정)
        cut_from = bib_start
        for m in _TAIL_HEADING.finditer(text):
            if original * 0.3 < m.start() < bib_start and bib_start - m.start() <= _ACK_MAX_GAP:
                cut_from = min(cut_from, m.start())

        head = text[:cut_from].rstrip()
        bib_end = _find_bib_end(text, bib_start)       # 참고문헌이 끝나는 곳(= 부록 시작)
        tail = text[bib_end:].strip() if bib_end is not None else ""

        if len(tail) >= _MIN_TAIL:
            body = head + BIB_ELLIPSIS + tail
            logger.info("source_trim: 참고문헌 %d자 도려냄 — 뒤 %d자(부록) 보존 (%d → %d)",
                        bib_end - cut_from, len(tail), original, len(body))
        elif (original - cut_from) > _MIN_UNCLASSIFIED and \
                (original - cut_from) / original > _MAX_BIB_FRACTION:
            # ★분류 못 하는 건 안 버린다. 참고문헌이 문서의 30%를 넘길 리 없다 —
            #   경계를 못 찾았는데 꼬리가 이만큼 크면 그 안에 부록이 있다(ReAct: 62%).
            logger.warning("source_trim: 참고문헌 끝을 못 찾았고 꼬리가 %d자(%.0f%%)다 — "
                           "부록 유실 위험이 커서 **자르지 않는다**",
                           original - cut_from, (original - cut_from) / original * 100)
        else:
            body = head
            logger.info("source_trim: 참고문헌 이후 %d자 제거 (%d → %d)",
                        original - len(body), original, len(body))

    else:
        # 참고문헌이 없고 감사말/보충자료만 있는 경우 — 그 이후를 버린다(기존 동작)
        tails = [m.start() for m in _TAIL_HEADING.finditer(text) if m.start() > original * 0.3]
        if tails:
            body = text[:min(tails)].rstrip()
            logger.info("source_trim: 참고문헌 없음 — 감사말 이후 %d자 제거", original - len(body))

    # ★★자르는 것은 **최후 수단**이다 — 정보를 버리는 짓이다.
    #   상한(MAX_SOURCE_CHARS=180,000자)은 Opus 컨텍스트의 61%라, 사실상 모든 논문이 통째로 들어간다.
    #   여기 도달하는 건 학위논문·단행본 수준뿐이다.
    #
    #   그때도 **앞에서 자르지 않는다**. 논문의 중요도는 균등하지 않다:
    #     앞: Abstract·Introduction   (무엇을 왜 했는가)
    #     중: Methods 상세·Related Work
    #     뒤: Results·Discussion·Conclusion  (★무엇을 알아냈는가)
    #   앞에서부터 자르면 **가장 중요한 결론부터 버린다**(실측: chitosan에서 175자 차이로 결론 유실).
    #
    #   ⚠️ 단 중간 생략도 손실이다 — Methods의 실험 조건(12.5kV·0.32wt%)이 거기 있고,
    #      우리 카드가 그 수치를 쓴다. 그래서 이 경로는 **최대한 안 타는 게 목표**다.
    if len(body) > limit:
        head = int(limit * HEAD_RATIO)
        tail = limit - head - len(ELLIPSIS)
        body = body[:head] + ELLIPSIS + body[-tail:]
        logger.warning("source_trim: 상한(%d자) 초과 — 중간 생략(앞 %d + 뒤 %d). "
                       "실험 조건이 중간에 있으면 유실될 수 있다.", limit, head, tail)

    return body, original - len(body)
