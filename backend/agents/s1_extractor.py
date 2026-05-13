from __future__ import annotations

import logging
import re
from io import BytesIO

import pdfplumber

from ..core.models import PaperMetadata, S1Output

logger = logging.getLogger(__name__)

# 섹션 헤더로 인식할 키워드 (소문자 비교)
_SECTION_PATTERNS = [
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


class S1Extractor:
    """S1: PDF bytes → raw_text + page_map + section_map + metadata."""

    MIN_WORD_COUNT = 50

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

        # ── 1차: pymupdf4llm.to_markdown ─────────────────────────────────────
        try:
            import pymupdf4llm
            import fitz  # PyMuPDF — bundled with pymupdf4llm

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for i, page in enumerate(doc, start=1):
                md = pymupdf4llm.to_markdown(doc, pages=[i - 1])
                page_map[i] = md.strip()

            # 메타데이터
            meta = doc.metadata or {}
            metadata = self._build_metadata(meta)
            doc.close()

        except Exception as exc:
            logger.warning("S1: pymupdf4llm failed (%s), falling back to pdfplumber", exc)
            warnings.append(f"S1: pdfplumber fallback — pymupdf4llm error: {exc}")

            # ── 2차: pdfplumber 폴백 ─────────────────────────────────────────
            page_map, metadata = self._try_pdfplumber(pdf_bytes, warnings)

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

        # ── raw_text 조합 (PAGE 마커 삽입) ───────────────────────────────────
        parts: list[str] = []
        for page_num in sorted(page_map):
            parts.append(f"<!-- PAGE {page_num} -->")
            parts.append(page_map[page_num])
        raw_text = "\n".join(parts)

        word_count = len(raw_text.split())

        if word_count < self.MIN_WORD_COUNT:
            warnings.append(f"S1: low word count ({word_count}) — possible scan or empty PDF")

        # ── 섹션 파싱 ────────────────────────────────────────────────────────
        section_map, degraded = self._parse_sections(raw_text)

        if degraded:
            warnings.append("S1: no section headers detected — degraded mode")

        # 메타데이터 title 경고
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

    # ── pdfplumber 폴백 ───────────────────────────────────────────────────────

    def _try_pdfplumber(
        self, pdf_bytes: bytes, warnings: list[str]
    ) -> tuple[dict[int, str], PaperMetadata]:
        page_map: dict[int, str] = {}
        metadata = PaperMetadata(title=None, authors=[], year=None, doi=None)
        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                meta = pdf.metadata or {}
                metadata = self._build_metadata(meta)
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    page_map[i] = text.strip()
        except Exception as exc:
            warnings.append(f"S1: pdfplumber error — {exc}")
        return page_map, metadata

    # ── 섹션 파싱 ────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_sections(raw_text: str) -> tuple[dict[str, str], bool]:
        """
        섹션 헤더를 찾아 section_map을 만든다.
        헤더 미감지 시 {"full_text": raw_text}를 반환하고 degraded=True.
        """
        lines = raw_text.splitlines()
        sections: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()

            # PAGE 마커는 섹션 텍스트에 포함시키지 않음
            if lower.startswith("<!-- page"):
                continue

            # pymupdf4llm은 "## **Abstract**" 형식으로 출력 — **...** 제거 후 비교
            normalized = re.sub(r"\*+", "", lower).strip()
            # Markdown 헤더 기호(#) 제거
            normalized_no_hash = re.sub(r"^#{1,3}\s*", "", normalized).strip()

            matched_section = None
            for pat in _SECTION_PATTERNS:
                # 평문 헤더: "Abstract", "1. Introduction", "Methods."
                if re.fullmatch(
                    rf"(?:\d+[\.\s]+)?{re.escape(pat)}[\.\s]*",
                    normalized_no_hash,
                    re.IGNORECASE,
                ):
                    matched_section = pat
                    break
                # Markdown 헤더: "# Abstract", "## **Results**"
                if re.fullmatch(
                    rf"#{1,3}\s*(?:\d+[\.\s]+)?{re.escape(pat)}[\.\s]*",
                    normalized,
                    re.IGNORECASE,
                ):
                    matched_section = pat
                    break

            if matched_section:
                if current_key is not None:
                    sections[current_key] = "\n".join(current_lines).strip()
                # 소문자 정규화 (예: "Materials and Methods" → "methods")
                current_key = matched_section.replace(" and ", " ").split()[0]
                if matched_section == "materials and methods":
                    current_key = "methods"
                elif matched_section == "related work":
                    current_key = "introduction"
                current_lines = []
            else:
                if current_key is not None:
                    current_lines.append(line)

        if current_key is not None:
            sections[current_key] = "\n".join(current_lines).strip()

        if not sections:
            return {"full_text": raw_text}, True

        return sections, False

    # ── 메타데이터 빌더 ──────────────────────────────────────────────────────

    @staticmethod
    def _build_metadata(meta: dict) -> PaperMetadata:
        title = meta.get("title") or meta.get("Title") or None
        author_raw = meta.get("author") or meta.get("Author") or ""
        authors = [a.strip() for a in re.split(r"[;,]", author_raw) if a.strip()]

        date_raw = meta.get("creationDate") or meta.get("CreationDate") or ""
        year_match = re.search(r"(\d{4})", date_raw)
        year = int(year_match.group(1)) if year_match else None

        subj = (meta.get("subject") or meta.get("Subject") or "") + (
            meta.get("keywords") or meta.get("Keywords") or ""
        )
        doi_match = re.search(r"10\.\d{4,}/\S+", subj)
        doi = doi_match.group(0).rstrip(".,)") if doi_match else None

        return PaperMetadata(title=title, authors=authors, year=year, doi=doi)
