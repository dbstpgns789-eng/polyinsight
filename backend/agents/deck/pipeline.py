# -*- coding: utf-8 -*-
"""단일 저작 파이프라인 (헌법 v3.0) — 레거시 run_pipeline과 공존하는 별도 함수.

S1 추출(재사용) → S6 저작 → V 검증(fidelity, 재사용) → 저장 → 렌더 → 카드 PNG 저장.
가드레일·단계 update_job·usage 집계 패턴은 orchestrator.py를 복제(원본 무수정).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from ...core import db
from ...core.config import settings
from ...core.fidelity import verify_deck
from ...core.llm_client import get_usage, start_usage_capture
from ...core.models import JobStatus, S1Input
from ..s1_extractor import s1_agent
from .authoring import author_deck
from .deck_renderer import render_deck

logger = logging.getLogger(__name__)

_job_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)

# 입력 가드레일 — orchestrator._ABORT_WORD_FLOOR와 동일(비논문·스캔본 조기 차단).
_ABORT_WORD_FLOOR = 80


def _verify_to_json(html: str, paper_text: str | None) -> tuple[str, dict]:
    """덱 HTML 충실성 검증 → (json 문자열, dict). paper_text 없으면 검증 보류(빈 결과)."""
    if not paper_text:
        payload = {"verified": 0, "unverified": 0, "claims": [], "skipped": True}
        return json.dumps(payload, ensure_ascii=False), payload
    claims = verify_deck(html, paper_text)
    payload = {
        "verified": sum(c.verified for c in claims),
        "unverified": sum(not c.verified for c in claims),
        "claims": [{"value": c.value, "context": c.context, "verified": c.verified} for c in claims],
    }
    return json.dumps(payload, ensure_ascii=False), payload


def compute_verify(html: str, paper_text: str | None) -> dict:
    """검증만 수행(저장·렌더 없음) — nlpatch propose 미커밋 미리보기용."""
    _, payload = _verify_to_json(html, paper_text)
    return payload


async def persist_edited_deck(job_id: str, html: str) -> dict:
    """편집된 덱 HTML 영속화 — 재검증(원문 있으면) → 저장 → PNG 재렌더.

    PATCH(직접조작)·nlpatch(자연어) 공용. 반환: {verify, cardCount, warnings}.
    원문(paper_text)이 없는 기존 덱은 재검증을 건너뛰고 경고로 표면화(막지 않음, 헌법 3조).
    """
    existing = await db.get_authored_deck(job_id)
    paper_text = existing.get("paper_text") if existing else None
    # 편집된 HTML이 카드 수의 사실 소스 (카드 삭제 반영)
    card_count = html.count("data-screen-label") or (existing.get("card_count") if existing else 0)

    warnings: list[str] = []
    verify_json, verify = _verify_to_json(html, paper_text)
    if not paper_text:
        warnings.append("이 덱은 원문이 없어 재검증 불가 — 재생성 시 충실성 검증이 복원됩니다.")

    await db.save_authored_deck(job_id, html, verify_json, card_count, paper_text=None)

    images, render_warns = await render_deck(html, job_id=job_id)
    warnings.extend(render_warns)
    if not images:
        warnings.append("deck render: 0 cards rendered")
    else:
        await db.delete_card_images_above(job_id, len(images))

    return {"verify": verify, "cardCount": len(images) or card_count, "warnings": warnings}


async def run_authoring_pipeline(
    job_id: str,
    pdf_bytes: bytes,
    card_count: int = 7,
    persona: str | None = None,
    user_id: int | None = None,
    style_direction: str | None = None,
) -> None:
    async with _job_semaphore:
        await _execute(job_id, pdf_bytes, card_count, persona, user_id, style_direction)


async def _log_done(job_id: str, user_id: int | None, started: float, card_count: int) -> None:
    usage = get_usage() or {}
    final = await db.get_job(job_id)
    try:
        await db.log_event(
            "deck_pipeline_complete",
            user_id=user_id,
            job_id=job_id,
            payload={
                "status": final["status"] if final else None,
                "duration_s": round(time.monotonic() - started, 2),
                "card_count": card_count,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "llm_calls": usage.get("calls", 0),
                "model": settings.LLM_MODEL_AUTHOR,
            },
        )
    except Exception:
        logger.exception("deck_pipeline_complete 이벤트 기록 실패")


async def _execute(
    job_id: str,
    pdf_bytes: bytes,
    card_count: int,
    persona: str | None,
    user_id: int | None,
    style_direction: str | None = None,
) -> None:
    start_usage_capture()
    started = time.monotonic()
    warnings: list[str] = []

    # ── S1: 추출 (재사용) ──────────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="S1", progress=10)
        s1_out = await s1_agent.execute(S1Input(job_id=job_id, pdf_bytes=pdf_bytes))
        warnings.extend(s1_out.warnings)
        logger.info("deck S1: %d words", s1_out.word_count)
    except Exception as exc:
        logger.error("deck S1 fatal: %s", exc)
        await db.update_job(job_id, status=JobStatus.ERROR, stage="S1", progress=10,
                            warnings=warnings + [f"ERR-S1: {exc}"])
        await _log_done(job_id, user_id, started, card_count)
        return

    # 입력 가드레일 — thin input 조기 차단
    if s1_out.word_count < _ABORT_WORD_FLOOR:
        msg = (f"ABORT-S1: PDF에서 충분한 텍스트를 추출하지 못했습니다 "
               f"({s1_out.word_count}단어). 스캔본이거나 논문이 아닐 수 있습니다.")
        await db.update_job(job_id, status=JobStatus.ERROR, stage="S1", progress=10,
                            degraded=True, warnings=warnings + [msg])
        await _log_done(job_id, user_id, started, card_count)
        return

    # ── S6: 단일 저작 ──────────────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="AUTHOR", progress=40)
        html = await author_deck(
            raw_text=s1_out.raw_text,
            metadata=s1_out.metadata,
            card_count=card_count,
            persona=persona,
            style_direction=style_direction,
        )
        if not html or "data-screen-label" not in html:
            raise ValueError("저작 결과에 카드(data-screen-label)가 없습니다")
    except Exception as exc:
        logger.error("deck AUTHOR fatal: %s", exc)
        await db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40,
                            warnings=warnings + [f"ERR-AUTHOR: {exc}"])
        await _log_done(job_id, user_id, started, card_count)
        return

    # ── V: 충실성 검증 (재사용) ────────────────────────────────────────────
    await db.update_job(job_id, status=JobStatus.RUNNING, stage="VERIFY", progress=70)
    claims = verify_deck(html, s1_out.raw_text)
    verify_json = json.dumps({
        "verified": sum(c.verified for c in claims),
        "unverified": sum(not c.verified for c in claims),
        "claims": [{"value": c.value, "context": c.context, "verified": c.verified} for c in claims],
    }, ensure_ascii=False)

    # 저장 (검증 리포트는 렌더 실패와 무관하게 확보). 원문은 편집본 재검증(Phase 3)용으로 보관.
    await db.save_authored_deck(job_id, html, verify_json, card_count, paper_text=s1_out.raw_text)

    # ── 렌더: 카드별 PNG ───────────────────────────────────────────────────
    await db.update_job(job_id, status=JobStatus.RUNNING, stage="RENDER", progress=85)
    images, render_warns = await render_deck(html, job_id=job_id)
    warnings.extend(render_warns)
    if not images:
        warnings.append("deck render: 0 cards rendered")
    else:
        await db.delete_card_images_above(job_id, len(images))

    # ── 완료 ───────────────────────────────────────────────────────────────
    status = JobStatus.DONE if images else JobStatus.ERROR
    await db.update_job(job_id, status=status, stage="DONE", progress=100, warnings=warnings)
    await _log_done(job_id, user_id, started, card_count)
