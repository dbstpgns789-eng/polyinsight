"""공유 픽스처."""
from __future__ import annotations

import pathlib
import pytest
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parents[2] / ".env")

PAPER_MD = pathlib.Path(
    r"C:\Users\User\OneDrive\Desktop\한국생산기술연구원_근로장학"
    r"\poly_claude_code\논문"
    r"\80 [cellulose_2024] Fabrication of composite microbeads consisting of cellulose"
    r" and covalent organic nanosheets via electrospray process (1) (2).md"
)


@pytest.fixture(scope="session")
def paper_text() -> str:
    return PAPER_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def paper_section_map() -> dict[str, str]:
    text = PAPER_MD.read_text(encoding="utf-8")

    def _slice(start_kw, end_kw, limit=3000):
        s = text.find(start_kw)
        e = text.find(end_kw) if end_kw else len(text)
        if s == -1:
            return ""
        return text[s + len(start_kw):e].strip()[:limit]

    return {
        "Abstract":     _slice("Abstract", "Introduction", 2000),
        "Introduction": _slice("Introduction", "Materials and methods", 3000),
        "Methods":      _slice("Materials and methods", "Results and discussion", 3000),
        "Results":      _slice("Results and discussion", "Conclusion", 4000),
        "Conclusion":   _slice("Conclusion", None, 3000),
    }


@pytest.fixture
def mock_card_data():
    """테스트용 최소 CardEditorData (새 가변 구조)."""
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

    from backend.core.models import (
        CardEditorData, CardMeta, CardSlot,
        FieldValue, FieldSource, MatchQuality, RiskLevel, ClaimType,
    )

    def fv(value: str) -> FieldValue:
        return FieldValue(
            value=value,
            confidence="high",
            match_quality=MatchQuality.EXACT,
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
        cards=[
            CardSlot(
                card_num=1,
                template_type="cover",
                fields={
                    "title": fv("셀룰로오스 기반\n친환경 마이크로비드"),
                    "subtitle": fv("마이크로플라스틱을 대체하는 생분해성 소재"),
                    "edition": fv("WIT Series Vol.80"),
                },
            ),
            CardSlot(
                card_num=2,
                template_type="closing",
                fields={
                    "title_white": fv("친환경 소재 연구,"),
                    "title_accent": fv("함께 만듭니다"),
                    "body": fv("한국생산기술연구원은 마이크로플라스틱 대체 소재 상용화를 위해 산업계와 협력하고 있습니다."),
                },
            ),
        ],
    )
