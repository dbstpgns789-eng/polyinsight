# -*- coding: utf-8 -*-
"""S1 스캔본 OCR 폴백 (2026-07-21).

정상 추출이 단어를 거의 못 뽑으면(=텍스트 레이어 없는 스캔) fitz 내장 Tesseract로 재추출한다.
실제 OCR은 Tesseract 언어데이터가 있는 서버(Docker)에서만 돈다 — 여기선 _ocr_extract를 mock해
**배선**을 검증한다: 언제 발동하나 / OCR이 도우면 교체하나 / OCR이 죽으면 안전하게 폴백하나.
"""
from unittest.mock import patch

import pytest

from backend.agents.s1_extractor import S1Extractor
from backend.core.config import settings
from backend.core.models import S1Input


def _blank_pdf_bytes() -> bytes:
    """텍스트 없는 1페이지 PDF (스캔 흉내 — 실제 스캔 대신 빈 페이지)."""
    import fitz
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.asyncio
async def test_ocr_triggers_on_low_word_count_and_replaces_text(monkeypatch):
    """스캔(단어 거의 0)이면 OCR을 부르고, OCR이 텍스트를 뽑으면 그걸 쓴다."""
    monkeypatch.setattr(settings, "OCR_ENABLED", True)
    ocr_pages = {1: "OCR로 복원된 본문 " * 40}   # 충분한 단어 수

    with patch("backend.agents.s1_extractor._ocr_extract", return_value=ocr_pages) as m:
        out = await S1Extractor().execute(S1Input(job_id="j", pdf_bytes=_blank_pdf_bytes()))

    assert m.called                              # 스캔 감지 → OCR 시도
    assert out.word_count > 100                  # OCR 텍스트로 교체됨
    assert "OCR로 복원된" in out.raw_text
    assert any("OCR" in w for w in out.warnings)


@pytest.mark.asyncio
async def test_ocr_not_triggered_for_normal_paper(monkeypatch):
    """정상 논문(단어 충분)엔 OCR을 부르지 않는다 — 비용·지연 0.

    (로컬 Windows에선 pymupdf4llm 서브프로세스가 인코딩 오류로 0단어를 내므로 — 서버 Linux는
    정상 — 정상 추출을 패치로 흉내낸다. 검증 대상은 '단어 충분하면 OCR 스킵'이라는 배선이다.)
    """
    monkeypatch.setattr(settings, "OCR_ENABLED", True)

    with patch("backend.agents.s1_extractor.pymupdf4llm.to_markdown",
               return_value="normal paper with plenty of extractable words "  * 60), \
         patch("backend.agents.s1_extractor._ocr_extract") as m:
        out = await S1Extractor().execute(S1Input(job_id="j", pdf_bytes=_blank_pdf_bytes()))

    assert not m.called
    assert out.word_count > 100


@pytest.mark.asyncio
async def test_ocr_failure_falls_back_safely(monkeypatch):
    """Tesseract 미설치 등으로 OCR이 빈 결과면 크래시 없이 degraded로 떨어진다(기존 동작 보존)."""
    monkeypatch.setattr(settings, "OCR_ENABLED", True)

    with patch("backend.agents.s1_extractor._ocr_extract", return_value={}):
        out = await S1Extractor().execute(S1Input(job_id="j", pdf_bytes=_blank_pdf_bytes()))

    assert out.degraded                          # 여전히 degraded (OCR도 실패)
    # 크래시하지 않고 정상 S1Output 반환


@pytest.mark.asyncio
async def test_ocr_disabled_skips_entirely(monkeypatch):
    """OCR_ENABLED=False면 스캔이어도 OCR을 안 부른다."""
    monkeypatch.setattr(settings, "OCR_ENABLED", False)

    with patch("backend.agents.s1_extractor._ocr_extract") as m:
        out = await S1Extractor().execute(S1Input(job_id="j", pdf_bytes=_blank_pdf_bytes()))

    assert not m.called
    assert out.degraded
