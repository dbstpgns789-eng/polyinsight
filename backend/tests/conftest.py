"""공유 픽스처 — 논문 텍스트 및 mock CardEditorData."""
from __future__ import annotations

import pathlib
import pytest
from dotenv import load_dotenv

# polyinsight/.env 자동 로드 (GEMINI_API_KEY 등)
load_dotenv(pathlib.Path(__file__).parents[2] / ".env")

# 테스트 논문 경로 (절대경로)
PAPER_MD = pathlib.Path(
    r"C:\Users\User\OneDrive\Desktop\한국생산기술연구원_근로장학"
    r"\poly_claude_code\논문"
    r"\80 [cellulose_2024] Fabrication of composite microbeads consisting of cellulose"
    r" and covalent organic nanosheets via electrospray process (1) (2).md"
)


@pytest.fixture(scope="session")
def paper_text() -> str:
    """논문 MD 파일의 원문 텍스트."""
    return PAPER_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def paper_section_map() -> dict[str, str]:
    """테스트용 수동 section_map (S6 입력으로 사용)."""
    text = PAPER_MD.read_text(encoding="utf-8")

    # Abstract: 파일 상단의 첫 번째 긴 단락
    abstract_start = text.find("Abstract")
    abstract_end = text.find("Introduction")
    abstract = text[abstract_start + len("Abstract"):abstract_end].strip() if abstract_start != -1 else ""

    # Introduction
    intro_start = text.find("Introduction")
    methods_start = text.find("Materials and methods")
    introduction = text[intro_start + len("Introduction"):methods_start].strip() if intro_start != -1 else ""

    # Methods
    results_start = text.find("Results and discussion")
    methods = text[methods_start + len("Materials and methods"):results_start].strip() if methods_start != -1 else ""

    # Results
    conclusion_start = text.find("Conclusion")
    results = text[results_start + len("Results and discussion"):conclusion_start].strip() if results_start != -1 else ""

    # Conclusion
    conclusion = text[conclusion_start + len("Conclusion"):].strip()[:3000] if conclusion_start != -1 else ""

    return {
        "Abstract": abstract[:2000],
        "Introduction": introduction[:3000],
        "Methods": methods[:3000],
        "Results": results[:4000],
        "Conclusion": conclusion,
    }


@pytest.fixture(scope="session")
def mock_card_data():
    """테스트용 최소 CardEditorData (실제 값, LLM 불필요)."""
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

    from backend.core.models import (
        CardEditorData, CardMeta, Card1, Card2, Card3, Card4, Card5,
        FieldValue, FieldSource, MatchQuality, RiskLevel, ClaimType,
    )

    def fv(value: str, mq: MatchQuality = MatchQuality.EXACT) -> FieldValue:
        return FieldValue(
            value=value,
            confidence="high",
            match_quality=mq,
            claim_type=ClaimType.QUALITATIVE,
            source=FieldSource(section="Abstract", page=1),
            risk_level=RiskLevel.LOW,
            verified=False,
        )

    return CardEditorData(
        meta=CardMeta(
            org=fv("한국생산기술연구원"),
            dept=fv("융합기술연구소"),
            researcher=fv("이호익"),
            month=fv("2024-01"),
            edition_number=fv("80"),
        ),
        card1=Card1(
            pretitle=fv("셀룰로오스 마이크로비드"),
            title=fv("전기분무 기반 친환경 복합 마이크로비드 제조"),
            mascot_bubble=fv("마이크로플라스틱을 대체합니다"),
        ),
        card2=Card2(
            intro=fv("마이크로플라스틱 문제를 해결하는 생분해성 셀룰로오스 마이크로비드"),
            keyword_line=fv("셀룰로오스 · 전기분무 · CON · 복합재 · 기계적 특성"),
            footnote=fv("Cellulose (2024) doi:10.1007/s10570-024-05757-4"),
        ),
        card3=Card3(
            problem=fv("석유계 마이크로플라스틱의 환경 오염"),
            achievement=fv("압축강도 238 ± 18 MPa 달성 — 폴리프로필렌(199 MPa) 초과"),
            mascot_bubble=fv("강도를 높였습니다"),
            photo_caption=fv("SEM 이미지: 전기분무로 제조한 셀룰로오스 마이크로비드"),
        ),
        card4=Card4(
            before_label=fv("순수 셀룰로오스 마이크로비드"),
            after_label=fv("CON 복합 마이크로비드"),
            description=fv("공유결합 유기 나노시트(CON) 첨가로 기계적 특성 향상"),
            result=fv("압축강도 68% 향상 (142 → 238 MPa)", MatchQuality.NORMALIZED),
            mascot_bubble=fv("CON이 핵심입니다"),
        ),
        card5=Card5(
            pre_title=fv("친환경 소재 연구"),
            main_title=fv("마이크로플라스틱, 이제 대체할 수 있습니다"),
            cta=fv("자세한 내용은 KITECH 연구팀에 문의하세요"),
            team_name=fv("한국생산기술연구원 융합기술연구소"),
        ),
        layout_variants={"1": "A", "2": "B", "3": "B", "4": "D", "5": "A"},
    )
