"""S6 멀티에이전트 가설 게이트 (Task 6).

설계팀(Architect, Sonnet)이 고정 논문에서 '내용 모양'에 맞는 확장 레이아웃
(multistat/compare_table/definition/quote 등)을 실제로 고르는지 검증한다.
Haiku 모놀리식에서는 0개였다. ≥1개면 "레이아웃 뇌 작동" 가설 통과.

실행:
    python backend/scripts/s6_gate.py
필요: .env의 ANTHROPIC_API_KEY (실제 Sonnet 호출 — 소액 비용).
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

try:                                # Windows 콘솔(cp949)에서 한글·em-dash 출력 보장
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from backend.agents.s6.architect import architect
from backend.core.models import ArchitectInput, PaperMetadata

# 고정 논문 (셀룰로스-COF 복합 미세구슬, 2024)
PAPER_MD = pathlib.Path(
    r"C:\Users\User\Desktop\한국생산기술연구원_근로장학\poly_claude_code\논문"
    r"\80 [cellulose_2024] Fabrication of composite microbeads consisting of cellulose"
    r" and covalent organic nanosheets via electrospray process (1) (2).md"
)

EXTENDED = {"definition", "image_hero", "callout", "multistat", "quote", "compare_table"}


def _section_map() -> dict[str, str]:
    text = PAPER_MD.read_text(encoding="utf-8")

    def _slice(start_kw, end_kw, limit):
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


async def main(card_count: int = 6) -> int:
    inp = ArchitectInput(
        section_map=_section_map(),
        paper_metadata=PaperMetadata(
            title="Fabrication of composite microbeads of cellulose and covalent organic nanosheets",
            authors=["KITECH"], year=2024, doi=None,
        ),
        card_count=card_count,
    )
    t0 = time.time()
    out = await architect.run(inp)
    dt = time.time() - t0

    print(f"\n=== Architect Storyboard (Sonnet, {dt:.1f}s) ===")
    print(f"story_arc: {out.storyboard.story_arc}")
    print(f"theme: {out.recommended_theme}\n")
    used = []
    for b in out.storyboard.beats:
        tag = "  ★확장" if b.template_type in EXTENDED else ""
        used.append(b.template_type)
        print(f"  카드{b.card_num} [{b.template_type}]{tag}")
        print(f"        역할: {b.narrative_role}")
        print(f"        근거: {b.content_shape_reason}")

    ext = [t for t in used if t in EXTENDED]
    print(f"\n확장 레이아웃 {len(ext)}개: {ext}")
    if ext:
        print("✅ 게이트 통과 — 레이아웃 뇌 작동(확장 레이아웃 ≥1).")
        return 0
    print("❌ 게이트 실패 — 확장 레이아웃 0개. 프롬프트/예시 재검토 필요(루프 투자 보류).")
    return 1


async def main_full(card_count: int = 6) -> int:
    """전체 슬라이스 E2E — 설계팀(Sonnet)→콘텐츠팀(Haiku)→조립→루프→검증."""
    from backend.agents.s6_card_json import s6_agent
    from backend.core.models import S6Input

    inp = S6Input(
        job_id="gate-full",
        section_map=_section_map(),
        page_map={1: "p1"},
        paper_metadata=PaperMetadata(
            title="Fabrication of composite microbeads of cellulose and covalent organic nanosheets",
            authors=["KITECH"], year=2024, doi=None,
        ),
        card_count=card_count,
    )
    t0 = time.time()
    out = await s6_agent.execute(inp)
    dt = time.time() - t0
    cd = out.card_data
    print(f"\n=== S6 full E2E ({dt:.1f}s) — cards={len(cd.cards)} CRITICAL={out.critical_count} HIGH={out.high_count} ===")
    print(f"theme: {cd.recommended_theme_key}")
    for c in cd.cards:
        tag = "  ★확장" if c.template_type in EXTENDED else ""
        head = c.fields.get("headline") or c.fields.get("quote")
        print(f"  카드{c.card_num} [{c.template_type}]{tag}  {head.value if head else ''}")
    if out.warnings:
        print("warnings:")
        for w in out.warnings:
            print(f"  - {w}")
    ext = [c.template_type for c in cd.cards if c.template_type in EXTENDED]
    print(f"\n확장 레이아웃 {len(ext)}개: {ext}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        raise SystemExit(asyncio.run(main_full()))
    raise SystemExit(asyncio.run(main()))
