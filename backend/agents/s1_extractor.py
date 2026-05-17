# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
from io import BytesIO

import pdfplumber
import pymupdf4llm
import fitz

from ..core.models import PaperMetadata, S1Output

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    # soft hyphen 제거, 줄 내부 연속 공백 정규화 (줄바꿈 보존)
    text = text.replace("\xad", "")
    lines = [re.sub(r"[ \t]+", " ", line) for line in text.splitlines()]
    return "\n".join(lines).strip()


# 번호 없는 종결 섹션 (numbered 아니어도 실제 섹션으로 인정)
_TERMINAL_SECTIONS = {"conclusion", "conclusions", "references", "acknowledgments",
                      "acknowledgements", "declaration of competing interest",
                      "credit authorship contribution statement", "data availability"}


def _parse_sections(raw_text: str) -> tuple[dict[str, str], bool]:
    """
    pymupdf4llm Markdown 출력 기반 섹션 파싱.

    규칙:
      - '## **N. Name**'  (굵게 + 번호) → 새 섹션
      - '## **Name**'     (굵게, 번호 없음, 60자 미만, _TERMINAL_SECTIONS) → 새 섹션
      - '## _N.M. Name_'  (이탤릭 소목차) → 부모 섹션에 병합
      - '> ...'           (blockquote, 첫 번호 섹션 이전) → abstract 원문
      - 그 외 ## 헤더     → 저널명/제목 → 스킵
    """
    lines = raw_text.splitlines()
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    pre_body: list[str] = []       # 첫 번호 섹션 이전 blockquote 내용
    found_first_section = False

    for line in lines:
        stripped = line.strip()

        if stripped.lower().startswith("<!-- page"):
            continue

        # ── ## **굵게** 헤더 ────────────────────────────────────────────────
        bold_m = re.match(r"^#{1,3}\s+\*\*(.+?)\*\*\s*$", stripped)
        if bold_m:
            raw_hdr = bold_m.group(1).strip()
            is_numbered = bool(re.match(r"^\d+[\.\s]", raw_hdr))
            key = re.sub(r"^\d+(\.\d+)*\.?\s*", "", raw_hdr).strip().lower()

            is_real = is_numbered or key in _TERMINAL_SECTIONS
            if not is_real or not key:
                # 저널명·제목 등 → 스킵
                continue

            # 이전 섹션 저장
            if current_key is not None:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.setdefault(current_key, body)

            # 첫 번호 섹션 직전까지 쌓인 abstract 저장
            if not found_first_section and is_numbered:
                found_first_section = True
                ab = "\n".join(pre_body).strip()
                if len(ab) > 80:
                    sections["abstract"] = ab

            current_key = key
            current_lines = []
            continue

        # ── ## _이탤릭_ 소목차 ──────────────────────────────────────────────
        italic_m = re.match(r"^#{1,3}\s+_(.+?)_\s*$", stripped)
        if italic_m and current_key is not None:
            sub_name = re.sub(r"^\d+(\.\d+)+\.?\s*", "", italic_m.group(1)).strip()
            current_lines.append(f"\n### {sub_name}")
            continue

        # ── > blockquote (abstract 원문) ─────────────────────────────────────
        if stripped.startswith(">"):
            content = re.sub(r"^>\s*", "", stripped)
            # Keywords 줄 제외
            if re.match(r"_?Keywords[_:]", content, re.IGNORECASE):
                continue
            if not found_first_section:
                pre_body.append(content)
            elif current_key:
                current_lines.append(content)
            continue

        # ── 일반 텍스트 ─────────────────────────────────────────────────────
        if current_key is not None:
            current_lines.append(line)
        elif not found_first_section and stripped and not stripped.startswith("**==>"):
            pre_body.append(line)

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
            metadata = _build_metadata(pdf.metadata or {})
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
    doi_m = re.search(r"10\.\d{4,}/[^\s,;)]+", subj)
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

        # 1차: pymupdf4llm (헤더/컬럼/하이픈 자동 처리)
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for i in range(len(doc)):
                md = pymupdf4llm.to_markdown(doc, pages=[i])
                page_map[i + 1] = _clean_text(md)
            metadata = _build_metadata(doc.metadata or {})
            doc.close()
        except Exception as exc:
            logger.warning("S1: pymupdf4llm failed (%s), falling back to pdfplumber", exc)
            warnings.append(f"S1: pdfplumber fallback -- pymupdf4llm error: {exc}")
            page_map, metadata = _try_pdfplumber(pdf_bytes, warnings)
            if not page_map:
                return S1Output(
                    raw_text="",
                    page_map={},
                    section_map={"full_text": ""},
                    metadata=metadata,
                    word_count=0,
                    degraded=True,
                    warnings=warnings + ["both pymupdf4llm and pdfplumber failed"],
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
