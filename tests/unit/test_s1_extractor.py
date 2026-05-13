"""
S1Extractor 단위 테스트.

실제 PDF 실행 — mock 없음.
라이브러리(pymupdf4llm / pdfplumber)의 실제 동작을 함께 검증한다.

Happy path (H):
  H1  정상 텍스트 추출
  H2  PAGE 마커 삽입 확인
  H3  page_map 구성 확인
  H4  섹션 감지 확인 (Abstract/Results 키 존재)
  H5  메타데이터 추출 or warnings 기록

Sad path (S):
  S1  빈 바이트 입력
  S2  PDF 아닌 파일 입력
  S3  섹션 미감지 → degraded mode
  S4  pymupdf4llm 실패 시 pdfplumber 폴백
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.models import S1Output

# S1Extractor는 아직 구현되지 않았다 — import 실패 시 테스트 스킵
try:
    from backend.agents.s1_extractor import S1Extractor
    _S1_AVAILABLE = True
except ImportError:
    _S1_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _S1_AVAILABLE,
    reason="S1Extractor not implemented yet",
)


# ── Happy path ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_h1_extracts_text(sample_pdf_bytes):
    """정상 PDF → raw_text 비어있지 않음, word_count > 0."""
    out: S1Output = await S1Extractor().execute(sample_pdf_bytes)

    assert out.raw_text.strip(), "raw_text가 비어 있음"
    assert out.word_count > 0


@pytest.mark.asyncio
async def test_h2_page_markers_inserted(sample_pdf_bytes):
    """2페이지 PDF → raw_text에 PAGE 마커 두 개 이상 존재."""
    out: S1Output = await S1Extractor().execute(sample_pdf_bytes)

    assert "<!-- PAGE 1 -->" in out.raw_text
    assert "<!-- PAGE 2 -->" in out.raw_text


@pytest.mark.asyncio
async def test_h3_page_map_built(sample_pdf_bytes):
    """page_map[1]이 비어있지 않은 문자열."""
    out: S1Output = await S1Extractor().execute(sample_pdf_bytes)

    assert 1 in out.page_map
    assert isinstance(out.page_map[1], str)
    assert out.page_map[1].strip()


@pytest.mark.asyncio
async def test_h4_sections_detected(sample_pdf_bytes):
    """
    sample_pdf_bytes 에는 명확한 섹션 헤더가 있다.
    section_map에 'abstract' 또는 'results' 키가 존재해야 한다.
    """
    out: S1Output = await S1Extractor().execute(sample_pdf_bytes)

    detected = set(out.section_map.keys())
    assert detected & {"abstract", "results"}, (
        f"예상 섹션 키 없음. 감지된 키: {detected}"
    )


@pytest.mark.asyncio
async def test_h5_metadata_title_or_warned(sample_pdf_bytes):
    """
    메타데이터 title이 추출되거나, 추출 실패 시 warnings에 기록되어야 한다.
    둘 중 하나는 반드시 충족.
    """
    out: S1Output = await S1Extractor().execute(sample_pdf_bytes)

    has_title = out.metadata.title is not None and out.metadata.title.strip()
    has_warning = any("title" in w.lower() or "metadata" in w.lower() for w in out.warnings)

    assert has_title or has_warning, "title도 없고 관련 warning도 없음"


# ── Sad path ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_s1_empty_bytes():
    """
    빈 바이트 입력.
    ValueError를 raise하거나, degraded=True + warnings 비어있지 않음.
    """
    try:
        out: S1Output = await S1Extractor().execute(b"")
        # 예외를 raise하지 않았으면 degraded 상태여야 함
        assert out.degraded is True
        assert out.warnings
    except (ValueError, RuntimeError):
        pass  # 명시적 예외도 허용


@pytest.mark.asyncio
async def test_s2_not_a_pdf():
    """
    PDF가 아닌 파일 입력 (텍스트 파일).
    degraded=True + warnings 비어있지 않거나, 적절한 예외 raise.
    """
    fake = b"This is not a PDF file. Just plain text.\n" * 5

    try:
        out: S1Output = await S1Extractor().execute(fake)
        assert out.degraded is True, "PDF 아닌 파일인데 degraded=False"
        assert out.warnings
    except (ValueError, RuntimeError):
        pass


@pytest.mark.asyncio
async def test_s3_no_sections_detected():
    """
    섹션 헤더가 전혀 없는 PDF (평문 단락만 있음).
    section_map == {"full_text": ...} 이고 degraded=True.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    # 헤더 없이 평문 단락만
    for _ in range(10):
        pdf.multi_cell(0, 6, "This is a generic sentence with no section headers. " * 3, new_x="LMARGIN", new_y="NEXT")

    flat_pdf = pdf.output()
    out: S1Output = await S1Extractor().execute(flat_pdf)

    assert "full_text" in out.section_map, (
        f"섹션 미감지 시 full_text 폴백 없음. 키: {list(out.section_map.keys())}"
    )
    assert out.degraded is True


@pytest.mark.asyncio
async def test_s4_pymupdf_fails_falls_back_to_pdfplumber(sample_pdf_bytes):
    """
    fitz.open 이 예외를 raise해도
    pdfplumber 폴백으로 raw_text는 여전히 채워져야 한다.
    """
    with patch("backend.agents.s1_extractor.fitz.open", side_effect=RuntimeError("fitz 강제 실패")):
        out: S1Output = await S1Extractor().execute(sample_pdf_bytes)

    assert out.raw_text.strip(), "pymupdf 실패 후 pdfplumber 폴백도 빈 텍스트"
    assert any("fallback" in w.lower() or "pdfplumber" in w.lower() for w in out.warnings), (
        "폴백 발생 시 warnings에 기록되어야 함"
    )
