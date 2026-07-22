"""무료체험 퍼널 판독 — 벽 히트가 T1(결제 켜기) 트리거에 도달했는지 본다.

실행: python -m backend.scripts.funnel_report
"""
from __future__ import annotations

import asyncio
from collections import Counter

from backend.core import db

T1_TRIGGER = 30  # 벽 히트 고유 유저 — 이 밑에선 전환율이 통계가 아니라 노이즈다


async def main() -> None:
    evts = await db.list_events(limit=100000)
    by_type: dict[str, set[int]] = {}
    for e in evts:
        by_type.setdefault(e["event_type"], set()).add(e["user_id"])

    gate_kinds: Counter[str] = Counter()
    gate_users: set[int] = set()
    for e in evts:
        if e["event_type"] == "plan_gate_hit":
            gate_kinds[(e["payload"] or {}).get("kind", "?")] += 1
            gate_users.add(e["user_id"])

    jobs = await db.list_jobs(limit=100000)
    done = [j for j in jobs if j["status"] == "DONE"]

    def n(t: str) -> int:
        return len(by_type.get(t, ()))

    print("── 무료체험 퍼널 (고유 유저 기준) ─────────────────")
    print(f"  가입              {n('signup'):>5}")
    print(f"  논문 업로드        {n('deck_upload'):>5}")
    print(f"  덱 완성           {len({j['user_id'] for j in done}):>5}   (덱 {len(done)}건)")
    print(f"  편집              {n('deck_edit'):>5}")
    print(f"  ★벽 히트          {len(gate_users):>5}   (export {gate_kinds['export']} / author {gate_kinds['author']}회)")
    print(f"  내보내기 성공      {n('deck_export'):>5}")
    print()
    denom = len({j["user_id"] for j in done})
    if denom:
        print(f"  덱 완성 → 벽 히트   {len(gate_users) / denom:.0%}   ← ★제품 지표(발행 의사)")
    print(f"  T1 트리거({T1_TRIGGER}명)   {'도달 ✅' if len(gate_users) >= T1_TRIGGER else f'미달 ({len(gate_users)}/{T1_TRIGGER})'}")


if __name__ == "__main__":
    asyncio.run(main())
