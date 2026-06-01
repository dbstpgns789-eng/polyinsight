"""
공통 pytest fixture.

sample_pdf_bytes  — fpdf2로 생성한 섹션 포함 소형 PDF
                    실제 논문 구조 재현: Abstract / Introduction / Methods / Results / Conclusion
                    수치 "95.3%" 와 "0.1 ms" 포함 → S6 grounding 검증용

mock_section_map  — 위 PDF를 S1이 파싱했다고 가정한 섹션 딕셔너리
mock_card_data    — CardEditorData(2장: cover + closing) → S7/S8 테스트용
"""

from __future__ import annotations

import pytest

from backend.core.models import (
    CardEditorData, CardMeta, CardSlot,
    CardTheme, ClaimType, FieldSource, FieldValue,
    MatchQuality, PaperMetadata, RiskLevel,
    S1Output,
)


# ── PDF fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    """fpdf2로 생성한 2페이지 소형 PDF."""
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed — run: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content_page1 = [
        ("B", 16, "Highly Sensitive Carbon Nanotube Gas Sensor"),
        ("",  11, "Kim Minjun, Lee Sooyeon - KITECH, 2024"),
        ("",  11, ""),
        ("B", 13, "Abstract"),
        ("",  11,
         "We developed a carbon nanotube-based gas sensor achieving 95.3% detection "
         "accuracy with a response time of 0.1 ms, a 40% improvement over prior work."),
        ("",  11, ""),
        ("B", 13, "Introduction"),
        ("",  11,
         "Conventional sensors suffer from low sensitivity and slow response. "
         "This study aims to overcome these limitations using CVD-grown CNT arrays."),
    ]
    for style, size, text in content_page1:
        pdf.set_font("Helvetica", style=style, size=size)
        pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    pdf.add_page()
    content_page2 = [
        ("B", 13, "Methods"),
        ("",  11,
         "CNTs were synthesized by chemical vapor deposition (CVD). "
         "Electrochemical measurements were conducted at room temperature."),
        ("",  11, ""),
        ("B", 13, "Results"),
        ("",  11,
         "Table 1. Performance: accuracy 95.3%, response time 0.1 ms. "
         "Compared to baseline: 40% improvement in accuracy, 60% reduction in response time."),
        ("",  11, ""),
        ("B", 13, "Conclusion"),
        ("",  11,
         "A high-performance gas sensor was developed and practical applicability confirmed."),
    ]
    for style, size, text in content_page2:
        pdf.set_font("Helvetica", style=style, size=size)
        pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


# ── Section map fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_section_map() -> dict[str, str]:
    return {
        "abstract": (
            "We developed a carbon nanotube-based gas sensor achieving 95.3% detection "
            "accuracy with a response time of 0.1 ms, a 40% improvement over prior work."
        ),
        "introduction": (
            "Conventional sensors suffer from low sensitivity and slow response. "
            "This study aims to overcome these limitations using CVD-grown CNT arrays."
        ),
        "methods": (
            "CNTs were synthesized by chemical vapor deposition (CVD). "
            "Electrochemical measurements were conducted at room temperature."
        ),
        "results": (
            "Table 1. Performance: accuracy 95.3%, response time 0.1 ms. "
            "Compared to baseline: 40% improvement in accuracy, 60% reduction in response time."
        ),
        "conclusion": (
            "A high-performance gas sensor was developed and practical applicability confirmed."
        ),
    }


@pytest.fixture
def degraded_section_map() -> dict[str, str]:
    return {
        "full_text": (
            "We developed a carbon nanotube-based gas sensor achieving 95.3% accuracy. "
            "CNTs were synthesized by CVD. Response time was 0.1 ms."
        )
    }


# ── FieldValue helper ─────────────────────────────────────────────────────────

def _fv(
    value: str,
    *,
    section: str = "results",
    page: int = 2,
    risk: str = "LOW",
    quality: str = "exact",
    claim: str = "qualitative",
    confidence: str = "high",
) -> FieldValue:
    return FieldValue(
        value=value,
        confidence=confidence,           # type: ignore[arg-type]
        match_quality=MatchQuality(quality),
        claim_type=ClaimType(claim),
        source=FieldSource(section=section, page=page),
        risk_level=RiskLevel(risk),
    )


# ── CardEditorData fixture (v2 — CardSlot 기반) ───────────────────────────────

@pytest.fixture
def mock_card_data() -> CardEditorData:
    """
    2장(cover + closing)의 CardEditorData.
    S7/S8 테스트에서 LLM 없이 바로 사용.
    CRITICAL 필드 포함 → risk 집계 테스트도 가능.
    """
    meta = CardMeta(
        org=_fv("한국생산기술연구원", section="abstract", page=1),
        dept=_fv("나노소재연구부", section="abstract", page=1),
        researcher=_fv("김민준", section="abstract", page=1),
        month=_fv("2024-03", section="abstract", page=1, quality="normalized"),
        edition_number=_fv("2024-01", section="abstract", page=1, quality="normalized"),
    )

    cover = CardSlot(
        card_num=1,
        template_type="cover",
        fields={
            "title": _fv(
                "탄소나노튜브 기반 고감도 가스 센서 개발",
                section="abstract", page=1,
            ),
            "subtitle": _fv(
                "95.3% 정확도, 0.1 ms 응답속도 달성",
                section="results", page=2,
                risk="CRITICAL", quality="exact", claim="quantitative",
            ),
            "edition": _fv("2024-01호", section="abstract", page=1),
        },
    )

    closing = CardSlot(
        card_num=2,
        template_type="closing",
        fields={
            "pre_title": _fv("실용화 가능성 확인", section="conclusion", page=2),
            "main_title": _fv("차세대 가스 센서 기술 선도", section="conclusion", page=2),
            "cta": _fv("논문 원문 확인하기", section="conclusion", page=2),
            "team_name": _fv("나노소재연구부 김민준 박사팀", section="abstract", page=1),
        },
    )

    return CardEditorData(meta=meta, cards=[cover, closing])


# ── Theme fixture ─────────────────────────────────────────────────────────────

@pytest.fixture
def mock_theme() -> CardTheme:
    return CardTheme(primary="#3BAF6B", dark="#228B4E")


# ── S1Output fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_s1_output(mock_section_map) -> S1Output:
    raw = (
        "<!-- PAGE 1 -->\n"
        "Highly Sensitive Carbon Nanotube Gas Sensor\n"
        "Abstract\n"
        "We developed a carbon nanotube-based gas sensor achieving 95.3% detection accuracy "
        "with a response time of 0.1 ms, a 40% improvement over prior work.\n"
        "Introduction\n"
        "Conventional sensors suffer from low sensitivity and slow response.\n"
        "<!-- PAGE 2 -->\n"
        "Methods\n"
        "CNTs were synthesized by CVD.\n"
        "Results\n"
        "Table 1. Performance: accuracy 95.3%, response time 0.1 ms.\n"
        "Conclusion\n"
        "A high-performance gas sensor was developed.\n"
    )
    return S1Output(
        raw_text=raw,
        page_map={1: "Highly Sensitive Carbon Nanotube...", 2: "Methods\nCNTs were..."},
        section_map=mock_section_map,
        metadata=PaperMetadata(
            title="Highly Sensitive Carbon Nanotube Gas Sensor",
            authors=["Kim Minjun", "Lee Sooyeon"],
            year=2024,
            doi="10.1234/example",
        ),
        word_count=len(raw.split()),
    )
