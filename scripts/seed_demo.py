"""
Demo seed script — 에디터/내보내기 UI 테스트용 DONE 상태 job 삽입.

실행:
    python scripts/seed_demo.py

출력된 URL로 브라우저에서 바로 에디터 진입 가능.
"""

import asyncio
import sys
import types
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

JOB_ID = "demo-seed-001"
CARD_COUNT = 5


async def main() -> None:
    from backend.core import db
    from backend.core.config import settings
    from backend.agents.s6_card_json import _build_mock_card_data

    print(f"DB: {settings.DATABASE_URL}")
    await db.migrate()

    # ── 기존 시드 데이터 정리 ─────────────────────────────────────────────
    import aiosqlite

    db_path = settings.DATABASE_URL
    if db_path.startswith("sqlite:///"):
        db_path = db_path[len("sqlite:///"):]
    elif db_path.startswith("sqlite://"):
        db_path = db_path[len("sqlite://"):]

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("DELETE FROM card_images WHERE job_id = ?", (JOB_ID,))
        await conn.execute("DELETE FROM card_data  WHERE job_id = ?", (JOB_ID,))
        await conn.execute("DELETE FROM jobs        WHERE job_id = ?", (JOB_ID,))
        await conn.commit()

    # ── job 생성 (DONE 상태) ──────────────────────────────────────────────
    await db.create_job(JOB_ID, title="[데모] 탄소나노튜브 기반 고감도 가스 센서 개발")
    await db.update_job(JOB_ID, status="DONE", stage="S8", progress=100)

    # ── mock 카드 데이터 생성 및 저장 ─────────────────────────────────────
    meta = types.SimpleNamespace(
        title="탄소나노튜브 기반 고감도 가스 센서 개발",
        authors=["김철수", "이영희"],
        year=2024,
    )
    card_data = _build_mock_card_data(
        card_count=CARD_COUNT,
        section_map={"Abstract": "CNT 기반 가스 센서 연구 내용.", "Results": "감도 95.3% 달성."},
        paper_metadata=meta,
    )
    await db.save_card_data(JOB_ID, card_data.model_dump_json())

    # ── 카드별 stub PNG 이미지 저장 (에디터 이미지 슬롯 미리보기용) ────────
    stub_png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x04\x38\x00\x00\x04\x38"
        b"\x08\x02\x00\x00\x00\xe4\x98\xc4\x14"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    for card in card_data.cards:
        await db.save_card_image(JOB_ID, card.card_num, stub_png, ttl_hours=72)

    print("\n✓ 시드 완료!")
    print(f"  job_id : {JOB_ID}")
    print(f"  cards  : {len(card_data.cards)}장")
    print(f"\n브라우저에서 아래 URL로 진입하세요:")
    print(f"  http://localhost:5173/editor/{JOB_ID}\n")


asyncio.run(main())
