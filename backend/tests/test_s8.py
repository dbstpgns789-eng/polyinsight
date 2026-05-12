"""S8 Packaging Agent 단위 테스트 — SQLite + ZIP 검증.

외부 의존성 없음 (LLM·Playwright 불필요).
임시 SQLite DB를 매 테스트마다 생성 후 삭제.
"""
from __future__ import annotations

import pathlib, sys, tempfile, os
sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

import pytest


# ── DB 픽스처: 테스트마다 임시 SQLite 파일 사용 ───────────────────────────────

@pytest.fixture
async def tmp_db(monkeypatch, tmp_path):
    """임시 DATABASE_URL을 주입하고 테이블을 migrate한다."""
    db_file = tmp_path / "test.db"
    db_url = f"sqlite:///{db_file}"

    # settings를 patch
    from backend.core import config as cfg_mod
    monkeypatch.setattr(cfg_mod.settings, "DATABASE_URL", db_url)

    # migrate (테이블 생성)
    from backend.core import db
    await db.migrate()

    # job 레코드 선생성 (FK 충족)
    await db.create_job("test-s8-job", title="셀룰로오스 마이크로비드 테스트")
    return db


@pytest.fixture
def fake_images() -> list[bytes]:
    """1×1 픽셀 더미 PNG bytes 5장."""
    # 최소 유효 PNG (1×1, 흑색)
    png_1x1 = (
        b"\x89PNG\r\n\x1a\n"                   # PNG signature
        b"\x00\x00\x00\rIHDR"                  # IHDR chunk
        b"\x00\x00\x00\x01\x00\x00\x00\x01"   # width=1, height=1
        b"\x08\x02\x00\x00\x00\x90wS\xde"     # 8-bit RGB, CRC
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f" # IDAT
        b"\x00\x00\x01\x01\x00\x05\x18\xd8N"  # data + CRC
        b"\x00\x00\x00\x00IEND\xaeB`\x82"      # IEND
    )
    return [png_1x1] * 5


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_s8_saves_card_data(tmp_db, mock_card_data, fake_images):
    """card_data가 SQLite card_data 테이블에 저장되어야 한다."""
    from backend.agents.s8_packaging import S8PackagingAgent
    from backend.core.models import S8Input

    agent = S8PackagingAgent()
    inp = S8Input(job_id="test-s8-job", card_data=mock_card_data, images=fake_images)
    await agent.execute(inp)

    saved = await tmp_db.get_card_data("test-s8-job")
    assert saved is not None
    assert "card1" in saved  # JSON 문자열에 card1 키 포함


@pytest.mark.asyncio
async def test_s8_saves_card_images(tmp_db, mock_card_data, fake_images):
    """PNG bytes가 card_images 테이블에 5개 저장되어야 한다."""
    from backend.agents.s8_packaging import S8PackagingAgent
    from backend.core.models import S8Input

    agent = S8PackagingAgent()
    inp = S8Input(job_id="test-s8-job", card_data=mock_card_data, images=fake_images)
    await agent.execute(inp)

    images = await tmp_db.get_card_images("test-s8-job")
    assert len(images) == 5


@pytest.mark.asyncio
async def test_s8_creates_zip_export(tmp_db, mock_card_data, fake_images):
    """ZIP export가 exports 테이블에 저장되어야 한다."""
    import aiosqlite
    from backend.agents.s8_packaging import S8PackagingAgent
    from backend.core.models import S8Input
    from backend.core.db import _db_path

    agent = S8PackagingAgent()
    inp = S8Input(job_id="test-s8-job", card_data=mock_card_data, images=fake_images)
    await agent.execute(inp)

    async with aiosqlite.connect(_db_path()) as conn:
        async with conn.execute("SELECT filename, zip_bytes FROM exports WHERE job_id = ?", ("test-s8-job",)) as cur:
            row = await cur.fetchone()

    assert row is not None, "No export row found"
    filename, zip_bytes = row
    assert filename.startswith("polyinsight_")
    assert filename.endswith(".zip")
    assert len(zip_bytes) > 0


@pytest.mark.asyncio
async def test_s8_zip_contains_correct_files(tmp_db, mock_card_data, fake_images):
    """ZIP 내부에 card_01.png ~ card_05.png + card_data.json이 있어야 한다."""
    import io, zipfile, aiosqlite
    from backend.agents.s8_packaging import S8PackagingAgent
    from backend.core.models import S8Input
    from backend.core.db import _db_path

    agent = S8PackagingAgent()
    inp = S8Input(job_id="test-s8-job", card_data=mock_card_data, images=fake_images)
    await agent.execute(inp)

    async with aiosqlite.connect(_db_path()) as conn:
        async with conn.execute("SELECT zip_bytes FROM exports WHERE job_id = ?", ("test-s8-job",)) as cur:
            row = await cur.fetchone()

    zf = zipfile.ZipFile(io.BytesIO(row[0]))
    names = zf.namelist()
    for i in range(1, 6):
        assert f"card_{i:02d}.png" in names, f"card_{i:02d}.png not in ZIP"
    assert "card_data.json" in names


@pytest.mark.asyncio
async def test_s8_status_done_on_success(tmp_db, mock_card_data, fake_images):
    """정상 실행 시 job status가 DONE이어야 한다."""
    from backend.agents.s8_packaging import S8PackagingAgent
    from backend.core.models import S8Input, JobStatus

    agent = S8PackagingAgent()
    inp = S8Input(job_id="test-s8-job", card_data=mock_card_data, images=fake_images)
    out = await agent.execute(inp)

    assert out.status == JobStatus.DONE


@pytest.mark.asyncio
async def test_s8_status_error_on_empty_images(tmp_db, mock_card_data):
    """images=[] 이면 job status가 ERROR여야 한다."""
    from backend.agents.s8_packaging import S8PackagingAgent
    from backend.core.models import S8Input, JobStatus

    agent = S8PackagingAgent()
    inp = S8Input(job_id="test-s8-job", card_data=mock_card_data, images=[])
    out = await agent.execute(inp)

    assert out.status == JobStatus.ERROR
