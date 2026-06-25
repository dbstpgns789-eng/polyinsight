"""S6 모듈 공유 유틸 — Architect/Writer/코디네이터가 함께 쓰는 순수 함수."""
from __future__ import annotations

import contextlib
import logging
import re

logger = logging.getLogger(__name__)

SECTION_MAX_CHARS = 50000
RAW_LOG_CHARS = 3000


@contextlib.contextmanager
def log_raw_on_parse_error(stage: str, raw: str):
    """파싱/검증 실패 시 LLM 원본 응답을 로그에 남기고 재-raise.

    결정론적 실패는 fail-fast(재시도 안 함)라 raw가 사라지면 재현이 불가능하다.
    실제 논문을 돌려야만 드러나는 에러(예: 모델이 못 채운 필드를 어떻게 인코딩하는지)를
    다음 디버깅에서 확인하려면 원본이 반드시 필요하다 — 앞 RAW_LOG_CHARS자를 남긴다.
    """
    try:
        yield
    except Exception as exc:
        logger.error(
            "S6 %s 파싱/검증 실패 (%s) — raw 응답[:%d]:\n%s",
            stage, type(exc).__name__, RAW_LOG_CHARS, (raw or "")[:RAW_LOG_CHARS],
        )
        raise


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


def format_digest(digest) -> str:
    """PaperDigest를 프롬프트용 '내용모양 인벤토리' 텍스트로 직렬화. 빈 섹션은 생략."""
    def _src(s):
        return f"[{s.section} p{s.page}]" if s and s.section else ""

    parts: list[str] = [f"한 줄 요약: {digest.one_liner}"]
    if digest.numbers:
        lines = [f"- {n.label or '값'}: {n.value}{n.unit} ({n.context}) {_src(n.source)}"
                 for n in digest.numbers]
        parts.append("핵심 수치:\n" + "\n".join(lines))
    if digest.comparisons:
        lines = [f"- {c.attribute}: " + " vs ".join(f"{i}={v}" for i, v in zip(c.items, c.values))
                 + f" {_src(c.source)}" for c in digest.comparisons]
        parts.append("비교쌍:\n" + "\n".join(lines))
    if digest.terms:
        parts.append("전문용어:\n" + "\n".join(f"- {t.term}: {t.plain}" for t in digest.terms))
    if digest.figures:
        parts.append("그림:\n" + "\n".join(f"- {f.ref}: {f.shows}" for f in digest.figures))
    if digest.process_steps:
        parts.append("공정 단계:\n" + "\n".join(f"- {s}" for s in digest.process_steps))
    if digest.claims:
        parts.append("역할별 핵심 주장:\n" + "\n".join(
            f"- [{c.role}] {c.text} {_src(c.source)}" for c in digest.claims))
    return "\n\n".join(parts)
