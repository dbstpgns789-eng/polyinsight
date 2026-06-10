from __future__ import annotations

import asyncio
import logging

from .base import BaseAgent
from .s6._util import extract_json, format_section_map
from .s6.architect import architect
from .s6.writer import writer
from ..core.config import settings
from ..core.llm_client import LLMTruncationError
from ..core.models import (
    ArchitectInput, ArchitectOutput, WriterInput, WriterOutput,
    CardEditorData, CardMeta, CardSlot, FieldValue,
    MatchQuality, RiskLevel, ClaimType, FieldSource,
    CardStorybeat, Storyboard,
    S6Input, S6Output,
    THEME_PRESETS,
)

logger = logging.getLogger(__name__)

# 프롬프트는 s6/prompts.py 로 분할 이관됨(설계팀/콘텐츠팀). 아래는 mock + 코디네이터.

# ---------------------------------------------------------------------------
# Mock (DEV_MOCK_LLM) + Agent
# ---------------------------------------------------------------------------

def _make_fv(
    value: str,
    *,
    section: str = "abstract",
    page: int = 1,
    risk: str = "LOW",
    quality: str = "exact",
    claim: str = "qualitative",
    confidence: str = "high",
) -> FieldValue:
    return FieldValue(
        value=value,
        confidence=confidence,       # type: ignore[arg-type]
        match_quality=MatchQuality(quality),
        claim_type=ClaimType(claim),
        source=FieldSource(section=section, page=page),
        risk_level=RiskLevel(risk),
    )


# card_count → 대표 시퀀스 (mock 결정적; 실제 LLM은 AI가 storyboard로 선택).
# 아크 정합: 첫=cover_v2, 끝=closing_v2, bigstat_compare 포함.
_MOCK_SEQUENCES: dict[int, list[str]] = {
    3: ["cover_v2", "bigstat_compare", "closing_v2"],
    4: ["cover_v2", "feature", "bigstat_compare", "closing_v2"],
    5: ["cover_v2", "statement", "feature", "bigstat_compare", "closing_v2"],
    6: ["cover_v2", "statement", "feature", "bigstat_compare", "grid_v2", "closing_v2"],
    7: ["cover_v2", "statement", "feature", "process_v2", "bigstat_compare", "grid_v2", "closing_v2"],
}


def _mock_sequence(card_count: int) -> list[str]:
    if card_count in _MOCK_SEQUENCES:
        return _MOCK_SEQUENCES[card_count]
    base = _MOCK_SEQUENCES[7]
    if card_count < 3:
        return _MOCK_SEQUENCES[3]
    if card_count <= 7:
        mid = base[1:-1][: card_count - 2]
        return ["cover_v2", *mid, "closing_v2"]
    return base

_MOCK_FIELDS: dict[str, dict[str, FieldValue]] = {
    "cover_v2": {
        "eyebrow":  _make_fv("KITECH Research Note · 2026", quality="normalized"),
        "headline": _make_fv("플라스틱을 *대체*하는 셀룰로스 미세구슬"),
        "subtitle": _make_fv("COF 복합화로 강도와 생분해성을 동시에", section="abstract", page=1),
        "org":      _make_fv("KITECH 친환경소재연구부문"),
    },
    "statement": {
        "eyebrow":  _make_fv("문제 제기"),
        "headline": _make_fv("왜 친환경 플라스틱은 *약할*까?", section="introduction", page=2),
        "body":     _make_fv(
            "생분해성 소재는 대개 강도가 낮아 구조재로 쓰기 어렵다. 이 한계가 상용화를 막아 왔다.",
            section="introduction", page=2, confidence="medium",
        ),
    },
    "feature": {
        "eyebrow":  _make_fv("핵심 혁신"),
        "headline": _make_fv("셀룰로스에 *COF*를 짜 넣다", section="methods", page=4),
        "body":     _make_fv(
            "공유결합 유기골격체(COF)를 셀룰로스 매트릭스에 복합해, 미세구슬 형태로 강도와 다공성을 함께 얻었다.",
            section="methods", page=4,
        ),
    },
    "process_v2": {
        "eyebrow":  _make_fv("제작 방법"),
        "headline": _make_fv("세 단계로 만든다", section="methods", page=5),
        "steps":    _make_fv(
            "셀룰로스 용액에 COF 전구체 분산|에멀전법으로 미세구슬 성형|동결건조로 다공 구조 고정",
            section="methods", page=5,
        ),
        "caption":  _make_fv("전 과정 무용매·저온 — 친환경 공정", confidence="medium"),
    },
    "bigstat_compare": {
        "eyebrow":      _make_fv("성능 검증"),
        "headline":     _make_fv("기존 플라스틱보다 *더 단단*하다"),
        "stat_value":   _make_fv("238", section="results", page=7,
                                 quality="exact", claim="quantitative"),
        "stat_unit":    _make_fv("MPa"),
        "stat_caption": _make_fv("셀룰로스–COF 복합 미세구슬의 압축 강도", section="results", page=7),
        "bars":         _make_fv(
            "우리 복합 구슬:238:1|폴리프로필렌(PP):199:0|무보강 셀룰로스:142:0",
            section="results", page=7, quality="exact", claim="quantitative",
        ),
        "source_ref":   _make_fv("출처: Cellulose (2024) · Results", section="results", page=7),
    },
    "reasons": {
        "eyebrow":  _make_fv("왜 이 소재인가"),
        "headline": _make_fv("셀룰로스를 고른 *세 가지* 이유"),
        "reasons":  _make_fv(
            "풍부함:지구상 가장 많은 천연 고분자, 원료 걱정이 없다"
            "|생분해성:토양·해양에서 완전 분해된다"
            "|기능화 용이:표면 -OH로 COF 결합이 쉽다",
            section="introduction", page=3,
        ),
    },
    "grid_v2": {
        "eyebrow":  _make_fv("응용 분야"),
        "headline": _make_fv("어디에 *쓰일까*?"),
        "items":    _make_fv(
            "포장재:일회용 플라스틱 대체|흡착소재:중금속·염료 제거"
            "|약물전달:다공성 캡슐|단열재:경량 구조재",
            section="discussion", page=10,
        ),
        "body":     _make_fv("강도·다공성·생분해성의 조합이 응용 폭을 넓힌다.", confidence="medium"),
    },
    "closing_v2": {
        "eyebrow":    _make_fv("맺음말"),
        "headline":   _make_fv("다음은 *대량 생산* 검증", section="conclusion", page=12),
        "body":       _make_fv(
            "실험실 성과를 파일럿 규모로 확장해 경제성과 균일도를 확인하는 후속 연구를 진행한다.",
            section="conclusion", page=12,
        ),
        "source_ref": _make_fv("출처: Cellulose (2024) · Conclusion", section="conclusion", page=12),
    },
}


def _build_mock_card_data(
    card_count: int,
    section_map: dict[str, str],
    paper_metadata,
) -> CardEditorData:
    """DEV_MOCK_LLM 모드용 — 신규 8뼈대 결정적 시퀀스."""
    title = getattr(paper_metadata, "title", "") or "연구 성과"
    authors = getattr(paper_metadata, "authors", []) or []
    year = getattr(paper_metadata, "year", 2024) or 2024
    fv = _make_fv

    meta = CardMeta(
        org=fv("한국생산기술연구원"),
        dept=fv("친환경소재연구부문"),
        researcher=fv(authors[0] if authors else "연구팀"),
        month=fv(f"{year}-01", quality="normalized"),
        edition_number=fv(f"{year}-01호", quality="normalized"),
    )

    sequence = _mock_sequence(card_count)

    cards = [
        CardSlot(
            card_num=i + 1,
            template_type=tmpl,
            fields=_MOCK_FIELDS.get(tmpl, {"headline": fv(title)}),
        )
        for i, tmpl in enumerate(sequence)
    ]

    _ROLE_MAP = {
        "cover_v2": "논문 주제 표지",
        "statement": "문제 제기 / 기존 한계",
        "feature": "핵심 혁신 소개",
        "process_v2": "제작 방법 단계",
        "bigstat_compare": "핵심 성능 + 기존 대비 + 출처",
        "reasons": "왜 이 소재인가",
        "grid_v2": "응용 분야",
        "closing_v2": "마무리 / 협력",
    }
    storyboard = Storyboard(
        story_arc=f"{title}의 배경·혁신·성능·응용을 {len(cards)}장으로 구성",
        beats=[
            CardStorybeat(
                card_num=i + 1,
                template_type=tmpl,
                narrative_role=_ROLE_MAP.get(tmpl, "내용 전달"),
                key_message=_MOCK_FIELDS.get(tmpl, {}).get(
                    "headline", fv(title)
                ).value,
            )
            for i, tmpl in enumerate(sequence)
        ],
    )

    return CardEditorData(
        storyboard=storyboard, meta=meta, cards=cards,
        theme=THEME_PRESETS["forest_green"],
        recommended_theme_key="forest_green",
    )


class S6CardJsonAgent(BaseAgent[S6Input, S6Output]):
    """S6: section_map + card_count → CardEditorData (가변 CardSlot 리스트)."""

    MAX_RETRIES = 5
    SECTION_MAX_CHARS = 50000
    # 503 서버 과부하 시 대기 시간 (초): 1차 30s, 2차 60s, 3차 120s ...
    _503_BACKOFF = [30, 60, 120, 180]
    # 발행급 밀도 상한 (docs/21 A4) — 측정용 경고 임계값. 고정 논문 시각 튜닝으로 조정 가능.
    DENSITY_CAPS = {"headline": 30, "subtitle": 45, "body": 90}

    async def execute(self, input_data: S6Input) -> S6Output:
        if settings.DEV_MOCK_LLM:
            logger.info("S6: DEV_MOCK_LLM=True — LLM 호출 건너뜀, mock 데이터 반환")
            card_data = _build_mock_card_data(
                input_data.card_count,
                input_data.section_map,
                input_data.paper_metadata,
            )
            return S6Output(
                card_data=card_data,
                critical_count=self._count_risk(card_data, RiskLevel.CRITICAL),
                high_count=self._count_risk(card_data, RiskLevel.HIGH),
            )

        # ── 멀티에이전트: 설계팀(Architect, Sonnet) → 콘텐츠팀(Writer, Haiku) ──
        arch_out: ArchitectOutput = await self._with_retries(
            lambda: architect.run(ArchitectInput(
                section_map=input_data.section_map,
                paper_metadata=input_data.paper_metadata,
                card_count=input_data.card_count,
            )),
            stage="Architect", truncation_is_card_overload=False,
        )

        wr_out: WriterOutput = await self._with_retries(
            lambda: self._run_writer(input_data, arch_out.storyboard),
            stage="Writer", truncation_is_card_overload=True,
            card_count=input_data.card_count,
        )

        card_data = self._assemble(arch_out, wr_out)
        card_data = self._post_process(card_data)
        critical = self._count_risk(card_data, RiskLevel.CRITICAL)
        high = self._count_risk(card_data, RiskLevel.HIGH)
        density_warns = self._density_warnings(card_data)
        if density_warns:
            logger.warning("S6 발행급 밀도 경고(docs/21): %s", "; ".join(density_warns))
        logger.info(
            "S6: done. cards=%d CRITICAL=%d HIGH=%d",
            len(card_data.cards), critical, high,
        )
        return S6Output(card_data=card_data, critical_count=critical, high_count=high)

    # ── 모듈 호출 래퍼 ────────────────────────────────────────────────────────

    async def _run_writer(self, input_data: S6Input, storyboard: Storyboard) -> WriterOutput:
        """Writer 실행 + 스토리보드 커버리지 일관성 검증(불일치 시 재시도 유발)."""
        wr = await writer.run(WriterInput(
            section_map=input_data.section_map,
            paper_metadata=input_data.paper_metadata,
            storyboard=storyboard,
        ))
        beat_nums = {b.card_num for b in storyboard.beats}
        card_nums = {c.card_num for c in wr.cards}
        if card_nums != beat_nums:
            raise ValueError(
                f"Writer 커버리지 불일치: beats={sorted(beat_nums)} cards={sorted(card_nums)}"
            )
        return wr

    async def _with_retries(
        self, factory, *, stage: str,
        truncation_is_card_overload: bool, card_count: int = 0,
    ):
        """각 모듈 호출을 개별 래핑 — Writer 503이 비싼 Architect를 재실행하지 않게."""
        last_exc: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await factory()
            except LLMTruncationError as exc:
                if truncation_is_card_overload:
                    # Writer(Haiku) 출력 천장 = 카드 과다. 재시도 무의미.
                    logger.error(
                        "S6 %s: 출력 천장 (out=%d/max=%d) — card_count=%d 과다",
                        stage, exc.output_tokens, exc.max_tokens, card_count,
                    )
                    raise RuntimeError(
                        f"ERR-S6-002: 카드 {card_count}장이 모델 출력 한계"
                        f"({exc.max_tokens} 토큰)를 초과해 JSON이 잘렸습니다. "
                        f"카드 수를 줄이거나 더 큰 출력 모델이 필요합니다."
                    ) from exc
                # Architect 출력 천장 = 프롬프트 버그(작은 출력인데 잘림). 카드 수 문제 아님.
                logger.error(
                    "S6 %s: 출력 천장 — 프롬프트 점검 필요 (out=%d/max=%d)",
                    stage, exc.output_tokens, exc.max_tokens,
                )
                raise RuntimeError(
                    f"ERR-S6-003: {stage} 출력이 천장에서 잘림 — 프롬프트 점검 필요."
                ) from exc
            except Exception as exc:
                last_exc = exc
                logger.warning("S6 %s: attempt %d failed — %s", stage, attempt + 1, exc)
                if "503" in str(exc) and attempt < self.MAX_RETRIES - 1:
                    wait = self._503_BACKOFF[min(attempt, len(self._503_BACKOFF) - 1)]
                    logger.info("S6 %s: 503 서버 과부하 — %ds 대기 후 재시도", stage, wait)
                    await asyncio.sleep(wait)

        raise RuntimeError(f"ERR-S6-001: {last_exc}")

    # ── 조립 ──────────────────────────────────────────────────────────────────

    def _assemble(self, arch_out: ArchitectOutput, wr_out: WriterOutput) -> CardEditorData:
        """설계팀 storyboard·theme + 콘텐츠팀 cards·meta → CardEditorData."""
        theme_key = (
            arch_out.recommended_theme
            if arch_out.recommended_theme in THEME_PRESETS else "tech_blue"
        )
        return CardEditorData(
            storyboard=arch_out.storyboard,
            meta=wr_out.meta,
            cards=wr_out.cards,
            theme=THEME_PRESETS[theme_key],
            recommended_theme_key=theme_key,
        )

    # ── 후처리 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _post_process(card_data: CardEditorData) -> CardEditorData:
        """verified 강제 False + risk_level 규칙 재판정."""
        for fv in _iter_field_values(card_data):
            fv.verified = False
            # 위험 신호는 수치(정량)가 진다. 정성/인과 의역은 MEDIUM 상한.
            is_quant = fv.claim_type == ClaimType.QUANTITATIVE
            mq = fv.match_quality
            if is_quant and mq == MatchQuality.FAILED:
                fv.risk_level = RiskLevel.CRITICAL
            elif is_quant and mq in (MatchQuality.FUZZY, MatchQuality.SEMANTIC):
                fv.risk_level = RiskLevel.HIGH
            elif is_quant and mq == MatchQuality.NORMALIZED:
                fv.risk_level = RiskLevel.MEDIUM
            elif mq in (MatchQuality.FAILED, MatchQuality.FUZZY, MatchQuality.SEMANTIC):
                # 정성/인과: 의역·미매칭은 검토 권장(MEDIUM)이지 위험(HIGH) 아님
                fv.risk_level = RiskLevel.MEDIUM
            else:
                fv.risk_level = RiskLevel.LOW
        return card_data

    # ── 발행급 밀도 측정 (docs/21) ────────────────────────────────────────────

    @staticmethod
    def _density_warnings(card_data: CardEditorData) -> list[str]:
        """발행급 bar(docs/21 A1 슬라이드수·A4 글자수) 측정 — 위반을 경고로 수집한다.
        하드 실패·자동 절단은 하지 않는다(의미·fidelity 훼손 방지). 프롬프트가 1차 강제, 이건 측정/관측."""
        warns: list[str] = []
        n = len(card_data.cards)
        if not (5 <= n <= 7):
            warns.append(f"슬라이드 수 {n}장(권장 5~7)")
        for card in card_data.cards:
            for key, cap in S6CardJsonAgent.DENSITY_CAPS.items():
                fv = card.fields.get(key)
                if fv and fv.value:
                    text = fv.value.replace("*", "")  # 강조 마커 제외
                    if len(text) > cap:
                        warns.append(f"카드{card.card_num} {key} {len(text)}자(상한 {cap})")
        return warns

    @staticmethod
    def _count_risk(card_data: CardEditorData, level: RiskLevel) -> int:
        return sum(1 for fv in _iter_field_values(card_data) if fv.risk_level == level)

    # ── 텍스트 헬퍼 ───────────────────────────────────────────────────────────

    def _format_section_map(self, section_map: dict[str, str]) -> str:
        return format_section_map(section_map, self.SECTION_MAX_CHARS)

    @staticmethod
    def _extract_json(text: str) -> str:
        return extract_json(text)


def _iter_field_values(card_data: CardEditorData):
    """CardEditorData의 모든 FieldValue를 순회."""
    for fv in vars(card_data.meta).values():
        if isinstance(fv, FieldValue):
            yield fv
    for slot in card_data.cards:
        yield from slot.fields.values()


s6_agent = S6CardJsonAgent()
