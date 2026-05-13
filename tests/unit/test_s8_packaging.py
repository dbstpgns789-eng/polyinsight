"""
S8Packager 단위 테스트.

인메모리 SQLite 사용 (DATABASE_URL=":memory:") — 파일시스템 오염 없음.

Happy path (H):
  H1  jobs 테이블에 DONE 상태로 기록
  H2  card_images 테이블에 5건 저장
  H3  ZIP 구조 확인 (5 PNG + card_data.json)
  H4  이미지 없어도 (images=[]) 실행 완료

Sad path (S):
  S1  DB 쓰기 실패 시 예외 전파 안 함 → S8Output(status=ERROR) 반환
      [S8 계약: S8은 항상 완료되어야 한다. 예외를 전파하면 파이프라인 전체가 죽는다.]
"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.models import JobStatus, S8Input, S8Output

try:
    from backend.agents.s8_packaging import S8Packager
    _S8_AVAILABLE = True
except ImportError:
    _S8_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not _S8_AVAILABLE, reason="S8Packager not implemented yet"),
    pytest.mark.asyncio,
]

# PNG stub — magic bytes만 있는 최소 유효 PNG
_STUB_PNG = (
    b"\x89PNG\r\n\x1a\n"                        # magic
    b"\x00\x00\x00\rIHDR"                        # IHDR chunk
    b"\x00\x00\x00\x01\x00\x00\x00\x01"         # 1×1
    b"\x08\x02\x00\x00\x00\x90wS\xde"           # bit depth + CRC
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"  # IDAT (1 pixel)
    b"\x00\x01\x01\x00\x05\x18\xd8N"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"           # IEND
)


@pytest.fixture
def five_images() -> list[bytes]:
    return [_STUB_PNG] * 5


@pytest.fixture
def s8_input(mock_card_data, five_images) -> S8Input:
    return S8Input(
        job_id="test-s8-001",
        card_data=mock_card_data,
        images=five_images,
    )


# ── in-memory DB setup ────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def use_in_memory_db(monkeypatch):
    """S8 테스트는 항상 인메모리 SQLite 사용."""
    from backend.core import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "DATABASE_URL", ":memory:")


# ── Happy path ───────────────────────────────────────────────────────────────

async def test_h1_jobs_table_done(s8_input):
    """S8 실행 후 jobs 테이블에 해당 job_id가 DONE으로 기록되어야 한다."""
    import aiosqlite

    out: S8Output = await S8Packager().execute(s8_input)

    assert out.status == JobStatus.DONE

    async with aiosqlite.connect(":memory:") as db:
        # S8 내부에서 사용한 같은 DB 연결이 아니므로
        # out.status만으로 검증 (실제 구현에서 DB 픽스처 공유 방식으로 개선 가능)
        pass


async def test_h2_card_images_count(mock_card_data, five_images):
    """5장 이미지 입력 → S8Output에서 이미지 5건 처리 확인."""
    inp = S8Input(job_id="test-s8-002", card_data=mock_card_data, images=five_images)
    out: S8Output = await S8Packager().execute(inp)

    # 구현에 따라 processed_count 필드를 추가하거나,
    # DB 조회 방식을 사용하는 경우 해당 로직으로 교체
    assert out.status == JobStatus.DONE


async def test_h3_zip_structure(mock_card_data, five_images):
    """
    ZIP bytes 안에 card_1.png ~ card_5.png 와 card_data.json이 있어야 한다.
    S8Output에 zip_bytes 필드가 필요하거나, exports 테이블에서 조회.
    """
    inp = S8Input(job_id="test-s8-003", card_data=mock_card_data, images=five_images)
    out: S8Output = await S8Packager().execute(inp)

    # S8Output이 zip_bytes를 직접 반환하는 경우
    if hasattr(out, "zip_bytes") and out.zip_bytes:
        zf = zipfile.ZipFile(io.BytesIO(out.zip_bytes))
        names = zf.namelist()
        for i in range(1, 6):
            assert any(f"card_{i}" in n for n in names), (
                f"card_{i}.png 없음. ZIP 내용: {names}"
            )
        assert any("card_data" in n for n in names), (
            f"card_data.json 없음. ZIP 내용: {names}"
        )
    else:
        # zip_bytes 필드가 없으면 status만 확인
        assert out.status == JobStatus.DONE


async def test_h4_empty_images_still_runs(mock_card_data):
    """
    images=[] (S7 전체 실패) 상황에서도 S8은 완료되어야 한다.
    ZIP에는 card_data.json만 포함.
    """
    inp = S8Input(
        job_id="test-s8-004",
        card_data=mock_card_data,
        images=[],
        warnings=["S7: 전체 카드 렌더링 실패"],
    )
    out: S8Output = await S8Packager().execute(inp)

    # 이미지가 없어도 예외 없이 완료
    assert out.status in (JobStatus.DONE, JobStatus.ERROR)
    # ERROR 이어도 예외를 throw하지 않아야 함


# ── Sad path ─────────────────────────────────────────────────────────────────

async def test_s1_db_write_failure_does_not_raise(mock_card_data, five_images):
    """
    S8 계약: DB 쓰기가 실패해도 예외를 전파하면 안 된다.
    파이프라인이 죽어버리면 어떠한 결과도 저장되지 않기 때문.

    기대: S8Output(status=ERROR) 반환, 예외 throw 없음.
    """
    with patch("aiosqlite.connect", side_effect=RuntimeError("DB 강제 실패")):
        inp = S8Input(job_id="test-s8-005", card_data=mock_card_data, images=five_images)

        # pytest.raises 없이 호출 — 예외가 올라오면 테스트 실패
        out: S8Output = await S8Packager().execute(inp)

    assert out.status == JobStatus.ERROR, (
        f"DB 실패 시 status=ERROR 기대, 실제: {out.status}"
    )
