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
