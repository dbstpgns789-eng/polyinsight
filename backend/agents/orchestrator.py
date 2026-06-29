from __future__ import annotations

import asyncio
import logging
import time

from ..core import db
from ..core.llm_client import get_usage, start_usage_capture
from ..core.models import (
    CardTheme,
    JobStatus,
    S1Input,
    S6Input,
    S7Input,
    S8Input,
)
from .s1_extractor import s1_agent
from .s6_card_json import s6_agent
from .s7_renderer import s7_agent
from .s8_packaging import s8_agent

logger = logging.getLogger(__name__)

_job_semaphore = asyncio.Semaphore(5)  # settings.MAX_CONCURRENT_JOBS

# 입력 가드레일: S1 추출은 성공했으나 word_count가 이 값 미만이면 S6 호출 없이 즉시 차단.
# 비논문 발췌(0096-0098.pdf=31단어)·스캔본이 빈 카드 7장을 만들어 신뢰를 훼손하는 것을 방지.
# 근거: 정상 논문 ≥800단어, 초록만 있어도 ~150단어. 80 미만은 카드 생성 불가.
# 계약: docs/contracts/04_architecture.md §5-1-1.
_ABORT_WORD_FLOOR = 80


async def run_pipeline(
    job_id: str,
    pdf_bytes: bytes,
    theme: CardTheme | None = None,
    card_count: int = 5,
    user_id: int | None = None,
) -> None:
    """Full S1→S6→S7→S8 pipeline. S8 always runs."""
    if theme is None:
        theme = CardTheme()

    async with _job_semaphore:
        await _execute(job_id, pdf_bytes, theme, card_count, user_id)


async def _log_pipeline_done(
    job_id: str, user_id: int | None, started: float, card_count: int
) -> None:
    """파이프라인 종료 시 최종 상태 + LLM 토큰 사용량을 events에 기록."""
    usage = get_usage() or {}
    final = await db.get_job(job_id)
    try:
        await db.log_event(
            "pipeline_complete",
            user_id=user_id,
            job_id=job_id,
            payload={
                "status": final["status"] if final else None,
                "degraded": bool(final["degraded"]) if final else None,
                "duration_s": round(time.monotonic() - started, 2),
                "card_count": card_count,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "llm_calls": usage.get("calls", 0),
            },
        )
    except Exception:
        logger.exception("pipeline_complete 이벤트 기록 실패")


async def _execute(
    job_id: str,
    pdf_bytes: bytes,
    theme: CardTheme,
    card_count: int = 5,
    user_id: int | None = None,
) -> None:
    start_usage_capture()
    started = time.monotonic()
    warnings: list[str] = []

    # ── S1: PDF extraction ────────────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S1", progress=10)
        s1_out = await s1_agent.execute(S1Input(job_id=job_id, pdf_bytes=pdf_bytes))
        warnings.extend(s1_out.warnings)
        if s1_out.degraded:
            await db.update_job(job_id, status=JobStatus.RUNNING, degraded=True)
        logger.info("S1 done: %d words, %d sections", s1_out.word_count, len(s1_out.section_map))
    except Exception as exc:
        logger.error("S1 fatal: %s", exc)
        await db.update_job(
            job_id,
            status=JobStatus.ERROR,
            stage="S1",
            progress=10,
            warnings=warnings + [f"ERR-S1: {exc}"],
        )
        await _log_pipeline_done(job_id, user_id, started, card_count)
        return

    # ── 입력 가드레일: thin input → S6 호출 없이 조기 차단 (계약 §5-1-1) ──────────
    if s1_out.word_count < _ABORT_WORD_FLOOR:
        msg = (
            f"ABORT-S1: PDF에서 충분한 텍스트를 추출하지 못했습니다 "
            f"({s1_out.word_count}단어). 스캔본이거나 논문이 아닐 수 있습니다."
        )
        logger.warning("S1 thin-input abort: %d words < %d (job %s)",
                       s1_out.word_count, _ABORT_WORD_FLOOR, job_id)
        await db.update_job(
            job_id,
            status=JobStatus.ERROR,
            stage="S1",
            progress=10,
            degraded=True,
            warnings=warnings + [msg],
        )
        await _log_pipeline_done(job_id, user_id, started, card_count)
        return

    # ── S6: Card JSON generation ──────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S6", progress=50)
        s6_out = await s6_agent.execute(
            S6Input(
                job_id=job_id,
                section_map=s1_out.section_map,
                page_map=s1_out.page_map,
                paper_metadata=s1_out.metadata,
                card_count=card_count,
            )
        )
        warnings.extend(s6_out.warnings)
        logger.info("S6 done: CRITICAL=%d HIGH=%d", s6_out.critical_count, s6_out.high_count)
    except Exception as exc:
        logger.error("S6 fatal: %s", exc)
        await db.update_job(
            job_id,
            status=JobStatus.ERROR,
            stage="S6",
            progress=50,
            warnings=warnings + [f"ERR-S6: {exc}"],
        )
        await _log_pipeline_done(job_id, user_id, started, card_count)
        return

    # ── S7: PNG rendering ─────────────────────────────────────────────────────
    # S7은 render 라우트(Next.js)가 DB에서 card_data를 읽어 렌더하므로,
    # S7 호출 전에 반드시 DB에 저장해야 한다. (S8이 나중에 동일 데이터로 덮어씀)
    try:
        await db.save_card_data(job_id, s6_out.card_data.model_dump_json())
    except Exception as exc:
        logger.error("pre-S7 card_data save failed: %s", exc)
        warnings.append(f"WARN-S7: card_data 사전 저장 실패 — {exc}")

    images: list[bytes] = []
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S7", progress=75)
        s7_out = await s7_agent.execute(
            S7Input(job_id=job_id, card_data=s6_out.card_data, theme=theme)
        )
        images = s7_out.images
        warnings.extend(s7_out.warnings)
        logger.info("S7 done: %d images", len(images))
    except Exception as exc:
        logger.error("S7 fatal: %s", exc)
        warnings.append(f"ERR-S7: {exc}")
        # S8 still runs with empty images — sets ERROR internally

    # ── S8: Packaging (always runs) ───────────────────────────────────────────
    await db.update_job(job_id, status=JobStatus.RUNNING, stage="S8", progress=90)
    await s8_agent.execute(
        S8Input(
            job_id=job_id,
            card_data=s6_out.card_data,
            images=images,
            warnings=warnings,
        )
    )

    await _log_pipeline_done(job_id, user_id, started, card_count)
