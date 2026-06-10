from __future__ import annotations

import asyncio
import logging

from .base import BaseAgent
from .s6._util import extract_json, format_section_map
from .s6.architect import architect
from .s6.writer import writer
from .s6.mock import mock_storyboard, mock_cards
from ..core.config import settings
from ..core.llm_client import LLMTruncationError
from ..core.models import (
    ArchitectInput, ArchitectOutput, WriterInput, WriterOutput,
    CardEditorData, FieldValue,
    MatchQuality, RiskLevel, ClaimType,
    Storyboard,
    S6Input, S6Output,
    THEME_PRESETS,
)

logger = logging.getLogger(__name__)

# 프롬프트는 s6/prompts.py 로 분할 이관됨(설계팀/콘텐츠팀). 아래는 mock + 코디네이터.

# ---------------------------------------------------------------------------
# Mock (DEV_MOCK_LLM) + Agent
# ---------------------------------------------------------------------------

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
            logger.info("S6: DEV_MOCK_LLM=True — mock 설계팀/콘텐츠팀으로 동형 경로 실행")
            arch_out = mock_storyboard(input_data.card_count, input_data.paper_metadata)
            wr_out = mock_cards(arch_out.storyboard, input_data.paper_metadata)
            card_data = self._assemble(arch_out, wr_out)
            card_data = self._post_process(card_data)
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
