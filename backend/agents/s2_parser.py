from __future__ import annotations

import json
import logging
import re

from .base import BaseAgent
from ..core.llm_client import llm_client
from ..core.models import S2Input, S2Output

logger = logging.getLogger(__name__)

# 영문 + 한국어 섹션 헤더 패턴
_SECTION_PATTERNS = re.compile(
    r"^(?P<title>"
    r"Abstract|Introduction|Background|Related Work|"
    r"Method(?:ology|s)?|Experiment(?:al)?(?:\s+Setup)?|"
    r"Result(?:s)?(?:\s+and\s+Discussion)?|Discussion|"
    r"Conclusion(?:s)?|References|Acknowledgement?s?|"
    r"초록|서론|배경|관련\s*연구|방법론?|실험|결과|논의|결론|참고\s*문헌"
    r")[\s\n:：]*$",
    re.IGNORECASE | re.MULTILINE,
)

_LLM_SYSTEM = """당신은 학술 논문의 섹션 구조를 파악하는 전문가입니다.
주어진 논문 텍스트를 아래 섹션으로 분리하여 JSON으로 반환하세요.
반환 형식: {"Abstract": "...", "Introduction": "...", "Methods": "...", "Results": "...", "Conclusion": "..."}
없는 섹션은 빈 문자열로 남기세요. JSON만 반환하고 다른 설명은 하지 마세요."""

_LLM_USER = """다음 논문 텍스트를 섹션별로 분리하세요:

{text}"""


class S2ParserAgent(BaseAgent[S2Input, S2Output]):
    """S2: raw_text → section_map (regex 우선, LLM 폴백)."""

    async def execute(self, input_data: S2Input) -> S2Output:
        warnings: list[str] = []

        # ── 1차: regex ─────────────────────────────────────────────────────────
        section_map = self._regex_split(input_data.raw_text)

        if len([v for v in section_map.values() if v.strip()]) >= 3:
            logger.info("S2: regex split succeeded (%d sections)", len(section_map))
            return S2Output(section_map=section_map, degraded_mode=False, warnings=warnings)

        # ── 2차: LLM 폴백 ──────────────────────────────────────────────────────
        logger.warning("S2: regex insufficient, trying LLM fallback")
        warnings.append("S2: regex failed, LLM fallback used")

        # 텍스트가 너무 길면 앞 6000자만 사용 (토큰 절약)
        text_snippet = input_data.raw_text[:6000]
        try:
            raw = await llm_client.call(
                system_prompt=_LLM_SYSTEM,
                user_prompt=_LLM_USER.format(text=text_snippet),
                max_tokens=2048,
                temperature=0.1,
            )
            section_map = json.loads(self._extract_json(raw))
            logger.info("S2: LLM fallback succeeded")
            return S2Output(section_map=section_map, degraded_mode=False, warnings=warnings)
        except Exception as exc:
            logger.error("S2: LLM fallback failed — %s", exc)
            warnings.append(f"ERR-S2-001: {exc}")

        # ── degraded: 전체를 single section으로 ─────────────────────────────
        return S2Output(
            section_map={"full_text": input_data.raw_text},
            degraded_mode=True,
            warnings=warnings,
        )

    def _regex_split(self, text: str) -> dict[str, str]:
        """섹션 헤더로 텍스트를 분할."""
        matches = list(_SECTION_PATTERNS.finditer(text))
        if not matches:
            return {}

        section_map: dict[str, str] = {}
        for i, m in enumerate(matches):
            title = m.group("title").strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_map[title] = text[start:end].strip()
        return section_map

    @staticmethod
    def _extract_json(text: str) -> str:
        """LLM 응답에서 JSON 블록만 추출."""
        # ```json ... ``` 블록 우선
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
        # 그냥 { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return m.group(0)
        return text


s2_agent = S2ParserAgent()
