# -*- coding: utf-8 -*-
"""단일 저작 파이프라인 (헌법 v3.0) — 유일한 저작 오케스트레이터.

S1 추출(재사용) → S6 저작 → V 검증(fidelity, 재사용) → 저장 → 렌더 → 카드 PNG 저장.
구 저작 파이프라인(orchestrator.run_pipeline·s6_card_json)은 L0(2026-07-09)에서 삭제됨.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from ...core import db
from ...core.config import settings
from ...core.fidelity import derived_claims, verify_deck
from ...core.llm_client import LLMCreditError, get_usage, start_usage_capture
from ...core.models import JobStatus, S1Input
from ..s1_extractor import s1_agent
from ...scripts.deck_judge import judge_pngs
from .authoring import MAX_SOURCE_CHARS, author_deck
from .source_trim import trim_source
from .best_of import pick_best
from .deck_renderer import render_deck
from .figures import extract_figures
from .manifest import build_history_block, parse_manifest, selfcheck_failures
from .vision_fix import apply_vision_fix

logger = logging.getLogger(__name__)

_job_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)

# 입력 가드레일 — 비논문·스캔본 조기 차단(S6 호출 전, 비용 0 방어).
_ABORT_WORD_FLOOR = 80


def _verify_to_json(html: str, paper_text: str | None) -> tuple[str, dict]:
    """덱 HTML 충실성 검증 → (json 문자열, dict). paper_text 없으면 검증 보류(빈 결과).

    V1(존재 대조) + V2(파생수치 산수 검산). V2는 '142→238을 170% 증가'처럼 원문 대조로는
    못 잡는 내부 모순을 잡는다 — suspect는 웹 팩트 패널이 표면화한다(막지 않음).
    """
    if not paper_text:
        payload = {"verified": 0, "unverified": 0, "claims": [], "derived": [], "skipped": True}
        return json.dumps(payload, ensure_ascii=False), payload
    claims = verify_deck(html, paper_text)
    payload = {
        "verified": sum(c.verified for c in claims),
        "unverified": sum(not c.verified for c in claims),
        "claims": [
            {"value": c.value, "context": c.context, "verified": c.verified, "card": c.card}
            for c in claims
        ],
        "derived": derived_claims(html, paper_text),
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
        # 프루닝 임계값 = html 카드 수(= 유효 최대 card_num). len(images)는 성공 수라
        # 중간 카드 실패 시 유효한 상위 카드를 삭제해버린다(무성 데이터 손실).
        await db.delete_card_images_above(job_id, card_count)

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


async def _author_best_of(author_fn, n: int, job_id: str) -> tuple[str, str]:
    """N개를 병렬 저작하고 저지가 최고를 고른다. (best_html, 선택 경고) 반환.

    선택된 덱만 이후 비전 루프를 탄다 — 후보 전부를 다듬는 건 낭비다.
    저작이 하나라도 살아남으면 진행(전부 죽으면 예외 → 상위에서 ERROR).
    """
    drafts = await asyncio.gather(*[author_fn() for _ in range(n)], return_exceptions=True)
    cands: list[dict] = []
    for d in drafts:
        if isinstance(d, Exception) or not d or "data-screen-label" not in d:
            logger.warning("best-of-N: 후보 저작 실패 — 제외 (%s)", type(d).__name__)
            continue
        cands.append({"html": d})
    if not cands:
        raise ValueError("모든 후보 저작이 실패했습니다")

    await db.update_job(job_id, status=JobStatus.RUNNING, stage="SELECT", progress=52)

    async def _score(c: dict) -> None:
        try:
            pngs, _ = await render_deck(c["html"])      # 저장하지 않는 임시 렌더
            c["pngs"] = pngs
            c["judge"] = await judge_pngs(pngs) if pngs else None
        except Exception as exc:
            logger.warning("best-of-N: 후보 심사 실패(%s)", exc)
            c["judge"] = None

    await asyncio.gather(*[_score(c) for c in cands])
    best, log = pick_best(cands)
    return best["html"], log


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
    # 원문 절단은 소리 없이 일어나면 안 된다 — V는 원문 전문으로 검증하고 저지는 논문을 못 보므로,
    # 본문을 누락한 덱이 모든 계기판에서 클린 패스한다.
    # ★참고문헌 제거는 '손실'이 아니다(오히려 결론이 살아난다). 본문 생략만 경고한다.
    _source, _ = trim_source(s1_out.raw_text, MAX_SOURCE_CHARS)
    if "중략" in _source:
        warnings.append(
            f"SOURCE_TRUNCATED: 원문이 매우 길어({len(s1_out.raw_text):,}자) 본문 중간부를 생략했습니다. "
            f"연구 배경과 결과·결론은 모두 반영했지만, **중간부(실험 조건 등)의 일부 수치가 "
            f"덱에 빠졌을 수 있습니다.** 카드의 수치를 원문과 대조해 확인해 주세요."
        )

    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="AUTHOR", progress=40)
        # 이 계정의 최근 덱(아크·팔레트·모티프)을 소프트 변주 선호로 주입 — 동질화 차단.
        recent = await db.get_recent_manifests(user_id)
        # 논문이 곧 레퍼런스 — 이 논문의 그림을 시각 앵커로 준다(남의 덱이 아니라).
        figures = extract_figures(pdf_bytes, max_figures=settings.AUTHOR_FIGURES_N)
        if not figures:
            warnings.append("논문에서 그림을 찾지 못했습니다 — 텍스트만으로 저작합니다.")

        async def _author_once() -> str:
            return await author_deck(
                raw_text=s1_out.raw_text,
                metadata=s1_out.metadata,
                card_count=card_count,
                persona=persona,
                style_direction=style_direction,
                history_block=build_history_block(recent),
                figures=figures,
            )

        n = max(1, settings.AUTHOR_CANDIDATES)
        if n == 1:
            html = await _author_once()
        else:
            # ★Best-of-N — 저작 분산을 통제하는 유일한 수단.
            # (Opus 4.8은 sampling 파라미터를 거부해 temperature로 분산을 줄일 수 없다.
            #  실측: 같은 논문·같은 코드 5회 저작에서 integrity 2↔4, finish 1~4.)
            html, sel_warn = await _author_best_of(_author_once, n, job_id)
            if sel_warn:
                warnings.append(sel_warn)

        if not html or "data-screen-label" not in html:
            raise ValueError("저작 결과에 카드(data-screen-label)가 없습니다")
    except LLMCreditError as exc:
        # 크레딧 소진 — 유저 잘못이 아니다. 영문 스택트레이스 대신 사람 말로.
        logger.error("deck AUTHOR: 크레딧 소진")
        await db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40,
                            warnings=warnings + [str(exc)])
        await _log_done(job_id, user_id, started, card_count)
        return
    except Exception as exc:
        logger.error("deck AUTHOR fatal: %s", exc)
        await db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40,
                            warnings=warnings + [f"ERR-AUTHOR: {exc}"])
        await _log_done(job_id, user_id, started, card_count)
        return

    # 저작 지문 저장 (소프트 — 미선언은 경고일 뿐 실패 아님. 코드가 형태를 강제하지 않는다)
    manifest = parse_manifest(html)
    if manifest:
        await db.save_deck_manifest(job_id, user_id, json.dumps(manifest, ensure_ascii=False))
    else:
        warnings.append("PI_MANIFEST 미선언 — 이 덱은 반복이력에 기록되지 않습니다.")

    # 자가판정(PI_SELFCHECK) — 모델이 스스로 실패라 신고한 항목을 경고로 표면화.
    # 자기신고라 정본은 아니고 V·저지와의 삼각측량 신호(막지 않음, 헌법 3조).
    sc_fails = selfcheck_failures(html)
    if sc_fails:
        warnings.append("자가검수 미통과 항목: " + ", ".join(sc_fails))

    # ── POLISH: 비전 자기수정 — 모델이 자기 카드의 렌더를 처음으로 '본다' ──
    # 텍스트 자가검수는 무력하다(실측: 5편 전부 '전항 통과' 신고 vs 저지는 5편 전부 결함 발견).
    # 빈 공간·겹침·형상 오독은 렌더를 봐야만 잡힌다. 실패는 소프트 — 원본 유지.
    # ★루프여야 한다(1패스가 아니라). 실측: 접근성 수정으로 텍스트를 늘리자 제목과 수치가
    #   겹쳐 finish 4→1. **수정이 만든 새 결함을 아무도 못 봤다** — 수정 후 렌더를 다시 봐야 한다.
    if settings.AUTHOR_VISION_FIX and not settings.DEV_MOCK_LLM:
        try:
            for rnd in range(1, settings.AUTHOR_VISION_ROUNDS + 1):
                await db.update_job(job_id, status=JobStatus.RUNNING, stage="POLISH",
                                    progress=55 + rnd * 5)
                draft_pngs, _ = await render_deck(html)   # job_id 없이 = 저장하지 않는 임시 렌더
                fixed, fix_warns = await apply_vision_fix(html, draft_pngs, round_no=rnd)
                warnings.extend(fix_warns)
                if fixed == html:                         # 고칠 게 없다 → 수렴, 조기 종료
                    logger.info("POLISH round %d: 변경 없음 — 수렴", rnd)
                    break
                html = fixed
        except Exception as exc:
            logger.warning("POLISH 단계 실패(%s) — 직전 HTML로 계속", exc)
            warnings.append(f"비전 수정 단계를 건너뛰었습니다 ({type(exc).__name__}).")

    # ── V: 충실성 검증 (V1 존재 대조 + V2 파생수치 산수) ───────────────────
    await db.update_job(job_id, status=JobStatus.RUNNING, stage="VERIFY", progress=70)
    verify_json, _ = _verify_to_json(html, s1_out.raw_text)

    # 저장 (검증 리포트는 렌더 실패와 무관하게 확보). 원문은 편집본 재검증(Phase 3)용으로 보관.
    await db.save_authored_deck(job_id, html, verify_json, card_count, paper_text=s1_out.raw_text)

    # ── 렌더: 카드별 PNG ───────────────────────────────────────────────────
    await db.update_job(job_id, status=JobStatus.RUNNING, stage="RENDER", progress=85)
    images, render_warns = await render_deck(html, job_id=job_id)
    warnings.extend(render_warns)
    if not images:
        warnings.append("deck render: 0 cards rendered")
    else:
        # 프루닝 임계값 = html 카드 수(= 유효 최대 card_num). len(images)는 성공 수라
        # 중간 카드 실패 시 유효한 상위 카드를 삭제해버린다(무성 데이터 손실).
        await db.delete_card_images_above(job_id, html.count("data-screen-label"))

    # ── 완료 ───────────────────────────────────────────────────────────────
    status = JobStatus.DONE if images else JobStatus.ERROR
    await db.update_job(job_id, status=status, stage="DONE", progress=100, warnings=warnings)
    await _log_done(job_id, user_id, started, card_count)
