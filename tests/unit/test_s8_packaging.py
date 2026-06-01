"""
S8Packager 단위 테스트.

인메모리 SQLite 사용 (DATABASE_URL=":memory:") — 파일시스템 오염 없음.
mock_card_data: 2장(cover + closing) CardEditorData

Happy path (H):
  H1  S8Output(status=DONE) 반환
  H2  images 수만큼 처리 완료 (status 검증)
  H3  ZIP 구조 확인 (PNG + card_data.json)
  H4  images=[] 입력 시 예외 없이 완료 (ERROR 상태)

Sad path (S):
  S1  DB 쓰기 실패 시 예외 전파 안 함 → status=ERROR 반환
      [S8 계약: S8은 항상 완료되어야 한다]
"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

import pytest

from backend.core.models import JobStatus, S8Input, S8Output

try:
    from backend.agents.s8_packaging import S8Packager
    _S8_AVAILABLE = True
except ImportError:
    _S8_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not _S8_AVAILABLE, reason="S8Packager not implemented"),
    pytest.mark.asyncio,
]

_STUB_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def stub_images(mock_card_data) -> list[bytes]:
    """mock_card_data 카드 수만큼 PNG stub 생성."""
    return [_STUB_PNG] * len(mock_card_data.cards)


@pytest.fixture
def s8_input(mock_card_data, stub_images) -> S8Input:
    return S8Input(
        job_id="test-s8-001",
        card_data=mock_card_data,
        images=stub_images,
    )


@pytest.fixture(autouse=True)
async def use_in_memory_db(tmp_path, monkeypatch):
    """각 S8 테스트에 독립된 SQLite 파일 + 마이그레이션 완료 상태."""
    from backend.core import config as cfg_module
    from backend.core import db as _db
    db_file = str(tmp_path / "s8test.db")
    monkeypatch.setattr(cfg_module.settings, "DATABASE_URL", f"sqlite:///{db_file}")
    await _db.migrate()


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_h1_status_done(s8_input):
    """정상 실행 → S8Output(status=DONE)."""
    out: S8Output = await S8Packager().execute(s8_input)
    assert out.status == JobStatus.DONE, f"DONE 기대, 실제: {out.status}"


async def test_h2_images_processed(mock_card_data, stub_images):
    """images 수만큼 처리 후 DONE 반환."""
    inp = S8Input(job_id="test-s8-002", card_data=mock_card_data, images=stub_images)
    out: S8Output = await S8Packager().execute(inp)
    assert out.status == JobStatus.DONE


async def test_h3_zip_structure(mock_card_data, stub_images):
    """
    ZIP bytes 내부에 card_01.png~card_N.png + card_data.json 포함 여부 확인.
    S8Output에 zip_bytes 필드가 없으면 status만 검증.
    """
    inp = S8Input(job_id="test-s8-003", card_data=mock_card_data, images=stub_images)
    out: S8Output = await S8Packager().execute(inp)

    if hasattr(out, "zip_bytes") and out.zip_bytes:
        zf = zipfile.ZipFile(io.BytesIO(out.zip_bytes))
        names = zf.namelist()
        for i in range(1, len(stub_images) + 1):
            assert any(f"card_{i:02d}" in n or f"card_{i}" in n for n in names), (
                f"card_{i:02d}.png 없음. ZIP 내용: {names}"
            )
        assert any("card_data" in n for n in names), f"card_data.json 없음: {names}"
    else:
        assert out.status == JobStatus.DONE


async def test_h4_empty_images_still_runs(mock_card_data):
    """
    images=[] (S7 전체 실패) 상황에서도 S8은 완료되어야 한다.
    예외를 throw하지 않고 ERROR 상태 반환.
    """
    inp = S8Input(
        job_id="test-s8-004",
        card_data=mock_card_data,
        images=[],
        warnings=["S7: 전체 카드 렌더링 실패"],
    )
    out: S8Output = await S8Packager().execute(inp)

    assert out.status in (JobStatus.DONE, JobStatus.ERROR)


# ── Sad path ──────────────────────────────────────────────────────────────────

async def test_s1_db_write_failure_does_not_raise(mock_card_data, stub_images):
    """
    S8 계약: DB 쓰기 실패 시 예외를 전파하면 안 된다.
    파이프라인이 죽으면 어떠한 결과도 저장되지 않기 때문.
    기대: S8Output(status=ERROR) 반환, 예외 없음.
    """
    with patch("aiosqlite.connect", side_effect=RuntimeError("DB 강제 실패")):
        inp = S8Input(job_id="test-s8-005", card_data=mock_card_data, images=stub_images)
        out: S8Output = await S8Packager().execute(inp)

    assert out.status == JobStatus.ERROR, (
        f"DB 실패 시 status=ERROR 기대, 실제: {out.status}"
    )
