import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import config, db, signing
from backend.main import app


def _key(monkeypatch):
    monkeypatch.setattr(config.settings, "PUBLIC_CARD_URL_SECRET", "test-secret-0123456789")


def test_valid_sig_passes(monkeypatch):
    _key(monkeypatch)
    exp, sig = signing.sign_card("job1", 2)
    assert signing.verify_card("job1", 2, exp, sig) is True


def test_expired_fails(monkeypatch):
    _key(monkeypatch)
    exp, sig = signing.sign_card("job1", 2, ttl_s=-1)   # 이미 만료
    assert signing.verify_card("job1", 2, exp, sig) is False


def test_forged_sig_fails(monkeypatch):
    _key(monkeypatch)
    exp, _ = signing.sign_card("job1", 2)
    assert signing.verify_card("job1", 2, exp, "deadbeef") is False


def test_wrong_card_fails(monkeypatch):
    _key(monkeypatch)
    exp, sig = signing.sign_card("job1", 2)
    assert signing.verify_card("job1", 3, exp, sig) is False   # 다른 카드 번호


def test_dormant_when_secret_empty(monkeypatch):
    # M3: 시크릿 없으면 verify 무조건 False — 빈키 위조 불가
    monkeypatch.setattr(config.settings, "PUBLIC_CARD_URL_SECRET", "")
    assert signing.enabled() is False
    assert signing.verify_card("job1", 2, 9999999999, "anything") is False


def test_to_jpeg_converts_and_downscales():
    # B1: 2160×2700 RGBA PNG → 1080폭 JPEG(알파 제거). Meta 발행 요건 충족 증명.
    import io

    from PIL import Image

    from backend.core import images
    src = Image.new("RGBA", (2160, 2700), (10, 20, 30, 255))
    buf = io.BytesIO()
    src.save(buf, format="PNG")
    out = images.to_jpeg(buf.getvalue(), max_width=1080)
    res = Image.open(io.BytesIO(out))
    assert res.format == "JPEG"
    assert res.width == 1080 and res.height == 1350   # 다운스케일
    assert res.mode == "RGB"                           # 알파 제거


async def test_public_route_rejects_bad_sig(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    _key(monkeypatch)
    await db.migrate()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/deck/j/cards/1/public?exp=9999999999&sig=bad")
        assert r.status_code == 404   # 서명 위조 거부(무인증이지만 sig 필요)
