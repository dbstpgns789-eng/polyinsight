"""S1 Extractor 단위 테스트 — 실제 PDF 없이 mock bytes로 검증."""
from __future__ import annotations

import io
import struct
import pytest

# 최소한의 유효 PDF bytes (텍스트 레이어 포함)
MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f\r
0000000009 00000 n\r
0000000058 00000 n\r
0000000115 00000 n\r
0000000274 00000 n\r
0000000370 00000 n\r
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""

GARBAGE_BYTES = b"This is not a PDF at all"


@pytest.fixture
def agent():
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))
    from backend.agents.s1_extractor import S1ExtractorAgent
    return S1ExtractorAgent()


# ── helpers ───────────────────────────────────────────────────────────────────

def test_parse_authors(agent):
    # 쉼표·세미콜론 모두 구분자
    assert agent._parse_authors("Kim, J; Lee, S") == ["Kim", "J", "Lee", "S"]
    assert agent._parse_authors("Alice Johnson") == ["Alice Johnson"]
    assert agent._parse_authors("") == []


def test_parse_year(agent):
    assert agent._parse_year("D:20230815120000") == 2023
    assert agent._parse_year("no year here") is None


def test_extract_doi(agent):
    assert agent._extract_doi("doi: 10.1038/s41586-021-03819-2") == "10.1038/s41586-021-03819-2"
    assert agent._extract_doi("no doi") is None


def test_is_sparse_empty(agent):
    page_map = {1: "", 2: ""}
    assert agent._is_sparse(page_map) is True


def test_is_sparse_rich(agent):
    page_map = {1: "word " * 300, 2: "word " * 300}
    assert agent._is_sparse(page_map) is False


# ── PyMuPDF 폴백 (garbage bytes → 빈 page_map 반환, 예외 없음) ───────────────

def test_pymupdf_garbage(agent):
    result = agent._try_pymupdf(GARBAGE_BYTES)
    assert isinstance(result, dict)   # 예외 없이 빈 dict 반환


# ── S1Output 구조 검증 (pdfplumber가 열 수 있는 최소 PDF) ────────────────────

@pytest.mark.asyncio
async def test_execute_minimal_pdf(agent):
    from backend.core.models import S1Input
    inp = S1Input(job_id="test-001", pdf_bytes=MINIMAL_PDF)
    out = await agent.execute(inp)
    assert out.raw_text is not None
    assert isinstance(out.page_map, dict)
    assert out.word_count >= 0
    assert isinstance(out.warnings, list)
    assert out.metadata is not None


@pytest.mark.asyncio
async def test_execute_garbage_raises(agent):
    from backend.core.models import S1Input
    inp = S1Input(job_id="test-002", pdf_bytes=GARBAGE_BYTES)
    with pytest.raises(RuntimeError, match="ERR-S1-001"):
        await agent.execute(inp)
