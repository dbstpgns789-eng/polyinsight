"""논문이해팀 Understand — raw section_map → PaperDigest(내용모양 인벤토리). (Haiku)

다이제스트는 힌트일 뿐(권위는 raw). Architect 입력 압축 + 레이아웃/grounding 재료 구조화.
"""
from __future__ import annotations
import json
import logging

from ...core.llm_client import llm_client
from ...core.models import PaperDigest, UnderstandInput
from ._util import extract_json, format_section_map
from . import prompts

logger = logging.getLogger(__name__)


class Understand:
    """UnderstandInput → PaperDigest. 코디네이터가 호출한다."""

    async def run(self, inp: UnderstandInput) -> PaperDigest:
        meta = inp.paper_metadata
        user = prompts.UNDERSTAND_USER.format(
            section_map_text=format_section_map(inp.section_map),
            title=meta.title or "unknown",
            authors=", ".join(meta.authors) if meta.authors else "unknown",
            year=meta.year or "unknown",
        )
        raw = await llm_client.call(
            system_prompt=prompts.UNDERSTAND_SYSTEM,
            user_prompt=user,
            max_tokens=4000,
            temperature=0.1,
            timeout_s=120,
        )
        parsed = json.loads(extract_json(raw))
        return PaperDigest.model_validate(parsed)


understand = Understand()
