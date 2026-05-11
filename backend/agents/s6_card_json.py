from __future__ import annotations

import json
import logging
import re

from .base import BaseAgent
from ..core.llm_client import llm_client
from ..core.models import (
    CardEditorData, CardTheme, FieldValue, MatchQuality,
    RiskLevel, ClaimType, FieldSource,
    S6Input, S6Output,
)

logger = logging.getLogger(__name__)

# ── 프롬프트 ──────────────────────────────────────────────────────────────────

_SYSTEM = """당신은 학술 논문을 기관 홍보용 카드뉴스로 변환하는 전문가입니다.

핵심 원칙:
1. 아래 section_map(원문)에서만 사실을 추출한다.
2. 수치(숫자, %, 배율)는 반드시 원문에서 찾아야 한다.
3. 원문에 없는 내용은 절대 만들지 않는다.
4. 찾을 수 없으면 value=""로 남기고 match_quality="failed"로 표기한다.
5. verified는 항상 false다.

반환: JSON만. 설명 없음."""

_USER = """## 논문 원문

{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}

---
## 지시

아래 JSON 스키마를 완성하라. <각 FieldValue>는 규칙에 따라 채운다.

FieldValue 구조:
{{
  "value": "텍스트",
  "confidence": "high|medium|low",
  "match_quality": "exact|normalized|fuzzy|semantic|failed",
  "claim_type": "quantitative|qualitative|causal",
  "source": {{"section": "섹션명", "page": 1}},
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "verified": false
}}

risk_level 규칙:
- quantitative + failed → CRITICAL
- fuzzy 또는 semantic  → HIGH
- normalized           → MEDIUM
- exact 또는 qualitative → LOW

출력 JSON:
{{
  "meta": {{
    "org":            <FieldValue>,
    "dept":           <FieldValue>,
    "researcher":     <FieldValue>,
    "month":          <FieldValue>,
    "edition_number": <FieldValue>
  }},
  "card1": {{
    "pretitle":      <FieldValue>,
    "title":         <FieldValue>,
    "mascot_bubble": <FieldValue>
  }},
  "card2": {{
    "intro":        <FieldValue>,
    "keyword_line": <FieldValue>,
    "footnote":     <FieldValue>
  }},
  "card3": {{
    "problem":       <FieldValue>,
    "achievement":   <FieldValue>,
    "mascot_bubble": <FieldValue>,
    "photo_caption": <FieldValue>
  }},
  "card4": {{
    "before_label":  <FieldValue>,
    "after_label":   <FieldValue>,
    "description":   <FieldValue>,
    "result":        <FieldValue>,
    "mascot_bubble": <FieldValue>
  }},
  "card5": {{
    "pre_title":  <FieldValue>,
    "main_title": <FieldValue>,
    "cta":        <FieldValue>,
    "team_name":  <FieldValue>
  }},
  "layout_variants": {{"1":"A","2":"B","3":"B","4":"D","5":"A"}}
}}"""


class S6CardJsonAgent(BaseAgent[S6Input, S6Output]):
    """S6: section_map → CardEditorData (FieldValue 스키마)."""

    MAX_RETRIES = 3
    SECTION_MAX_CHARS = 12000   # 토큰 절약: 섹션 합산 최대 길이

    async def execute(self, input_data: S6Input) -> S6Output:
        section_map_text = self._format_section_map(input_data.section_map)
        meta = input_data.paper_metadata

        user_prompt = _USER.format(
            section_map_text=section_map_text,
            title=meta.title or "unknown",
            authors=", ".join(meta.authors) if meta.authors else "unknown",
            year=meta.year or "unknown",
        )

        last_exc: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                raw = await llm_client.call(
                    system_prompt=_SYSTEM,
                    user_prompt=user_prompt,
                    max_tokens=4096,
                    temperature=0.2,
                )
                card_data = CardEditorData.model_validate(
                    json.loads(self._extract_json(raw))
                )
                # 후처리: verified 강제 초기화 + risk_level 재판정
                card_data = self._post_process(card_data)
                critical = self._count_risk(card_data, RiskLevel.CRITICAL)
                high = self._count_risk(card_data, RiskLevel.HIGH)
                logger.info("S6: done. CRITICAL=%d HIGH=%d", critical, high)
                return S6Output(
                    card_data=card_data,
                    critical_count=critical,
                    high_count=high,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning("S6: attempt %d failed — %s", attempt + 1, exc)

        raise RuntimeError(f"ERR-S6-001: {last_exc}")

    # ── 헬퍼 ──────────────────────────────────────────────────────────────────

    def _format_section_map(self, section_map: dict[str, str]) -> str:
        parts = []
        total = 0
        for section, text in section_map.items():
            chunk = f"### {section}\n{text}"
            if total + len(chunk) > self.SECTION_MAX_CHARS:
                remaining = self.SECTION_MAX_CHARS - total
                if remaining > 200:
                    parts.append(chunk[:remaining] + "\n[truncated]")
                break
            parts.append(chunk)
            total += len(chunk)
        return "\n\n".join(parts)

    @staticmethod
    def _extract_json(text: str) -> str:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return m.group(0)
        return text

    @staticmethod
    def _post_process(card_data: CardEditorData) -> CardEditorData:
        """verified 강제 False + risk_level 규칙 재판정."""
        for field_value in _iter_field_values(card_data):
            field_value.verified = False
            # risk_level 재판정 (LLM이 잘못 넣었을 경우 교정)
            if (field_value.claim_type == ClaimType.QUANTITATIVE
                    and field_value.match_quality == MatchQuality.FAILED):
                field_value.risk_level = RiskLevel.CRITICAL
            elif field_value.match_quality in (MatchQuality.FUZZY, MatchQuality.SEMANTIC):
                field_value.risk_level = RiskLevel.HIGH
            elif field_value.match_quality == MatchQuality.NORMALIZED:
                field_value.risk_level = RiskLevel.MEDIUM
            else:
                field_value.risk_level = RiskLevel.LOW
        return card_data

    @staticmethod
    def _count_risk(card_data: CardEditorData, level: RiskLevel) -> int:
        return sum(
            1 for fv in _iter_field_values(card_data) if fv.risk_level == level
        )


def _iter_field_values(card_data: CardEditorData):
    """CardEditorData의 모든 FieldValue를 순회."""
    for group in [card_data.meta, card_data.card1, card_data.card2,
                  card_data.card3, card_data.card4, card_data.card5]:
        for val in vars(group).values():
            if isinstance(val, FieldValue):
                yield val


s6_agent = S6CardJsonAgent()
