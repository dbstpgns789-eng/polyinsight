"""무료체험 배관 — 스키마·차감·환불·게이트."""
from __future__ import annotations

import io

import aiosqlite
import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from backend.agents.deck import pipeline as _pipeline
from backend.core import db as _db
from backend.core import plans
from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.core.models import JobStatus
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blobstore"))
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    await _db.migrate()
    yield


async def _mk_user(email: str = "free@test") -> int:
    return await _db.create_user(email, "hash")


@pytest.mark.asyncio
async def test_new_user_defaults_to_free_with_zero_used():
    uid = await _mk_user()
    user = await _db.get_user_by_id(uid)
    assert user["plan"] == "free"
    assert user["free_decks_used"] == 0
    assert user["onboarded_at"] is None


@pytest.mark.asyncio
async def test_consume_free_deck_increments():
    uid = await _mk_user()
    await _db.consume_free_deck(uid)
    user = await _db.get_user_by_id(uid)
    assert user["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_refund_free_deck_decrements_but_never_below_zero():
    uid = await _mk_user()
    await _db.consume_free_deck(uid)
    await _db.refund_free_deck(uid)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0
    # 이중 환불이 음수를 만들면 안 된다 — 무료 횟수가 늘어나는 버그가 된다
    await _db.refund_free_deck(uid)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_paid_user_counter_untouched():
    """유료 유저는 무료 카운터를 소비하지 않는다 (게이트 대상이 아님, no-op이므로 False 반환)."""
    uid = await _mk_user("pro@test")
    await _db.set_plan(uid, "pro")
    assert await _db.consume_free_deck(uid) is False
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_consume_free_deck_returns_false_when_exhausted():
    """상한을 넘으면 소비가 일어나지 않는다 — 카운터도 안 오른다(check-then-act 레이스 차단)."""
    uid = await _mk_user("exhaust@test")
    assert await _db.consume_free_deck(uid) is True
    assert await _db.consume_free_deck(uid) is False
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_mark_onboarded_is_idempotent():
    uid = await _mk_user()
    await _db.mark_onboarded(uid)
    first = (await _db.get_user_by_id(uid))["onboarded_at"]
    assert first is not None
    await _db.mark_onboarded(uid)
    assert (await _db.get_user_by_id(uid))["onboarded_at"] == first


async def _seed_old_users_schema(db_path: str, email: str) -> None:
    """구스키마(plan/free_decks_used/onboarded_at 없는 users) 직접 재현.
    migrate()는 CREATE TABLE IF NOT EXISTS라서 테이블이 아예 없어야 ALTER 백필 경로를 탄다
    (fixture의 선행 migrate()가 이미 신스키마로 만들어버리므로 별도 DB 파일에 재현한다)."""
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, "hash", "2020-01-01T00:00:00"),
        )
        await conn.commit()


@pytest.mark.asyncio
async def test_migrate_backfills_existing_users_to_lab_and_is_idempotent(tmp_path, monkeypatch):
    """구스키마 유저(게이트 도입 전부터 있던 계정) = plan='lab'(면제)+onboarded_at 백필 대상.
    재migrate해도 onboarded_at을 덮어쓰지 않아야 하고, 백필 후 신규유저는 여전히 free/None이어야 한다."""
    legacy_db = str(tmp_path / "legacy.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{legacy_db}")
    await _seed_old_users_schema(legacy_db, "legacy@test")

    await _db.migrate()
    legacy = await _db.get_user_by_id(1)
    assert legacy["plan"] == "lab"
    assert legacy["onboarded_at"] is not None

    # 재migrate — 멱등: onboarded_at 값이 안 바뀐다
    await _db.migrate()
    legacy_again = await _db.get_user_by_id(1)
    assert legacy_again["onboarded_at"] == legacy["onboarded_at"]

    # 백필 후 신규 유저는 DDL DEFAULT 경로 — 여전히 free/None (백필과 충돌 없음)
    new_uid = await _mk_user("newafterbackfill@test")
    new_user = await _db.get_user_by_id(new_uid)
    assert new_user["plan"] == "free"
    assert new_user["onboarded_at"] is None


@pytest.mark.asyncio
async def test_migrate_backfill_survives_crash_between_alter_and_update(tmp_path, monkeypatch):
    """ALTER 직후~UPDATE 커밋 이전 크래시를 재현 — BEGIN으로 묶었으니 둘 다(컬럼까지) 롤백되고,
    재기동한 migrate()가 처음부터 다시 정상 백필해야 한다(영구 스킵 없음)."""
    crash_db = str(tmp_path / "crash.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{crash_db}")
    await _seed_old_users_schema(crash_db, "crashvictim@test")

    # migrate()의 BEGIN+ALTER+UPDATE를 직접 재현하되 commit 없이 close.
    # SQLite는 crash-safe라 pending 트랜잭션 중 close(=강제종료 동치)는 통째로 롤백된다.
    conn = await aiosqlite.connect(crash_db)
    await conn.execute("BEGIN")
    await conn.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
    await conn.execute("UPDATE users SET plan = 'lab'")
    await conn.close()

    # 크래시 직후: 컬럼 자체가 없어야 한다 — UPDATE만 유실되는 게 아니라 ALTER까지 롤백됨.
    # (이게 안 되면 BEGIN 감싸기가 무의미: 컬럼만 남아 다음 migrate()가 영원히 스킵한다)
    async with aiosqlite.connect(crash_db) as check_conn:
        async with check_conn.execute("PRAGMA table_info(users)") as cur:
            cols_after_crash = [row[1] for row in await cur.fetchall()]
    assert "plan" not in cols_after_crash

    # 재기동 — migrate()가 스킵하지 않고 처음부터 다시 정상 백필해야 한다
    await _db.migrate()
    user = await _db.get_user_by_id(1)
    assert user["plan"] == "lab"


@pytest.mark.asyncio
async def test_migrate_backfill_keeps_real_external_users_free(tmp_path, monkeypatch):
    """운영 DB엔 게이트 도입 전 가입한 진짜 외부 유저(hoik0822@gmail.com 등)가 섞여 있었다
    (로컬엔 없어 안 보였음) — '기존 유저=전원 내부' 전제가 운영에서만 깨진 사례.
    이 두 이메일은 무료체험 정상 대상이라 free로 남아야 하고, 나머지 내부 계정은 lab 그대로여야 한다."""
    prod_db = str(tmp_path / "prod.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{prod_db}")
    await _seed_old_users_schema(prod_db, "admin@internal")
    async with aiosqlite.connect(prod_db) as conn:
        await conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            ("hoik0822@gmail.com", "hash", "2026-07-14T00:00:00"),
        )
        await conn.commit()

    await _db.migrate()

    internal = await _db.get_user_by_email("admin@internal")
    external = await _db.get_user_by_email("hoik0822@gmail.com")
    assert internal["plan"] == "lab"
    assert external["plan"] == "free"


# ── 게이트 판정 ────────────────────────────────────────────────────────────


def test_free_user_with_zero_used_can_author_but_cannot_export():
    u = {"id": 1, "plan": "free", "free_decks_used": 0}
    assert plans.can_author(u) is True
    assert plans.can_export(u) is False


def test_free_user_who_used_their_deck_cannot_author():
    u = {"id": 1, "plan": "free", "free_decks_used": 1}
    assert plans.can_author(u) is False


def test_paid_user_can_do_both():
    for plan in ("pro", "lab"):
        u = {"id": 1, "plan": plan, "free_decks_used": 99}
        assert plans.can_author(u) is True
        assert plans.can_export(u) is True


def test_render_service_user_is_exempt():
    """X-Render-Token 서비스 유저는 plan 키 자체가 없다 — KeyError 나면 렌더가 죽는다."""
    u = {"id": 0, "email": "__render__", "role": "service"}
    assert plans.can_author(u) is True
    assert plans.can_export(u) is True


def test_missing_plan_key_defaults_to_free():
    """DB row가 아닌 dict가 들어와도 터지지 않고 보수적으로 free 취급."""
    u = {"id": 1}
    assert plans.can_export(u) is False


def test_require_can_export_raises_402_with_plan_code():
    u = {"id": 1, "plan": "free", "free_decks_used": 1}
    with pytest.raises(HTTPException) as ei:
        plans.require_can_export(u)
    assert ei.value.status_code == 402
    assert ei.value.detail["code"] == "ERR-PLAN-EXPORT"


def test_require_can_author_raises_402_with_plan_code():
    u = {"id": 1, "plan": "free", "free_decks_used": 1}
    with pytest.raises(HTTPException) as ei:
        plans.require_can_author(u)
    assert ei.value.status_code == 402
    assert ei.value.detail["code"] == "ERR-PLAN-AUTHOR"


def test_require_passes_silently_when_allowed():
    u = {"id": 1, "plan": "pro", "free_decks_used": 0}
    plans.require_can_author(u)   # 예외 없이 통과해야 함
    plans.require_can_export(u)


def test_gate_error_factories_match_require_responses():
    """읽기 판정과 원자적 소비 실패가 같은 402 응답을 내야 한다.

    Task 3에서 라우트가 두 경로로 같은 벽을 만든다 — 프론트가 한 가지 분기만
    다루려면 code/status가 동일해야 한다.
    """
    err = plans.author_gate_error()
    assert err.status_code == 402
    assert err.detail["code"] == "ERR-PLAN-AUTHOR"

    exp = plans.export_gate_error()
    assert exp.status_code == 402
    assert exp.detail["code"] == "ERR-PLAN-EXPORT"


def test_should_consume_free_deck_service_role_false():
    """plan 키가 없는 서비스 유저도 can_author와 같은 면제를 받아야 한다.

    호출부가 plan_of()만 보면 plan 키 없는 서비스 유저가 "free"로 폴백돼
    소비 블록에서 잘못 402를 맞는다 — should_consume_free_deck이 그 불변식을 보존한다.
    """
    u = {"id": 0, "email": "__render__", "role": "service"}
    assert plans.should_consume_free_deck(u) is False


def test_should_consume_free_deck_free_user_true():
    u = {"id": 1, "plan": "free", "free_decks_used": 0}
    assert plans.should_consume_free_deck(u) is True


def test_should_consume_free_deck_paid_user_false():
    for plan in ("pro", "lab"):
        u = {"id": 1, "plan": plan, "free_decks_used": 0}
        assert plans.should_consume_free_deck(u) is False


# ── 생성 게이트 (HTTP) ─────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _as_user(user: dict):
    """이 유저로 로그인된 것처럼 만든다."""
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _fake_pdf() -> tuple[str, io.BytesIO, str]:
    return ("p.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")


@pytest.mark.asyncio
async def test_free_user_first_upload_accepted(client, monkeypatch):
    uid = await _mk_user("first@test")
    user = dict(await _db.get_user_by_id(uid))
    _as_user(user)
    # 파이프라인은 돌리지 않는다 — 게이트만 검증
    monkeypatch.setattr(
        "backend.routers.deck.run_authoring_pipeline",
        lambda *a, **k: None,
    )
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 202
    # 선차감됐나
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_free_user_second_upload_blocked_with_402(client):
    uid = await _mk_user("second@test")
    await _db.consume_free_deck(uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ERR-PLAN-AUTHOR"


@pytest.mark.asyncio
async def test_paid_user_upload_does_not_consume_free_counter(client, monkeypatch):
    """유료 유저는 무료 카운터를 건드리지 않는다(no-op 반환을 실패로 오해하면 안 됨)."""
    uid = await _mk_user("paidupload@test")
    await _db.set_plan(uid, "pro")
    _as_user(dict(await _db.get_user_by_id(uid)))
    monkeypatch.setattr(
        "backend.routers.deck.run_authoring_pipeline",
        lambda *a, **k: None,
    )
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 202
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_race_loser_gets_same_402_as_read_gate(client, monkeypatch):
    """★읽기 판정을 통과했어도 원자적 소비에서 지면 같은 402를 받아야 한다.

    스냅샷(free_decks_used=0)으로 요청을 만들되 DB는 이미 소진 상태로 만들어
    레이스에서 진 상황을 재현한다. 프론트가 한 가지 분기만 다루려면 code가 같아야 한다.
    """
    uid = await _mk_user("racer@test")
    stale = dict(await _db.get_user_by_id(uid))   # free_decks_used = 0 스냅샷
    await _db.consume_free_deck(uid)              # 그 사이 다른 요청이 먼저 소비
    _as_user(stale)
    monkeypatch.setattr(
        "backend.routers.deck.run_authoring_pipeline",
        lambda *a, **k: None,
    )
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ERR-PLAN-AUTHOR"
    # 카운터가 2가 되면 안 된다(뚫린 것)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_service_role_upload_is_not_gated(client, monkeypatch):
    """★X-Render-Token 서비스 유저는 plan 키가 없다 — 소비 블록에서 402 맞으면 안 된다.

    can_author는 면제하는데 소비 블록만 안 하면 내부 렌더 경로가 죽는다.
    """
    _as_user({"id": 0, "email": "__render__", "role": "service"})
    monkeypatch.setattr(
        "backend.routers.deck.run_authoring_pipeline",
        lambda *a, **k: None,
    )
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code != 402


# ── 실패 환불 ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_failed_pipeline_refunds_the_free_deck():
    """실패로 아하를 못 본 유저가 영구히 막히면 안 된다."""
    uid = await _mk_user("fail@test")
    await _db.consume_free_deck(uid)
    job_id = "job-fail"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40)

    await _pipeline._log_done(job_id, uid, 0.0, 7)

    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_successful_pipeline_does_not_refund():
    uid = await _mk_user("ok@test")
    await _db.consume_free_deck(uid)
    job_id = "job-ok"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.update_job(job_id, status=JobStatus.DONE, stage="S8", progress=100)

    await _pipeline._log_done(job_id, uid, 0.0, 7)

    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 1


@pytest.mark.asyncio
async def test_refund_does_not_touch_paid_user():
    """유료 유저는 애초에 소비하지 않았으므로 환불도 no-op이어야 한다."""
    uid = await _mk_user("paidfail@test")
    await _db.set_plan(uid, "pro")
    job_id = "job-paidfail"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40)

    await _pipeline._log_done(job_id, uid, 0.0, 7)

    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_refund_failure_does_not_swallow_completion_event(monkeypatch):
    """★환불이 터져도 비용 추적 이벤트는 남아야 한다."""
    uid = await _mk_user("refundboom@test")
    await _db.consume_free_deck(uid)
    job_id = "job-boom"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40)

    calls = []

    async def _boom(_uid):
        calls.append(_uid)
        raise RuntimeError("db locked")

    monkeypatch.setattr(_db, "refund_free_deck", _boom)

    # 예외가 새어나오면 안 된다
    await _pipeline._log_done(job_id, uid, 0.0, 7)

    # 패치가 실제로 먹었는지 확인 — 안 먹으면 이 테스트는 아무것도 검증 못 한다
    assert calls == [uid]
    # 환불이 실패했으니 free_decks_used는 원복되지 않고 그대로 1이어야 한다
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 1
    # 완료 이벤트(비용 추적)는 그래도 기록됐어야 한다
    events = await _db.list_events(limit=10)
    matching = [
        e for e in events
        if e["job_id"] == job_id and e["event_type"] == "deck_pipeline_complete"
    ]
    assert len(matching) == 1


# ── export 게이트 ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_free_user_export_blocked_with_402(client):
    uid = await _mk_user("noexport@test")
    job_id = "job-x"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/export")
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ERR-PLAN-EXPORT"


@pytest.mark.asyncio
async def test_free_user_single_card_download_blocked(client):
    """★우회 구멍 — 단일 카드 첨부 다운로드도 막혀야 한다."""
    uid = await _mk_user("nocard@test")
    job_id = "job-y"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get(f"/api/cards/{job_id}/download/1")
    assert r.status_code == 402


@pytest.mark.asyncio
async def test_free_user_can_still_view_card_inline(client):
    """★순수잠금 = 다 보이되 못 가져감. 뷰어 표시 경로는 402가 아니어야 한다.

    이미지가 아직 없으니 404가 정상 — 중요한 건 402가 아니라는 것.
    여기에 게이트를 걸면 무료 유저 뷰어가 빈 화면이 되고 아하가 죽는다.
    """
    uid = await _mk_user("canview@test")
    job_id = "job-z"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get(f"/api/cards/{job_id}/image/1")
    assert r.status_code != 402


@pytest.mark.asyncio
async def test_free_user_can_still_view_deck_card(client):
    """★뷰어 카드 피드도 열려 있어야 한다(get_deck_card)."""
    uid = await _mk_user("canviewdeck@test")
    job_id = "job-zz"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get(f"/api/deck/{job_id}/cards/1")
    assert r.status_code != 402


@pytest.mark.asyncio
async def test_paid_user_export_not_blocked_by_plan(client):
    """유료는 플랜 게이트를 통과한다(그 뒤 단계에서 404가 나는 건 무방)."""
    uid = await _mk_user("paidexp@test")
    await _db.set_plan(uid, "pro")
    job_id = "job-p"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/export")
    assert r.status_code != 402


@pytest.mark.asyncio
async def test_service_role_export_not_gated(client):
    """★내부 렌더(X-Render-Token)는 면제 — 자가치유 재렌더가 죽으면 안 된다."""
    _as_user({"id": 0, "email": "__render__", "role": "service"})
    r = await client.get("/api/cards/job-svc/download/1")
    assert r.status_code != 402


# ── /me 확장 · 온보딩 ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_me_exposes_plan_state(client):
    uid = await _mk_user("me@test")
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "free"
    assert body["freeDecksUsed"] == 0
    assert body["freeDeckLimit"] == 1
    assert body["canAuthor"] is True
    assert body["canExport"] is False
    assert body["onboarded"] is False


@pytest.mark.asyncio
async def test_me_keeps_existing_fields(client):
    """기존 프론트 3곳이 email/role/emailVerified를 쓴다 — 깨뜨리면 안 된다."""
    uid = await _mk_user("keep@test")
    _as_user(dict(await _db.get_user_by_id(uid)))

    body = (await client.get("/api/auth/me")).json()
    assert body["email"] == "keep@test"
    assert body["role"] == "user"
    assert body["emailVerified"] is False


@pytest.mark.asyncio
async def test_me_reflects_exhausted_free_user(client):
    uid = await _mk_user("used@test")
    await _db.consume_free_deck(uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    body = (await client.get("/api/auth/me")).json()
    assert body["freeDecksUsed"] == 1
    assert body["canAuthor"] is False
    assert body["canExport"] is False


@pytest.mark.asyncio
async def test_me_paid_user_can_export(client):
    uid = await _mk_user("mepaid@test")
    await _db.set_plan(uid, "pro")
    _as_user(dict(await _db.get_user_by_id(uid)))

    body = (await client.get("/api/auth/me")).json()
    assert body["plan"] == "pro"
    assert body["canAuthor"] is True
    assert body["canExport"] is True


@pytest.mark.asyncio
async def test_post_onboarded_marks_and_is_idempotent(client):
    uid = await _mk_user("onb@test")
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post("/api/auth/onboarded")
    assert r.status_code == 200
    first = (await _db.get_user_by_id(uid))["onboarded_at"]
    assert first is not None

    r2 = await client.post("/api/auth/onboarded")
    assert r2.status_code == 200
    # 멱등 — 처음 시각을 유지한다
    assert (await _db.get_user_by_id(uid))["onboarded_at"] == first


@pytest.mark.asyncio
async def test_me_onboarded_true_after_marking(client):
    uid = await _mk_user("onbflag@test")
    await _db.mark_onboarded(uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    assert (await client.get("/api/auth/me")).json()["onboarded"] is True
