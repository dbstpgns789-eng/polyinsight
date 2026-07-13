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
_END_SECTIONS = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?[ \t]*"           # 마크다운 헤딩(선택)
    r"(?:\d+[.)]?[ \t]*)?"                                # "4." 같은 번호(선택)
    r"(?:References?|Bibliography|Acknowledge?ments?|Acknowledgement|"
    r"Author\s+Contributions?|Declaration\s+of|Conflicts?\s+of\s+Interest|"
    r"Supplementary|참고\s*문헌|감사의?\s*글|사사)"
    r"[ \t]*:?[ \t]*(?:\*\*)?[ \t]*$",                    # 줄 끝까지(제목 줄이어야 함)
    re.M | re.I,
)


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


_MIN_BIB_RUN = 3        # 참고문헌은 최소 3창(≈3,600자) 연속 고밀도다(본문의 인용 밀집과 구분)

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

    # 1) 헤딩 기반 — 본문 30% 이전 매치는 오탐으로 무시
    cuts = [m.start() for m in _END_SECTIONS.finditer(text) if m.start() > original * 0.3]
    cut_at = min(cuts) if cuts else None

    # 2) 폴백 — 헤딩을 못 찾으면 서지 마커 밀도로
    if cut_at is None:
        cut_at = _find_bib_start(text)
        if cut_at is not None:
            logger.info("source_trim: 헤딩 없음 → 서지 밀도로 참고문헌 추정(%d자 지점)", cut_at)

    if cut_at is not None:
        body = text[:cut_at].rstrip()
        logger.info("source_trim: 참고문헌 이후 %d자 제거 (%d → %d)",
                    original - len(body), original, len(body))

    # ★참고문헌을 빼도 상한을 넘으면(리뷰 논문·학위논문): **앞에서 자르지 않는다.**
    #   논문의 중요도는 균등하지 않다 —
    #     앞: Abstract·Introduction (필수. 무엇을 왜 했는가)
    #     중: Methods 상세·Related Work (덜 중요. 카드뉴스에 상세 공정은 안 들어간다)
    #     뒤: Results·Discussion·Conclusion (★핵심. 무엇을 알아냈는가)
    #   앞에서부터 자르면 **가장 중요한 결론부터 버린다**(실측: chitosan에서 175자 차이로 결론 유실).
    #   그래서 앞머리와 꼬리를 남기고 **중간을 생략**한다.
    if len(body) > limit:
        head = int(limit * HEAD_RATIO)
        tail = limit - head - len(ELLIPSIS)
        body = body[:head] + ELLIPSIS + body[-tail:]
        logger.info("source_trim: 상한 초과 — 앞 %d자 + 뒤 %d자 보존, 중간 생략", head, tail)

    return body, original - len(body)
