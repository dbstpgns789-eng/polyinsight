# -*- coding: utf-8 -*-
"""논문 figure 추출 — '논문이 곧 레퍼런스'(2026-07-13).

배경: few-shot refs(남의 덱 HTML)를 주면 모델이 그 팔레트를 복사한다(실측: `#36E0CE 전기 시안`
→ `#3DD6D0 전기 시안`). refs를 늘리면 앵커만 강해지고, 우리 산출물을 refs로 승격시키면
미감이 근친교배로 수축한다. 유한한 레퍼런스로는 '논문 수만큼의 룩'에 도달할 수 없다.

그래서 앵커를 밖에서 안으로 뒤집는다: **이 논문이 스스로 입고 있는 옷**(SEM 사진·그래프·도식)을
모델에게 보여준다. 논문마다 그림이 다르므로 동질화가 원리적으로 불가능하고,
'이 논문만의 옷'이라는 제품 약속과 정확히 일치한다.

실측(2026-07-13): Attention 논문의 실제 시각 언어는 파스텔(분홍·주황·노랑) + 둥근 박스인데
우리 파이프라인은 refs 때문에 미드나잇 네온을 입혔다 — 논문 자신을 배신한 것.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MIN_W, _MIN_H = 240, 180        # 로고·아이콘·수식 조각 컷
_MAX_BYTES = 3_500_000           # 이미지당 API 한계(5MB) 안전 마진
_CANDIDATE_POOL = 12             # 크기 상위 후보 풀(여기서 페이지 분산으로 고른다)


def extract_figures(
    pdf_bytes: bytes,
    max_figures: int = 3,
    _return_meta: bool = False,
) -> list:
    """PDF에서 대표 figure를 PNG 바이트로 추출. 실패·부재 시 빈 리스트(소프트 — 저작을 막지 않는다).

    선택 전략: 크기 상위 후보 중 **페이지를 분산**해 고른다.
    (단순히 가장 큰 3장을 뽑으면 같은 페이지의 SEM 패널만 나와 논문이 회색조 세계로만 보인다.
     앞쪽 도식 · 중간 사진 · 뒤쪽 그래프가 섞여야 그 논문의 시각 '범위'가 전달된다.)
    """
    if not pdf_bytes:
        return []
    try:
        import fitz
    except ImportError:
        logger.warning("figures: PyMuPDF 없음 — figure 추출 건너뜀")
        return []

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        logger.info("figures: PDF 열기 실패(%s) — figure 없이 저작", exc)
        return []

    cands: list[dict] = []
    try:
        for pno in range(doc.page_count):
            for img in doc[pno].get_images(full=True):
                xref = img[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                except Exception:
                    continue
                if pix.width < _MIN_W or pix.height < _MIN_H:
                    continue
                cands.append({"page": pno, "xref": xref,
                              "area": pix.width * pix.height})
    except Exception as exc:
        logger.info("figures: 스캔 실패(%s)", exc)
        doc.close()
        return []

    if not cands:
        doc.close()
        logger.info("figures: 추출 가능한 figure 없음(스캔본·벡터 전용 논문일 수 있음)")
        return []

    # 크기 상위 풀 → 페이지 분산으로 max_figures장 선택
    cands.sort(key=lambda c: -c["area"])
    pool = cands[:_CANDIDATE_POOL]
    picked: list[dict] = []
    seen_pages: set[int] = set()
    for c in pool:                                  # 1차: 서로 다른 페이지에서
        if c["page"] in seen_pages:
            continue
        picked.append(c)
        seen_pages.add(c["page"])
        if len(picked) >= max_figures:
            break
    for c in pool:                                  # 2차: 부족하면 같은 페이지도 허용
        if len(picked) >= max_figures:
            break
        if c not in picked:
            picked.append(c)
    picked.sort(key=lambda c: c["page"])            # 논문 흐름 순서대로

    out: list = []
    for c in picked:
        try:
            pix = fitz.Pixmap(doc, c["xref"])
            if pix.n - pix.alpha >= 4:              # CMYK → RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            data = pix.tobytes("png")
        except Exception:
            continue
        if len(data) > _MAX_BYTES:
            continue
        out.append({"page": c["page"], "png": data} if _return_meta else data)
    doc.close()

    logger.info("figures: %d장 추출(페이지 %s)",
                len(out), [c["page"] + 1 for c in picked])
    return out
