# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
from io import BytesIO

import pdfplumber
import pymupdf4llm
import fitz

from .base import BaseAgent
from ..core.models import DegradeCode, DegradeEvent, PaperMetadata, S1Input, S1Output

logger = logging.getLogger(__name__)


def build_s1_degrade_events(
    *, word_count: int, min_word_count: int,
    section_degraded: bool, parse_fallback: bool,
) -> list[DegradeEvent]:
    """S1 degrade 사유를 타입드 이벤트로. EXTRACT_FAILED는 execute()의 빈입력/양쪽실패
    경로에서 직접 emit(여기 인자에 없음)."""
    events: list[DegradeEvent] = []
    if parse_fallback:
        events.append(DegradeEvent(code=DegradeCode.S1_PARSE_FALLBACK))
    if word_count < min_word_count:
        events.append(DegradeEvent(code=DegradeCode.S1_LOW_WORDS, detail=f"{word_count} words"))
    if section_degraded:
        events.append(DegradeEvent(code=DegradeCode.S1_NO_SECTIONS))
    return events


def _clean_text(text: str) -> str:
    # soft hyphen 제거, 줄 내부 연속 공백 정규화 (줄바꿈 보존)
    text = text.replace("\xad", "")
    lines = [re.sub(r"[ \t]+", " ", line) for line in text.splitlines()]
    return "\n".join(lines).strip()


# 번호 없는 종결 섹션 (numbered 아니어도 실제 섹션으로 인정)
_TERMINAL_SECTIONS = {
    # 영어
    "abstract", "introduction", "background",
    "methods", "method", "methodology", "materials and methods",
    "results", "results and discussion", "discussion",
    "conclusion", "conclusions",
    "references", "acknowledgments", "acknowledgements",
    "declaration of competing interest",
    "credit authorship contribution statement", "data availability",
    # 한국어
    "초록", "요약",
    "서론", "배경",
    "방법", "방법론", "연구 방법", "재료 및 방법", "실험 방법",
    "결과", "연구 결과", "결과 및 고찰",
    "고찰", "논의",
    "결론", "결론 및 제언",
    "참고문헌", "감사의 말", "감사의 글",
}


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

        # ── ## 평문 헤더 폴백 (bold 없음: bioRxiv/arXiv/ChemSusChem 스타일) ─────
        # bold_m이 이미 처리했으므로 여기는 bold 없는 경우만. 번호 섹션 or TERMINAL만 허용.
        if not bold_m:
            plain_m = re.match(r"^#{1,3}\s+(.+?)\s*$", stripped)
            if plain_m:
                raw_hdr = plain_m.group(1).strip()
                is_numbered = bool(re.match(r"^\d+[\.\s]", raw_hdr))
                key = re.sub(r"^\d+(\.\d+)*\.?\s*", "", raw_hdr).strip().lower()
                is_real = is_numbered or key in _TERMINAL_SECTIONS
                if is_real and key:
                    if current_key is not None:
                        body = "\n".join(current_lines).strip()
                        if body:
                            sections.setdefault(current_key, body)
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


class S1Extractor(BaseAgent[S1Input, S1Output]):
    _MIN_WORD_COUNT = 100

    async def execute(self, input_data: S1Input) -> S1Output:
        pdf_bytes = input_data.pdf_bytes
        if not pdf_bytes:
            return S1Output(
                raw_text="",
                page_map={},
                section_map={"full_text": ""},
                metadata=PaperMetadata(title=None, authors=[], year=None, doi=None),
                word_count=0,
                degraded=True,
                warnings=["empty input bytes"],
                degrade_events=[DegradeEvent(code=DegradeCode.S1_EXTRACT_FAILED)],
            )

        warnings: list[str] = []
        page_map: dict[int, str] = {}
        metadata = PaperMetadata(title=None, authors=[], year=None, doi=None)
        parse_fallback = False

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
            parse_fallback = True
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
                    degrade_events=[DegradeEvent(code=DegradeCode.S1_EXTRACT_FAILED)],
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
            degrade_events=build_s1_degrade_events(
                word_count=word_count, min_word_count=self._MIN_WORD_COUNT,
                section_degraded=section_degraded, parse_fallback=parse_fallback,
            ),
        )


s1_agent = S1Extractor()
