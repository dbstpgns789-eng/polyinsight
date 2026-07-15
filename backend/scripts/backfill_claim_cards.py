"""일회성 백필 — 기존 authored_deck의 verify_json에 claim 카드 인덱스를 채운다.

배경: verify_deck이 카드 단위 순회로 바뀌기 전에 검증된 덱은 claim에 card가 없다
(팩트 패널 '수치 클릭→그 카드로 점프'가 비활성). paper_text가 남아 있는 덱을
새 코드로 재검증(compute_verify)해 verify_json을 갱신한다. 순수 코드 — LLM 호출 0.

멱등: 재실행하면 같은 결과(같은 html·paper_text → 같은 payload). 이미 card가 있어도
재계산이 동일하므로 안전. paper_text 없는 덱(구 저작물)은 검증 불가라 skip.

사용법(루트에서):
  PYTHONUTF8=1 .venv/Scripts/python.exe -m backend.scripts.backfill_claim_cards          # 실행
  PYTHONUTF8=1 .venv/Scripts/python.exe -m backend.scripts.backfill_claim_cards --dry     # 미리보기
"""
from __future__ import annotations

import asyncio
import json
import sys

import aiosqlite

from backend.agents.deck.pipeline import compute_verify
from backend.core import db as _db


async def backfill(dry: bool = False) -> tuple[int, int]:
    """(갱신, skip) 반환. skip = paper_text 없어 재검증 불가한 덱."""
    await _db.migrate()
    updated = skipped = 0
    async with _db._connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT job_id, html, paper_text FROM authored_deck"
        ) as cur:
            rows = await cur.fetchall()

        for r in rows:
            if not r["paper_text"] or not r["html"]:
                skipped += 1
                continue
            payload = compute_verify(r["html"], r["paper_text"])
            has_card = any(c.get("card") is not None for c in payload["claims"])
            tag = "카드있음" if has_card else "카드없음(분할마커 X)"
            print(f"  {r['job_id'][:12]}  claims={len(payload['claims'])}  {tag}")
            if not dry:
                await conn.execute(
                    "UPDATE authored_deck SET verify_json = ? WHERE job_id = ?",
                    (json.dumps(payload, ensure_ascii=False), r["job_id"]),
                )
            updated += 1
        if not dry:
            await conn.commit()
    return updated, skipped


async def main() -> None:
    dry = "--dry" in sys.argv
    print(f"claim 카드 인덱스 백필{' (DRY RUN)' if dry else ''} …")
    updated, skipped = await backfill(dry=dry)
    verb = "재검증 대상" if dry else "갱신"
    print(f"\n{verb} {updated}건 · skip {skipped}건(paper_text 없음)")


if __name__ == "__main__":
    asyncio.run(main())
