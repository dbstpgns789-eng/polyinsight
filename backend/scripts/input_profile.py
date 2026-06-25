"""논문당 입력 물성(input_profile) 결정론 추출 — Mode A 집계축(spec §4·§6).
S1 취약성은 카드 layout이 아니라 *입력 문서 물성*(조판·저널)으로 묶어야 핀셋 가치가 산다."""
from __future__ import annotations

import re

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
