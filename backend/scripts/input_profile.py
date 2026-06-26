"""논문당 입력 물성(input_profile) 결정론 추출 — Mode A 집계축(spec §4·§6).
S1 취약성은 카드 layout이 아니라 *입력 문서 물성*(조판·저널)으로 묶어야 핀셋 가치가 산다."""
from __future__ import annotations

import re
from io import BytesIO

import pdfplumber

# DOI 등록기관 접두사 → 퍼블리셔. 있을 때만 — 없으면 unknown.
PUBLISHER_BY_DOI_PREFIX = {
    "10.1016": "Elsevier", "10.1002": "Wiley", "10.1021": "ACS",
    "10.1039": "RSC", "10.1038": "Nature", "10.1073": "PNAS",
    "10.1101": "bioRxiv", "10.48550": "arXiv", "10.1109": "IEEE",
    "10.1145": "ACM",
}


def journal_family_from_doi(doi: str | None) -> str:
    if not doi:
        return "unknown"
    m = re.match(r"(10\.\d{4,9})/", doi.strip())
    if not m:
        return "unknown"
    prefix = m.group(1)
    return PUBLISHER_BY_DOI_PREFIX.get(prefix, f"other:{prefix}")


# 거터(중앙 빈 띠) 판정 파라미터 — Golden/코퍼스로 후속 캘리브레이션 가능.
_GUTTER_LO, _GUTTER_HI = 0.42, 0.58
_SIDE_MIN = 0.25     # 좌·우 각 절반이 최소 이만큼 차야 2단 후보
# 0.35로 완화: 실제 2단 논문은 제목/초록이 full-width라 중앙 단어 비율이 ~30%까지 올라감.
_GUTTER_MAX = 0.35

_DOI_RE = re.compile(r"\b(10\.\d{4,}/[^\s,;)\"'<>]+)", re.IGNORECASE)


def columns_from_centers(centers: list[float]) -> int:
    """정규화 단어 중심좌표(0~1) 분포 → 1 또는 2단. 순수·결정론."""
    if not centers:
        return 1
    n = len(centers)
    left = sum(1 for c in centers if c < _GUTTER_LO) / n
    right = sum(1 for c in centers if c > _GUTTER_HI) / n
    central = sum(1 for c in centers if _GUTTER_LO <= c <= _GUTTER_HI) / n
    if left > _SIDE_MIN and right > _SIDE_MIN and central < _GUTTER_MAX:
        return 2
    return 1


def detect_columns(pdf_bytes: bytes) -> int:
    """앞 5페이지 단어 중심좌표를 모아 columns_from_centers에 위임. 파싱 실패 시 1."""
    centers: list[float] = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:5]:
                w = page.width or 1
                for word in page.extract_words():
                    centers.append(((word["x0"] + word["x1"]) / 2) / w)
    except Exception:
        return 1
    return columns_from_centers(centers)


def doi_from_text(pdf_bytes: bytes) -> str | None:
    """첫 2페이지 본문에서 DOI 패턴 검색. 메타데이터에 없을 때 폴백."""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:2]:
                text = page.extract_text() or ""
                m = _DOI_RE.search(text)
                if m:
                    return m.group(1).rstrip(".,)")
    except Exception:
        pass
    return None


def build_input_profile(pdf_bytes: bytes, doi: str | None) -> dict:
    """논문 1편 → {columns, journal_family}. Mode A가 GROUP BY 하는 메타."""
    if not doi:
        doi = doi_from_text(pdf_bytes)
    return {
        "columns": detect_columns(pdf_bytes),
        "journal_family": journal_family_from_doi(doi),
    }
