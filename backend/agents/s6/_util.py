"""S6 모듈 공유 유틸 — Architect/Writer/코디네이터가 함께 쓰는 순수 함수."""
from __future__ import annotations

import re

SECTION_MAX_CHARS = 50000


def format_section_map(section_map: dict[str, str], max_chars: int = SECTION_MAX_CHARS) -> str:
    """section_map을 프롬프트용 텍스트로 직렬화. 길면 max_chars에서 자른다."""
    parts: list[str] = []
    total = 0
    for section, text in section_map.items():
        chunk = f"### {section}\n{text}"
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 200:
                parts.append(chunk[:remaining] + "\n[truncated]")
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n\n".join(parts)


def extract_json(text: str) -> str:
    """LLM 응답에서 JSON 본문만 추출(코드펜스/잡텍스트 제거)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0)
    return text
