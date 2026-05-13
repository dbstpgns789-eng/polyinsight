# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
from io import BytesIO
from statistics import median

import fitz  # PyMuPDF
import pdfplumber

from ..core.models import PaperMetadata, S1Output

logger = logging.getLogger(__name__)

_SECTION_KEYWORDS = [
    "abstract",
    "introduction",
    "background",
    "related work",
    "methods",
    "methodology",
    "materials and methods",
    "experimental",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "references",
    "acknowledgements",
    "acknowledgments",
]

_SECTION_KEY_MAP: dict[str, str] = {
    "abstract": "abstract",
    "introduction": "introduction",
    "background": "introduction",
    "related work": "introduction",
    "methods": "methods",
    "methodology": "methods",
    "materials and methods": "methods",
    "experimental": "methods",
    "results": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "conclusions": "conclusion",
    "references": "references",
    "acknowledgements": "acknowledgements",
    "acknowledgments": "acknowledgements",
}


def _clean_text(text: str) -> str:
    # soft hyphen, 특수문자 정규화 (줄바꿈 보존)
    text = text.replace("\xad", "")              # soft hyphen
    text = text.replace("’", "'")           # right single quotation
    text = text.replace("‘", "'")           # left single quotation
    text = text.replace("“", '"')           # left double quotation
    text = text.replace("”", '"')           # right double quotation
    text = text.replace("—", "--")          # em dash
    text = text.replace("–", "-")           # en dash
    # 줄 내부 연속 공백만 정규화 (줄바꿈은 유지)
    lines = [re.sub(r"[ \t]+", " ", line) for line in text.splitlines()]
    return "\n".join(lines).strip()


def _is_two_column(blocks: list) -> bool:
    # 텍스트 블록 x0 좌표 분포로 2컬럼 여부 판단
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    if len(text_blocks) < 4:
        return False
    x0_values = [b[0] for b in text_blocks]
    mid = median(x0_values)
    left = [x for x in x0_values if x < mid]
    right = [x for x in x0_values if x >= mid]
    if not left or not right:
        return False
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    page_width = max(b[2] for b in text_blocks)
    return (right_mean - left_mean) > page_width * 0.2


def _extract_page_text(page: fitz.Page) -> str:
    # 2컬럼 레이아웃은 좌->우 순서로 재정렬
    blocks = page.get_text("blocks", sort=False)  # type: ignore[arg-type]
    if _is_two_column(blocks):
        page_width = page.rect.width
        mid = page_width / 2
        left_blocks = sorted(
            [b for b in blocks if b[6] == 0 and b[0] < mid],
            key=lambda b: b[1],
        )
        right_blocks = sorted(
            [b for b in blocks if b[6] == 0 and b[0] >= mid],
            key=lambda b: b[1],
        )
        ordered = left_blocks + right_blocks
    else:
        ordered = sorted(
            [b for b in blocks if b[6] == 0],
            key=lambda b: (b[1], b[0]),
        )
    return "\n".join(_clean_text(b[4]) for b in ordered if b[4].strip())


def _parse_sections(raw_text: str) -> tuple[dict[str, str], bool]:
    # 섹션 헤더 감지 → section_map 반환. 미감지 시 {"full_text": raw_text}, True
    lines = raw_text.splitlines()
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("<!-- page"):
            continue

        # "## **Abstract**" 등 마크다운/볼드 제거 후 비교
        normalized = re.sub(r"\*+|#{1,3}", "", lower).strip()

        matched_kw = None
        for kw in _SECTION_KEYWORDS:
            if re.fullmatch(
                rf"(?:\d+[\.\s]+)?{re.escape(kw)}[\.\s:]*",
                normalized,
                re.IGNORECASE,
            ):
                matched_kw = kw
                break

        if matched_kw:
            if current_key is not None:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.setdefault(current_key, body)
            current_key = _SECTION_KEY_MAP[matched_kw]
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        body = "\n".join(current_lines).strip()
        if body:
            sections.setdefault(current_key, body)

    if not sections:
        return {"full_text": raw_text}, True
    return sections, False


def _try_pdfplumber(
    pdf_bytes: bytes, warnings: list[str]
) -> tuple[dict[int, str], PaperMetadata]:
    page_map: dict[int, str] = {}
    metadata = PaperMetadata(title=None, authors=[], year=None, doi=None)
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            meta = pdf.metadata or {}
            metadata = _build_metadata(meta)
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                page_map[i] = _clean_text(text)
    except Exception as exc:
        warnings.append(f"S1: pdfplumber error -- {exc}")
    return page_map, metadata


def _build_metadata(meta: dict) -> PaperMetadata:
    title = meta.get("title") or meta.get("Title") or None
    author_raw = meta.get("author") or meta.get("Author") or ""
    authors = [a.strip() for a in re.split(r"[;,]", author_raw) if a.strip()]
    date_raw = meta.get("creationDate") or meta.get("CreationDate") or ""
    year_m = re.search(r"(\d{4})", date_raw)
    year = int(year_m.group(1)) if year_m else None
    subj = (meta.get("subject") or meta.get("Subject") or "") + (
        meta.get("keywords") or meta.get("Keywords") or ""
    )
    doi_m = re.search(r"10\.\d{4,}/\S+", subj)
    doi = doi_m.group(0).rstrip(".,)") if doi_m else None
    return PaperMetadata(title=title, authors=authors, year=year, doi=doi)


class S1Extractor:
    _MIN_WORD_COUNT = 100

    async def execute(self, pdf_bytes: bytes) -> S1Output:
        if not pdf_bytes:
            return S1Output(
                raw_text="",
                page_map={},
                section_map={"full_text": ""},
                metadata=PaperMetadata(title=None, authors=[], year=None, doi=None),
                word_count=0,
                degraded=True,
                warnings=["empty input bytes"],
            )

        warnings: list[str] = []
        page_map: dict[int, str] = {}
        metadata = PaperMetadata(title=None, authors=[], year=None, doi=None)

        # 1차: fitz (PyMuPDF)
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for i, page in enumerate(doc, start=1):
                page_map[i] = _extract_page_text(page)
            metadata = _build_metadata(doc.metadata or {})
            doc.close()
        except Exception as exc:
            logger.warning("S1: fitz failed (%s), falling back to pdfplumber", exc)
            warnings.append(f"S1: pdfplumber fallback -- fitz error: {exc}")
            page_map, metadata = _try_pdfplumber(pdf_bytes, warnings)
            if not page_map:
                return S1Output(
                    raw_text="",
                    page_map={},
                    section_map={"full_text": ""},
                    metadata=metadata,
                    word_count=0,
                    degraded=True,
                    warnings=warnings + ["both fitz and pdfplumber failed"],
                )

        # PAGE 마커 삽입
        parts: list[str] = []
        for n in sorted(page_map):
            parts.append(f"<!-- PAGE {n} -->")
            parts.append(page_map[n])
        raw_text = "\n".join(parts)

        word_count = len(raw_text.split())
        degraded = word_count < self._MIN_WORD_COUNT
        if degraded:
            warnings.append(f"S1: low word count ({word_count}) -- degraded mode")

        section_map, section_degraded = _parse_sections(raw_text)
        if section_degraded:
            degraded = True
            warnings.append("S1: no section headers detected -- degraded mode")

        if not (metadata.title and metadata.title.strip()):
            warnings.append("S1: metadata title not found")

        return S1Output(
            raw_text=raw_text,
            page_map=page_map,
            section_map=section_map,
            metadata=metadata,
            word_count=word_count,
            degraded=degraded,
            warnings=warnings,
        )
