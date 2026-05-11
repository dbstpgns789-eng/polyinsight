from __future__ import annotations

import logging
import re
from io import BytesIO

import pdfplumber
import fitz  # PyMuPDF

from .base import BaseAgent
from ..core.models import PaperMetadata, S1Input, S1Output

logger = logging.getLogger(__name__)


class S1ExtractorAgent(BaseAgent[S1Input, S1Output]):
    """S1: PDF → raw_text + page_map + metadata."""

    MIN_TEXT_RATIO = 0.10   # 페이지당 글자 수 / 페이지 면적 비율 하한 (스캔본 판별)
    MIN_WORD_COUNT = 100    # 유효 논문 최소 단어 수

    async def execute(self, input_data: S1Input) -> S1Output:
        pdf_bytes = input_data.pdf_bytes
        warnings: list[str] = []

        # ── 1차: pdfplumber ───────────────────────────────────────────────────
        page_map, metadata = self._try_pdfplumber(pdf_bytes, warnings)

        # pdfplumber 실패 또는 텍스트 희박 → PyMuPDF 폴백
        if not page_map or self._is_sparse(page_map):
            logger.warning("S1: pdfplumber sparse/failed, trying PyMuPDF")
            warnings.append("S1: fallback to PyMuPDF")
            page_map = self._try_pymupdf(pdf_bytes)
            if not page_map:
                raise RuntimeError("ERR-S1-001: both pdfplumber and PyMuPDF failed")

        raw_text = "\n\n".join(page_map[p] for p in sorted(page_map))
        word_count = len(raw_text.split())

        if word_count < self.MIN_WORD_COUNT:
            warnings.append(f"S1: low word count ({word_count}) — possible scan or empty PDF")

        return S1Output(
            raw_text=raw_text,
            page_map=page_map,
            metadata=metadata,
            word_count=word_count,
            warnings=warnings,
        )

    # ── pdfplumber ────────────────────────────────────────────────────────────

    def _try_pdfplumber(
        self, pdf_bytes: bytes, warnings: list[str]
    ) -> tuple[dict[int, str], PaperMetadata]:
        page_map: dict[int, str] = {}
        metadata = PaperMetadata(title=None, authors=[], year=None, doi=None)
        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                # 메타데이터
                meta = pdf.metadata or {}
                metadata = PaperMetadata(
                    title=meta.get("Title") or None,
                    authors=self._parse_authors(meta.get("Author", "")),
                    year=self._parse_year(meta.get("CreationDate", "")),
                    doi=self._extract_doi(meta.get("Subject", "") + meta.get("Keywords", "")),
                )
                # 페이지 텍스트
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    page_map[i] = text.strip()
        except Exception as exc:
            warnings.append(f"S1: pdfplumber error — {exc}")
        return page_map, metadata

    def _is_sparse(self, page_map: dict[int, str]) -> bool:
        """추출된 텍스트가 너무 적으면 스캔본으로 간주."""
        total_chars = sum(len(t) for t in page_map.values())
        return total_chars < 200 * len(page_map)  # 페이지당 평균 200자 미만

    # ── PyMuPDF ───────────────────────────────────────────────────────────────

    def _try_pymupdf(self, pdf_bytes: bytes) -> dict[int, str]:
        page_map: dict[int, str] = {}
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for i, page in enumerate(doc, start=1):
                page_map[i] = page.get_text("text").strip()
            doc.close()
        except Exception as exc:
            logger.error("S1: PyMuPDF error — %s", exc)
        return page_map

    # ── 메타데이터 파싱 헬퍼 ─────────────────────────────────────────────────

    @staticmethod
    def _parse_authors(raw: str) -> list[str]:
        if not raw:
            return []
        return [a.strip() for a in re.split(r"[;,]", raw) if a.strip()]

    @staticmethod
    def _parse_year(creation_date: str) -> int | None:
        m = re.search(r"(\d{4})", creation_date)
        return int(m.group(1)) if m else None

    @staticmethod
    def _extract_doi(text: str) -> str | None:
        m = re.search(r"10\.\d{4,}/\S+", text)
        return m.group(0).rstrip(".,)") if m else None


s1_agent = S1ExtractorAgent()
