from __future__ import annotations

import asyncio
import logging

from ..core import db
from ..core.models import (
    CardTheme,
    JobStatus,
    S1Input,
    S2Input,
    S6Input,
    S7Input,
    S8Input,
)
from .s1_extractor import s1_agent
from .s2_parser import s2_agent
from .s6_card_json import s6_agent
from .s7_renderer import s7_agent
from .s8_packaging import s8_agent

logger = logging.getLogger(__name__)

_job_semaphore = asyncio.Semaphore(5)  # settings.MAX_CONCURRENT_JOBS


async def run_pipeline(
    job_id: str,
    pdf_bytes: bytes,
    theme: CardTheme | None = None,
) -> None:
    """Full S1→S2→S6→S7→S8 pipeline. S8 always runs."""
    if theme is None:
        theme = CardTheme()

    async with _job_semaphore:
        await _execute(job_id, pdf_bytes, theme)


async def _execute(job_id: str, pdf_bytes: bytes, theme: CardTheme) -> None:
    warnings: list[str] = []

    # ── S1: PDF extraction ────────────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S1", progress=10)
        s1_out = await s1_agent.execute(S1Input(job_id=job_id, pdf_bytes=pdf_bytes))
        warnings.extend(s1_out.warnings)
        logger.info("S1 done: %d words", s1_out.word_count)
    except Exception as exc:
        logger.error("S1 fatal: %s", exc)
        await db.update_job(
            job_id,
            status=JobStatus.ERROR,
            stage="S1",
            progress=10,
            warnings=warnings + [f"ERR-S1: {exc}"],
        )
        return

    # ── S2: Section parsing ───────────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S2", progress=25)
        s2_out = await s2_agent.execute(
            S2Input(
                job_id=job_id,
                raw_text=s1_out.raw_text,
                page_map=s1_out.page_map,
            )
        )
        warnings.extend(s2_out.warnings)
        if s2_out.degraded_mode:
            await db.update_job(job_id, status=JobStatus.RUNNING, degraded=True)
        logger.info("S2 done: %d sections, degraded=%s", len(s2_out.section_map), s2_out.degraded_mode)
    except Exception as exc:
        logger.error("S2 fatal: %s", exc)
        await db.update_job(
            job_id,
            status=JobStatus.ERROR,
            stage="S2",
            progress=25,
            warnings=warnings + [f"ERR-S2: {exc}"],
        )
        return

    # ── S6: Card JSON generation ──────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S6", progress=50)
        s6_out = await s6_agent.execute(
            S6Input(
                job_id=job_id,
                section_map=s2_out.section_map,
                page_map=s1_out.page_map,
                paper_metadata=s1_out.metadata,
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
        return

    # ── S7: PNG rendering ─────────────────────────────────────────────────────
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
