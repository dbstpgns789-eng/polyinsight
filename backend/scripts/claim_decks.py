# -*- coding: utf-8 -*-
"""eval로 만든 덱을 내 계정으로 옮긴다 — 실 API 토큰으로 만든 작품은 대시보드에 남아야 한다.

배경: eval_runner는 이력 격리(deck_manifest 초기화)를 위해 전용 유저로 돈다.
그 결과 실제 비용을 낸 사람의 대시보드엔 아무것도 안 보인다. 실험은 격리하되,
**산출물은 소유자에게 돌려준다.**

사용:
  python -m backend.scripts.claim_decks --to dbstpgns789@gmail.com [--from eval@polyinsight.local]
  python -m backend.scripts.claim_decks --to <email> --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import aiosqlite

from backend.core import db
from backend.core.config import settings


async def main_async(from_email: str, to_email: str, dry: bool, label: str | None) -> None:
    src = await db.get_user_by_email(from_email.strip().lower())
    dst = await db.get_user_by_email(to_email.strip().lower())
    if not src:
        sys.exit(f"[ERROR] 원 소유자 없음: {from_email}")
    if not dst:
        sys.exit(f"[ERROR] 대상 유저 없음: {to_email}")

    path = settings.DATABASE_URL.replace("sqlite:///", "")
    async with aiosqlite.connect(path) as conn:
        conn.row_factory = aiosqlite.Row
        q = "SELECT job_id, title, status, created_at FROM jobs WHERE user_id = ? AND status = 'DONE'"
        params: list = [src["id"]]
        async with conn.execute(q + " ORDER BY created_at", params) as cur:
            rows = await cur.fetchall()

        if not rows:
            print("옮길 덱이 없습니다.")
            return

        print(f"{from_email}(id={src['id']}) → {to_email}(id={dst['id']})  덱 {len(rows)}개")
        for r in rows:
            print(f"  {r['created_at'][:16]}  {(r['title'] or '')[:50]}")

        if dry:
            print("\n(--dry-run — 실제로 옮기지 않았습니다)")
            return

        await conn.execute(
            "UPDATE jobs SET user_id = ? WHERE user_id = ? AND status = 'DONE'",
            (dst["id"], src["id"]),
        )
        # 저작 지문 이력도 함께 이전 — 소유자의 '최근 덱' 변주 참고에 반영되도록
        await conn.execute(
            "UPDATE deck_manifest SET user_id = ? WHERE user_id = ?",
            (dst["id"], src["id"]),
        )
        await conn.commit()
        print(f"\n완료 — {to_email} 대시보드에서 확인하세요.")


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="eval 덱을 내 계정으로 이전")
    ap.add_argument("--to", required=True, help="받을 계정 이메일")
    ap.add_argument("--from", dest="from_email", default="eval@polyinsight.local")
    ap.add_argument("--label", default=None, help="(예약) 특정 런만 — 현재는 전체")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    asyncio.run(main_async(args.from_email, args.to, args.dry_run, args.label))


if __name__ == "__main__":
    main()
