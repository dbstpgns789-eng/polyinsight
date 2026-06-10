"""설계팀 Architect — section_map을 읽어 Storyboard(레이아웃 결정)만 만든다. (Sonnet)

레이아웃 뇌(prompts.SEQUENCING_RULES)가 여기 격리된다. 본문 fields는 만들지 않는다.
"""
from __future__ import annotations

import json
import logging

from ...core.config import settings
from ...core.llm_client import llm_client
from ...core.models import (
    ArchitectInput, ArchitectOutput, CardStorybeat, Storyboard,
    THEME_PRESETS, VALID_TEMPLATE_TYPES,
)
from ._util import extract_json, format_section_map
from . import prompts

logger = logging.getLogger(__name__)


class Architect:
    """ArchitectInput → ArchitectOutput. 코디네이터가 호출한다."""

    async def run(self, inp: ArchitectInput) -> ArchitectOutput:
        meta = inp.paper_metadata
        user = prompts.ARCHITECT_USER.format(
            section_map_text=format_section_map(inp.section_map),
            title=meta.title or "unknown",
            authors=", ".join(meta.authors) if meta.authors else "unknown",
            year=meta.year or "unknown",
            template_purposes=prompts.TEMPLATE_PURPOSES,
            sequencing_rules=prompts.SEQUENCING_RULES,
            theme_rules=prompts.THEME_RULES,
            card_count=inp.card_count,
        )
        if inp.revise_beats:
            user += prompts.ARCHITECT_REVISE_SUFFIX.format(
                current_storyboard=_storyboard_brief(inp.current_storyboard),
                revise_list="\n".join(
                    f"- 카드{s.card_num}: {s.reason} → 제안 {s.suggested_shape}"
                    for s in inp.revise_beats
                ),
            )

        raw = await llm_client.call(
            system_prompt=prompts.ARCHITECT_SYSTEM,
            user_prompt=user,
            max_tokens=4000,            # 스토리보드만 — 작음
            temperature=0.2,
            timeout_s=120,
            model=settings.LLM_MODEL_ARCHITECT,
        )
        parsed = json.loads(extract_json(raw))
        storyboard = _parse_storyboard(parsed)

        # 피드백 루프: 지목된 비트만 바뀌도록 방어적 복원(나머지는 원본 유지).
        if inp.revise_beats and inp.current_storyboard:
            storyboard = _restore_untargeted(
                storyboard, inp.current_storyboard,
                targeted={s.card_num for s in inp.revise_beats},
            )

        raw_theme = parsed.get("recommended_theme", "tech_blue")
        theme = raw_theme if raw_theme in THEME_PRESETS else "tech_blue"
        return ArchitectOutput(storyboard=storyboard, recommended_theme=theme)


def _parse_storyboard(parsed: dict) -> Storyboard:
    raw_sb = parsed.get("storyboard") or {}
    beats = [CardStorybeat.model_validate(b) for b in raw_sb.get("beats", [])]
    if not beats:
        raise ValueError("Architect: storyboard.beats 비어 있음")

    for b in beats:
        if b.template_type not in VALID_TEMPLATE_TYPES:
            raise ValueError(f"Architect: 알 수 없는 template_type '{b.template_type}'")

    # 첫=cover_v2, 끝=closing_v2 강제 교정(설계상 고정).
    beats[0].template_type = "cover_v2"
    beats[-1].template_type = "closing_v2"
    return Storyboard(story_arc=raw_sb.get("story_arc", ""), beats=beats)


def _restore_untargeted(revised: Storyboard, original: Storyboard, targeted: set[int]) -> Storyboard:
    """지목되지 않은 비트는 원본 그대로 — 모델이 다른 비트를 흔들어도 무시."""
    by_num = {b.card_num: b for b in revised.beats}
    merged: list[CardStorybeat] = []
    for orig in original.beats:
        if orig.card_num in targeted and orig.card_num in by_num:
            merged.append(by_num[orig.card_num])
        else:
            merged.append(orig)
    return Storyboard(story_arc=original.story_arc, beats=merged)


def _storyboard_brief(sb: Storyboard | None) -> str:
    if not sb:
        return "(없음)"
    return "\n".join(
        f"- 카드{b.card_num} [{b.template_type}] {b.key_message}" for b in sb.beats
    )


architect = Architect()
