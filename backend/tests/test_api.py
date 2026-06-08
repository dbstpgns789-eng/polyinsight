"""API 라우터 단위 테스트.

- run_pipeline은 mock (LLM/Playwright 없이 실행)
- SQLite는 :memory: 사용
- httpx AsyncClient로 엔드포인트 직접 호출
"""
from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core.config import settings
from backend.main import app


# ── 픽스처 ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def use_memory_db(tmp_path, monkeypatch):
    """각 테스트마다 독립된 SQLite 파일 사용."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    await _db.migrate()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def dummy_pdf() -> bytes:
    """최소 PDF 바이너리 (S1이 처리하지 않도록 pipeline을 mock함)."""
    return b"%PDF-1.4 dummy"


# ── 업로드 ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_returns_job_id(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        resp = await client.post(
            "/api/upload",
            files={"file": ("paper.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    assert resp.status_code == 202
    body = resp.json()
    assert "jobId" in body
    assert body["status"] == "PENDING"


@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        resp = await client.post(
            "/api/upload",
            files={"file": ("report.txt", b"hello", "text/plain")},
            data={"card_count": "5"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "ERR-INP-001"


@pytest.mark.asyncio
async def test_upload_rejects_oversized(client):
    big = b"x" * (51 * 1024 * 1024)
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        resp = await client.post(
            "/api/upload",
            files={"file": ("big.pdf", big, "application/pdf")},
            data={"card_count": "5"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "ERR-INP-002"


@pytest.mark.asyncio
async def test_upload_card_count_validation(client, dummy_pdf):
    """card_count 범위 벗어나면 422."""
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        resp = await client.post(
            "/api/upload",
            files={"file": ("paper.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "20"},  # max 15
        )
    assert resp.status_code == 422


# ── 상태 폴링 ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_status_unknown_job(client):
    resp = await client.get("/api/status/nonexistent-id")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "ERR-JOB-001"


@pytest.mark.asyncio
async def test_status_returns_pending(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        upload = await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    job_id = upload.json()["jobId"]

    resp = await client.get(f"/api/status/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["jobId"] == job_id
    assert body["status"] == "PENDING"
    assert "progress" in body


# ── 카드 데이터 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_cards_not_found(client):
    resp = await client.get("/api/cards/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_cards_returns_data(client, dummy_pdf, mock_card_data):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        upload = await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    job_id = upload.json()["jobId"]

    # DB에 card_data 수동 주입
    await _db.save_card_data(job_id, mock_card_data.model_dump_json())

    resp = await client.get(f"/api/cards/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["jobId"] == job_id
    assert "cardData" in body
    assert "cards" in body["cardData"]


# ── 자동저장 ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_cards_saves(client, dummy_pdf, mock_card_data):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        upload = await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    job_id = upload.json()["jobId"]

    resp = await client.patch(
        f"/api/cards/{job_id}/data",
        json={"cardData": mock_card_data.model_dump()},
    )
    assert resp.status_code == 200
    assert resp.json()["autoSaveStatus"] == "saved"


@pytest.mark.asyncio
async def test_patch_cards_invalid_schema(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        upload = await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    job_id = upload.json()["jobId"]

    resp = await client.patch(
        f"/api/cards/{job_id}/data",
        json={"cardData": {"invalid": "data"}},
    )
    assert resp.status_code == 422


# ── 프로젝트 목록 / 통계 ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_projects_empty(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json()["projects"] == []


@pytest.mark.asyncio
async def test_projects_stats_empty(client):
    resp = await client.get("/api/projects/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["done"] == 0


@pytest.mark.asyncio
async def test_projects_lists_uploaded(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )

    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    assert len(resp.json()["projects"]) == 1


@pytest.mark.asyncio
async def test_projects_stats_counts(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        for _ in range(3):
            await client.post(
                "/api/upload",
                files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
                data={"card_count": "5"},
            )

    resp = await client.get("/api/projects/stats")
    body = resp.json()
    assert body["total"] == 3
    assert body["draft"] == 3  # PENDING = draft


# ── 내보내기 다운로드 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_download_expired(client):
    resp = await client.get("/api/export/nonexistent-export-id/download")
    assert resp.status_code == 410
    assert resp.json()["detail"]["code"] == "ERR-EXP-004"


@pytest.mark.asyncio
async def test_export_download_returns_zip(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        upload = await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    job_id = upload.json()["jobId"]

    # ZIP 수동 저장
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("card_01.png", b"fakepng")
    zip_bytes = buf.getvalue()

    import uuid
    export_id = str(uuid.uuid4())
    await _db.save_export(export_id, job_id, zip_bytes, "test.zip")

    resp = await client.get(f"/api/export/{export_id}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert zipfile.is_zipfile(io.BytesIO(resp.content))


# ── 카드 이미지 ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_card_image_not_found(client):
    resp = await client.get("/api/cards/nonexistent/image/1")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_card_image_returns_png(client, dummy_pdf):
    with patch("backend.routers.jobs.run_pipeline", new_callable=AsyncMock):
        upload = await client.post(
            "/api/upload",
            files={"file": ("p.pdf", dummy_pdf, "application/pdf")},
            data={"card_count": "5"},
        )
    job_id = upload.json()["jobId"]

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    await _db.save_card_image(job_id, card_num=1, png_bytes=fake_png)

    resp = await client.get(f"/api/cards/{job_id}/image/1")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


# ── CardEditorData bg_color 필드 ──────────────────────────────────────────

def test_card_editor_data_bg_color_default():
    from backend.core.models import CardEditorData, CardMeta, FieldValue, FieldSource, MatchQuality, ClaimType, RiskLevel
    fv = FieldValue(
        value="test", confidence="high",
        match_quality=MatchQuality.EXACT, claim_type=ClaimType.QUALITATIVE,
        source=FieldSource(section="test", page=1), risk_level=RiskLevel.LOW,
    )
    meta = CardMeta(
        org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv,
    )
    data = CardEditorData(meta=meta, cards=[])
    assert data.bg_color == "#111111"


def test_card_editor_data_bg_color_custom():
    from backend.core.models import CardEditorData, CardMeta, FieldValue, FieldSource, MatchQuality, ClaimType, RiskLevel
    fv = FieldValue(
        value="test", confidence="high",
        match_quality=MatchQuality.EXACT, claim_type=ClaimType.QUALITATIVE,
        source=FieldSource(section="test", page=1), risk_level=RiskLevel.LOW,
    )
    meta = CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv)
    data = CardEditorData(meta=meta, cards=[], bg_color="#0A0F1E")
    assert data.bg_color == "#0A0F1E"


# ── 파일명 변경 / 삭제 / 단일 카드 다운로드 ──────────────────────────────────

@pytest.mark.asyncio
async def test_get_cards_includes_filename(client):
    await _db.create_job("j1", "paper.pdf")
    await _db.save_card_data("j1", json.dumps({"cards": []}))
    resp = await client.get("/api/cards/j1")
    assert resp.status_code == 200
    assert resp.json()["filename"] == "paper.pdf"


@pytest.mark.asyncio
async def test_rename_job(client):
    await _db.create_job("j1", "old.pdf")
    resp = await client.patch("/api/jobs/j1", json={"title": "새 이름.pdf"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "새 이름.pdf"
    job = await _db.get_job("j1")
    assert job["title"] == "새 이름.pdf"


@pytest.mark.asyncio
async def test_rename_empty_rejected(client):
    await _db.create_job("j1", "old.pdf")
    resp = await client.patch("/api/jobs/j1", json={"title": "   "})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_rename_missing_job_404(client):
    resp = await client.patch("/api/jobs/nope", json={"title": "x"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_cascade(client):
    await _db.create_job("j1", "p.pdf")
    await _db.save_card_data("j1", json.dumps({"cards": []}))
    resp = await client.delete("/api/jobs/j1")
    assert resp.status_code == 204
    assert await _db.get_job("j1") is None
    assert await _db.get_card_data("j1") is None
    resp2 = await client.delete("/api/jobs/j1")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_download_card_fresh_render(client):
    await _db.create_job("j1", "paper.pdf")
    await _db.save_card_data("j1", json.dumps({"cards": []}))
    fake_png = b"\x89PNG fake-bytes"
    with patch(
        "backend.routers.export._playwright_render_via_url_sync",
        return_value=([fake_png], []),
    ):
        resp = await client.get("/api/cards/j1/download/1")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    cd = resp.headers["content-disposition"]
    assert "attachment" in cd and "paper_01.png" in cd
    assert resp.content == fake_png


@pytest.mark.asyncio
async def test_download_missing_carddata_404(client):
    await _db.create_job("j1", "p.pdf")
    resp = await client.get("/api/cards/j1/download/1")
    assert resp.status_code == 404
