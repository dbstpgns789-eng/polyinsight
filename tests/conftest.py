"""
공통 pytest fixture.

sample_pdf_bytes  — fpdf2로 생성한 섹션 포함 소형 PDF
                    실제 논문 구조 재현: Abstract / Introduction / Methods / Results / Conclusion
                    수치 "95.3%" 와 "0.1 ms" 포함 → S6 grounding 검증용

mock_section_map  — 위 PDF를 S1이 파싱했다고 가정한 섹션 딕셔너리
mock_card_data    — CardEditorData 완전 채움 → S6/S7/S8 테스트용
"""

from __future__ import annotations

import io
from datetime import datetime

import pytest

from backend.core.models import (
    Card1, Card2, Card3, Card4, Card5,
    CardEditorData, CardMeta,
    ClaimType, FieldSource, FieldValue,
    MatchQuality, PaperMetadata, RiskLevel,
    S1Output,
)


# ── PDF fixture ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    """
    fpdf2로 생성한 2페이지 소형 PDF.
    섹션 헤더(Abstract/Introduction/Methods/Results/Conclusion)와
    수치("95.3%", "0.1 ms")가 명시적으로 포함된다.
    """
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
        ("",  11, "Kim Minjun, Lee Sooyeon — KITECH, 2024"),
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
        pdf.multi_cell(0, 6, text)

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
        pdf.multi_cell(0, 6, text)

    return pdf.output()


# ── Section map fixture ───────────────────────────────────────────────────────

@pytest.fixture
def mock_section_map() -> dict[str, str]:
    """sample_pdf_bytes 를 S1이 파싱했다고 가정한 결과."""
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
    """S1이 섹션을 감지하지 못해 degraded mode로 반환한 섹션맵."""
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
        confidence=confidence,  # type: ignore[arg-type]
        match_quality=MatchQuality(quality),
        claim_type=ClaimType(claim),
        source=FieldSource(section=section, page=page),
        risk_level=RiskLevel(risk),
    )


# ── CardEditorData fixture ────────────────────────────────────────────────────

@pytest.fixture
def mock_card_data() -> CardEditorData:
    """
    완전히 채워진 CardEditorData.
    S6 / S7 / S8 테스트에서 LLM을 거치지 않고 바로 사용.
    수치 필드는 CRITICAL 위험도로 설정해 risk 집계 테스트도 가능.
    """
    meta = CardMeta(
        org=_fv("한국생산기술연구원", section="abstract", page=1, risk="LOW", quality="exact"),
        dept=_fv("나노소재연구부", section="abstract", page=1, risk="LOW", quality="exact"),
        researcher=_fv("김민준", section="abstract", page=1, risk="LOW", quality="exact"),
        month=_fv("2024-03", section="abstract", page=1, risk="LOW", quality="normalized"),
        edition_number=_fv("2024-01", section="abstract", page=1, risk="LOW", quality="normalized"),
    )
    card1 = Card1(
        pretitle=_fv("나노소재 연구 성과", section="abstract", page=1),
        title=_fv("탄소나노튜브 기반 고감도 가스 센서 개발", section="abstract", page=1),
        mascot_bubble=_fv("95.3% 정확도 달성!", section="results", page=2, claim="quantitative"),
    )
    card2 = Card2(
        intro=_fv("기존 센서의 낮은 민감도와 느린 응답속도 문제", section="introduction", page=1),
        keyword_line=_fv("CNT · CVD · 전기화학 · 가스 센서", section="methods", page=2),
        footnote=_fv("Kim et al., KITECH 2024", section="abstract", page=1),
    )
    card3 = Card3(
        problem=_fv("기존 대비 민감도 40% 낮음, 응답시간 2배 느림", section="introduction", page=1),
        achievement=_fv(
            "정확도 95.3%, 응답시간 0.1 ms 달성",
            section="results", page=2,
            risk="CRITICAL", quality="exact", claim="quantitative",
        ),
        mascot_bubble=_fv("기존 대비 40% 향상!", section="results", page=2),
        photo_caption=_fv("CNT 어레이 SEM 이미지 (×50,000)", section="methods", page=2),
    )
    card4 = Card4(
        before_label=_fv("기존 센서", section="introduction", page=1),
        after_label=_fv("CNT 센서 (본 연구)", section="results", page=2),
        description=_fv("CVD 공정으로 CNT 합성 후 전기화학 측정", section="methods", page=2),
        result=_fv(
            "응답시간 0.1 ms (기존 0.25 ms 대비 60% 단축)",
            section="results", page=2,
            risk="CRITICAL", quality="exact", claim="quantitative",
        ),
        mascot_bubble=_fv("60% 빠른 응답속도!", section="results", page=2),
    )
    card5 = Card5(
        pre_title=_fv("실용화 가능성 확인", section="conclusion", page=2),
        main_title=_fv("차세대 가스 센서 기술 선도", section="conclusion", page=2),
        cta=_fv("논문 원문 확인하기", section="conclusion", page=2),
        team_name=_fv("나노소재연구부 김민준 박사팀", section="abstract", page=1),
    )
    return CardEditorData(
        meta=meta,
        card1=card1,
        card2=card2,
        card3=card3,
        card4=card4,
        card5=card5,
        layout_variants={
            "card1": "A", "card2": "A", "card3": "A", "card4": "A", "card5": "A"
        },
    )


@pytest.fixture
def mock_theme() -> dict:
    return {"primary": "#3BAF6B", "dark": "#228B4E"}


# ── S1Output fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_s1_output(mock_section_map) -> S1Output:
    """mock_section_map을 포함한 완전한 S1Output."""
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
