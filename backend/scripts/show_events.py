"""행동 이벤트 뷰어 (운영자용) — 백엔드 events 감사 로그 조회 + LLM 비용 추정.

사용법:
    python -m backend.scripts.show_events [limit]
    (배포 서버) docker compose exec backend python -m backend.scripts.show_events 50

PostHog가 행동 분석/세션리플레이(웹 UI)를 담당하고,
이 스크립트는 백엔드 감사 소스 오브 트루스(누가·언제·무엇 + 토큰/비용)를 본다.
"""
from __future__ import annotations

import asyncio
import sys

from backend.core import db

# 대략적 단가(USD per 1M tokens). 실제 청구는 Anthropic 콘솔이 정확.
# Haiku 기준(콘텐츠팀 다수). 설계팀(Sonnet) 호출은 더 비싸므로 하한 추정으로 본다.
INPUT_USD_PER_MTOK = 1.0
OUTPUT_USD_PER_MTOK = 5.0


def _fmt_row(e: dict) -> str:
    ts = (e.get("created_at") or "")[:16].replace("T", " ")
    et = e.get("event_type", "?")
    uid = e.get("user_id")
    job = e.get("job_id")
    p = e.get("payload") or {}
    head = f"{ts}  {et:<17} user={uid}"
    if job:
        head += f"  job={str(job)[:8]}"
    # 이벤트 이름은 구(upload)·신(deck_upload) 둘 다 매칭 — 레거시 데이터와 현재 데이터를 모두 포맷.
    if et in ("upload", "deck_upload"):
        head += f"  {p.get('filename')} ({p.get('card_count')}장)"
    elif et in ("pipeline_complete", "deck_pipeline_complete"):
        head += (
            f"  {p.get('status')}  {p.get('duration_s')}s"
            f"  in={p.get('input_tokens')} out={p.get('output_tokens')} calls={p.get('llm_calls')}"
            + ("  [degraded]" if p.get("degraded") else "")
        )
    elif et in ("export", "deck_export"):
        head += f"  imgs={p.get('image_count')}"
    return head


async def main(limit: int) -> None:
    events = await db.list_events(limit=limit)

    print(f"=== 최근 이벤트 ({len(events)}건, 최신순) ===")
    for e in events:
        print(_fmt_row(e))

    # 요약
    counts: dict[str, int] = {}
    in_tok = out_tok = calls = 0
    for e in events:
        counts[e["event_type"]] = counts.get(e["event_type"], 0) + 1
        if e["event_type"] in ("pipeline_complete", "deck_pipeline_complete"):
            p = e.get("payload") or {}
            in_tok += int(p.get("input_tokens") or 0)
            out_tok += int(p.get("output_tokens") or 0)
            calls += int(p.get("llm_calls") or 0)

    print("\n=== 요약 ===")
    print("이벤트: " + "  ".join(f"{k}×{v}" for k, v in sorted(counts.items())))
    cost = in_tok / 1_000_000 * INPUT_USD_PER_MTOK + out_tok / 1_000_000 * OUTPUT_USD_PER_MTOK
    print(f"LLM 누적: input {in_tok:,} tok / output {out_tok:,} tok / {calls} calls")
    print(f"예상 비용(대략, Haiku ${INPUT_USD_PER_MTOK}/${OUTPUT_USD_PER_MTOK} per MTok): ${cost:.4f}")
    print("  * 설계팀(Sonnet) 호출은 더 비쌈 - 실제 청구는 Anthropic 콘솔 확인")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(main(limit))
