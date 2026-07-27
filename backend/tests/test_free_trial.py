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
async def test_migrate_backfill_maps_prod_users_by_identity(tmp_path, monkeypatch):
    """운영 DB엔 게이트 도입 전 가입한 유저가 신원별로 섞여 있었다(로컬엔 없어 안 보였음) —
    '기존 유저=전원 내부' 전제가 운영에서만 깨진 사례. 신원 매핑(2026-07-20 확정):
      - hoik0822@gmail.com = 박사님·동업자 → lab(벽 면제)
      - dhkdals14@gmail.com = 지인 → free(정상 무료체험, 벽 적용)
      - 나머지 내부 계정(admin 등) → lab 그대로."""
    prod_db = str(tmp_path / "prod.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{prod_db}")
    await _seed_old_users_schema(prod_db, "admin@internal")
    async with aiosqlite.connect(prod_db) as conn:
        await conn.executemany(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            [
                ("hoik0822@gmail.com", "hash", "2026-07-14T00:00:00"),   # 박사님·동업자
                ("dhkdals14@gmail.com", "hash", "2026-07-16T00:00:00"),  # 지인
            ],
        )
        await conn.commit()

    await _db.migrate()

    assert (await _db.get_user_by_email("admin@internal"))["plan"] == "lab"
    assert (await _db.get_user_by_email("hoik0822@gmail.com"))["plan"] == "lab"   # 동업자=면제
    assert (await _db.get_user_by_email("dhkdals14@gmail.com"))["plan"] == "free"  # 지인=벽 적용


# ── 게이트 판정 ────────────────────────────────────────────────────────────


def test_free_user_with_zero_used_can_author_but_cannot_export():
    u = {"id": 1, "plan": "free", "free_decks_used": 0}
    assert plans.can_author(u) is True
    assert plans.can_export(u) is False


def test_free_user_who_used_their_deck_cannot_author():
    u = {"id": 1, "plan": "free", "free_decks_used": 1}
    assert plans.can_author(u) is False


def test_paid_user_can_do_both():
    # lab(면제)은 크레딧 없이도 무제한
    lab = {"id": 1, "plan": "lab", "free_decks_used": 99}
    assert plans.can_author(lab) is True
    assert plans.can_export(lab) is True
    # pro는 크레딧이 있어야 생성(B1). export는 크레딧 무관(plan 게이트만).
    pro_rich = {"id": 2, "plan": "pro", "credits": plans.DECK_COST}
    assert plans.can_author(pro_rich) is True
    assert plans.can_export(pro_rich) is True
    pro_poor = {"id": 2, "plan": "pro", "credits": 0}
    assert plans.can_author(pro_poor) is False   # 잔액 0 → 생성 불가
    assert plans.can_export(pro_poor) is True     # export는 여전히 가능


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
    u = {"id": 1, "plan": "pro", "free_decks_used": 0, "credits": plans.DECK_COST}
    plans.require_can_author(u)   # 잔액 충분 → 예외 없이 통과
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
    await _db.add_credits(uid, plans.DECK_COST)   # 유료(pro)+크레딧 (B1: pro도 잔액 필요)
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


# ── AI 디자이너 게이트 (자연어 편집 = 유료, 2026-07-22) ──────────────────────


def test_free_user_cannot_use_ai_designer():
    u = {"id": 1, "plan": "free", "free_decks_used": 0}
    assert plans.can_use_ai_designer(u) is False


def test_paid_user_can_use_ai_designer():
    for plan in ("pro", "lab"):
        u = {"id": 1, "plan": plan, "free_decks_used": 0}
        assert plans.can_use_ai_designer(u) is True


def test_service_role_can_use_ai_designer():
    """내부 렌더 서비스는 plan 키가 없다 — 면제(KeyError 나면 안 됨)."""
    u = {"id": 0, "email": "__render__", "role": "service"}
    assert plans.can_use_ai_designer(u) is True


def test_require_can_ai_designer_raises_402_with_plan_code():
    u = {"id": 1, "plan": "free", "free_decks_used": 0}
    with pytest.raises(HTTPException) as ei:
        plans.require_can_ai_designer(u)
    assert ei.value.status_code == 402
    assert ei.value.detail["code"] == "ERR-PLAN-AI-DESIGNER"


@pytest.mark.asyncio
async def test_free_user_nlpatch_blocked_with_402(client):
    """★무료는 AI 디자이너(자연어 편집) 불가 — 호출마다 LLM 원가가 새는 구멍.
    게이트는 덱 조회·LLM 호출 앞에서 막아 지출을 원천 차단한다."""
    uid = await _mk_user("noai@test")
    job_id = "job-ai"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/nlpatch", json={"instruction": "제목 키워"})
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ERR-PLAN-AI-DESIGNER"


@pytest.mark.asyncio
async def test_free_user_nlpatch_propose_blocked_with_402(client):
    """★propose(미커밋 제안)도 LLM을 태우므로 같이 막힌다."""
    uid = await _mk_user("noaipropose@test")
    job_id = "job-aip"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(
        f"/api/deck/{job_id}/nlpatch/propose",
        json={"instruction": "제목 키워", "html": "<div data-screen-label='1'>x</div>"},
    )
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ERR-PLAN-AI-DESIGNER"


@pytest.mark.asyncio
async def test_paid_user_nlpatch_not_blocked_by_plan(client):
    """유료는 플랜 게이트를 통과한다(덱이 없어 뒤에서 404 나는 건 무방 — LLM은 안 탄다)."""
    uid = await _mk_user("paidai@test")
    await _db.add_credits(uid, plans.DECK_COST)   # 유료(pro)+크레딧 (B1: AI편집도 잔액 필요)
    job_id = "job-paidai"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/nlpatch", json={"instruction": "제목 키워"})
    assert r.status_code != 402


@pytest.mark.asyncio
async def test_ai_designer_gate_hit_is_logged(client):
    """벽 히트가 기록돼야 'AI 디자이너 원해서 벽 맞음'을 전환 데이터에서 판정할 수 있다."""
    uid = await _mk_user("aigatelog@test")
    job_id = "job-ailog"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/nlpatch", json={"instruction": "x"})
    assert r.status_code == 402

    evts = [e for e in await _db.list_events(limit=50) if e["event_type"] == "plan_gate_hit"]
    assert len(evts) == 1
    assert evts[0]["payload"]["kind"] == "ai_designer"


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
    assert body["credits"] == 0


@pytest.mark.asyncio
async def test_me_exposes_credit_balance(client):
    """충전 후 /me가 잔액을 노출한다(P1-2 위젯이 읽을 자리)."""
    uid = await _mk_user("mecred@test")
    await _db.add_credits(uid, 30)
    _as_user(dict(await _db.get_user_by_id(uid)))
    body = (await client.get("/api/auth/me")).json()
    assert body["credits"] == 30
    assert body["plan"] == "pro"


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
    await _db.add_credits(uid, plans.DECK_COST)   # 유료(pro)+크레딧 (B1: canAuthor는 잔액 필요)
    _as_user(dict(await _db.get_user_by_id(uid)))

    body = (await client.get("/api/auth/me")).json()
    assert body["plan"] == "pro"
    assert body["canAuthor"] is True
    assert body["canExport"] is True


# ── 크레딧 차감 라우터 (B1 Step 3) ─────────────────────────────────────────
async def _mk_deck(uid: int, job_id: str = "d1") -> str:
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.save_authored_deck(job_id, "<div data-screen-label='1'>x</div>", "{}", 1, "paper")
    return job_id


@pytest.mark.asyncio
async def test_pro_upload_consumes_deck_cost_and_stamps_job(client, monkeypatch):
    uid = await _mk_user("proupload@test")
    await _db.add_credits(uid, plans.DECK_COST)             # 유료 + 정확히 1덱분
    _as_user(dict(await _db.get_user_by_id(uid)))
    captured: dict = {}
    monkeypatch.setattr("backend.routers.deck.run_authoring_pipeline",
                        lambda job_id, *a, **k: captured.update(job_id=job_id))
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 202
    assert await _db.get_credits(uid) == 0                  # DECK_COST 차감
    job = await _db.get_job(captured["job_id"])
    assert job["charged_credits"] == plans.DECK_COST        # 각인(환불 근거)


@pytest.mark.asyncio
async def test_pro_upload_insufficient_credits_402_no_deduct(client, monkeypatch):
    uid = await _mk_user("poorpro@test")
    await _db.add_credits(uid, plans.DECK_COST - 1)         # 부족
    _as_user(dict(await _db.get_user_by_id(uid)))
    monkeypatch.setattr("backend.routers.deck.run_authoring_pipeline", lambda *a, **k: None)
    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "ERR-CREDIT-LOW"
    assert await _db.get_credits(uid) == plans.DECK_COST - 1  # 불변(선차감 롤백)


@pytest.mark.asyncio
async def test_pro_nlpatch_no_change_does_not_charge(client, monkeypatch):
    """적용 0건이면 무과금(스펙 §11-1) — LLM 돌아도 바뀐 게 없으면 크레딧 불변."""
    uid = await _mk_user("edit0@test")
    await _db.add_credits(uid, plans.AIEDIT_COST)
    job_id = await _mk_deck(uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    async def _noop(*a, **k):
        return ("<div data-screen-label='1'>변화없음</div>", 0, "적용할 게 없었어요")
    monkeypatch.setattr("backend.routers.deck.apply_nl_patch", _noop)
    r = await client.post(f"/api/deck/{job_id}/nlpatch", json={"instruction": "x"})
    assert r.status_code == 200
    assert r.json()["applied"] == 0
    assert await _db.get_credits(uid) == plans.AIEDIT_COST   # 무과금


@pytest.mark.asyncio
async def test_pro_nlpatch_success_charges_aiedit(client, monkeypatch):
    uid = await _mk_user("editok@test")
    await _db.add_credits(uid, plans.AIEDIT_COST)
    job_id = await _mk_deck(uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    async def _good(*a, **k):
        return ("<div data-screen-label='1'>고침</div>", 1, "고쳤어요")
    async def _fake_persist(job_id, html, revision_source=None):
        return {"cardCount": 1, "pngVersion": 1}
    monkeypatch.setattr("backend.routers.deck.apply_nl_patch", _good)
    monkeypatch.setattr("backend.routers.deck.persist_edited_deck", _fake_persist)
    r = await client.post(f"/api/deck/{job_id}/nlpatch", json={"instruction": "x"})
    assert r.status_code == 200
    assert await _db.get_credits(uid) == 0                   # AIEDIT_COST 차감


@pytest.mark.asyncio
async def test_pro_propose_no_change_does_not_charge(client, monkeypatch):
    """propose(라이브 경로)도 적용 0건이면 무과금(스펙 §11-1)."""
    uid = await _mk_user("prop0@test")
    await _db.add_credits(uid, plans.AIEDIT_COST)
    job_id = await _mk_deck(uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    async def _noop(*a, **k):
        return ("<div data-screen-label='1'>y</div>", 0, "무변경")
    monkeypatch.setattr("backend.routers.deck.apply_nl_patch", _noop)
    r = await client.post(f"/api/deck/{job_id}/nlpatch/propose",
                          json={"instruction": "x", "html": "<div data-screen-label='1'>y</div>"})
    assert r.status_code == 200
    assert r.json()["applied"] == 0
    assert await _db.get_credits(uid) == plans.AIEDIT_COST


@pytest.mark.asyncio
async def test_log_done_refunds_credits_on_error():
    """§13-① 정상 실행 중 ERROR → _log_done이 각인 크레딧 환불(recover와 같은 멱등 훅)."""
    uid = await _mk_user("logdone@test")
    await _db.add_credits(uid, plans.DECK_COST)
    job_id = "job-logdone"
    await _db.create_job(job_id, "t", uid)
    await _db.consume_credits_for_job(uid, job_id, plans.DECK_COST)
    await _db.update_job(job_id, "ERROR")
    await _pipeline._log_done(job_id, uid, 0.0, 1)
    assert await _db.get_credits(uid) == plans.DECK_COST     # 복구


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


# ── 인라인 해상도 차등 ─────────────────────────────────────────────────────
from PIL import Image


def _png_size(raw: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(raw)).size


async def _seed_card(job_id: str, uid: int) -> tuple[int, int]:
    """★실제 파이프라인은 레티나 2배로 저장한다(deck_renderer scale=2) — 2160×2700."""
    buf = io.BytesIO()
    Image.new("RGB", (2160, 2700), (20, 120, 90)).save(buf, format="PNG")
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.save_card_image(job_id, card_num=1, png_bytes=buf.getvalue())
    return (2160, 2700)


@pytest.mark.asyncio
async def test_free_user_gets_downscaled_inline_card(client):
    """★무료 유저는 화면용 축소본을 받는다 — 원본이 나가면 export 벽이 무의미해진다.

    절대값으로 단언한다(튜플 사전식 비교로는 높이 축소를 놓친다 — (540, 9999) < (1080, 1350)도 True).
    """
    uid = await _mk_user("smallpng@test")
    await _seed_card("job-small", uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get("/api/cards/job-small/image/1")
    assert r.status_code == 200
    # 무료 = 인스타 규격(1080)의 절반 — 화면에선 읽히고 게시엔 부족
    assert _png_size(r.content) == (540, 675)


@pytest.mark.asyncio
async def test_paid_user_gets_original_inline_card(client):
    uid = await _mk_user("bigpng@test")
    await _db.set_plan(uid, "pro")
    await _seed_card("job-big", uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get("/api/cards/job-big/image/1")
    assert _png_size(r.content) == (2160, 2700)


@pytest.mark.asyncio
async def test_render_service_user_gets_original(client):
    """★렌더 서비스 유저가 축소본을 받으면 산출물 품질이 통째로 망가진다."""
    uid = await _mk_user("svc@test")
    await _seed_card("job-svc", uid)
    _as_user({"id": uid, "email": "__render__", "role": "service"})

    r = await client.get("/api/cards/job-svc/image/1")
    assert _png_size(r.content) == (2160, 2700)


def test_downscale_is_absolute_not_relative():
    """★원본 해상도가 바뀌어도 미리보기 크기는 고정이어야 한다.

    상대 배율이면 렌더 scale이 바뀔 때 미리보기가 조용히 커진다(실제로 그렇게 뚫렸다:
    scale=2 렌더 원본 2160×2700을 0.5배 축소하면 정확히 인스타 게시 규격 1080×1350이 나옴).
    """
    from backend.core import images as iu

    def _png(w, h):
        b = io.BytesIO()
        Image.new("RGB", (w, h)).save(b, format="PNG")
        return b.getvalue()

    assert _png_size(iu.downscale_png(_png(2160, 2700))) == (540, 675)
    assert _png_size(iu.downscale_png(_png(1080, 1350))) == (540, 675)
    # 이미 작으면 그대로 둔다(확대 금지)
    assert _png_size(iu.downscale_png(_png(400, 500))) == (400, 500)


# ── 퍼널 이벤트 ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_export_gate_hit_is_logged(client):
    """★벽 히트가 기록되지 않으면 T1 트리거(벽 히트 N명)를 판정할 수 없다."""
    uid = await _mk_user("gatelog@test")
    job_id = "job-log"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/export")
    assert r.status_code == 402

    evts = [e for e in await _db.list_events(limit=50) if e["event_type"] == "plan_gate_hit"]
    assert len(evts) == 1
    assert evts[0]["user_id"] == uid
    assert evts[0]["payload"]["kind"] == "export"


@pytest.mark.asyncio
async def test_author_gate_hit_is_logged(client):
    uid = await _mk_user("gatelog2@test")
    await _db.consume_free_deck(uid, 1)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 402

    evts = [e for e in await _db.list_events(limit=50) if e["event_type"] == "plan_gate_hit"]
    assert evts[0]["payload"]["kind"] == "author"


@pytest.mark.asyncio
async def test_logging_failure_does_not_break_the_response(client, monkeypatch):
    """로깅이 죽어도 402는 정상적으로 나가야 한다 — 계측이 제품을 막으면 안 된다."""
    uid = await _mk_user("logfail@test")
    job_id = "job-lf"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    async def _boom(*a, **k):
        raise RuntimeError("events table gone")

    monkeypatch.setattr(_db, "log_event", _boom)
    r = await client.post(f"/api/deck/{job_id}/export")
    assert r.status_code == 402


@pytest.mark.asyncio
async def test_plain_http_errors_are_not_logged_as_gate_hits(client):
    """★PlanGateError 핸들러가 일반 HTTPException(404 등)을 가로채면 안 된다.

    핸들러를 HTTPException 전체에 걸면 모든 에러가 plan_gate_hit로 기록된다.
    """
    uid = await _mk_user("notgate@test")
    _as_user(dict(await _db.get_user_by_id(uid)))

    # 존재하지 않는 잡 → 404 (플랜 벽 아님)
    r = await client.get("/api/deck/does-not-exist-xyz")
    assert r.status_code == 404

    evts = [e for e in await _db.list_events(limit=50) if e["event_type"] == "plan_gate_hit"]
    assert len(evts) == 0


# ── 스톡 자산 URL 임포트 (P0-4) ────────────────────────────────────────────
import httpx as _httpx


def _tiny_png() -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (4, 4), (10, 120, 90)).save(b, format="PNG")
    return b.getvalue()


class _FakeResp:
    def __init__(self, content: bytes, ctype: str):
        self.content = content
        self.headers = {"content-type": ctype}

    def raise_for_status(self):
        pass


def _fake_httpx(content: bytes, ctype: str):
    class _FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, **k): return _FakeResp(content, ctype)
    return _FakeClient


@pytest.mark.asyncio
async def test_import_stock_asset_saves_deck_asset(client, monkeypatch):
    """스톡 URL을 서버가 받아 deck_asset으로 저장 → {assetId, url}. 렌더 인라인용 소유 자산."""
    uid = await _mk_user("stock@test")
    job_id = "job-stock"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    monkeypatch.setattr(_httpx, "AsyncClient", _fake_httpx(_tiny_png(), "image/png"))

    r = await client.post(f"/api/deck/{job_id}/assets/from-url",
                          json={"url": "https://images.pexels.com/photos/1/x.jpg", "source_type": "stock-pexels"})
    assert r.status_code == 201
    asset_id = r.json()["assetId"]
    asset = await _db.get_deck_asset(job_id, asset_id)
    assert asset is not None and asset["bytes"] == _tiny_png()


@pytest.mark.asyncio
async def test_import_stock_rejects_ssrf_host(client, monkeypatch):
    """★SSRF — allowlist 밖 호스트(내부/사설)는 fetch 전에 400. 서버가 내부로 요청 못 감."""
    uid = await _mk_user("ssrf@test")
    job_id = "job-ssrf"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    called = []

    class _Boom:
        def __init__(self, *a, **k): called.append("init")
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): called.append("get"); return _FakeResp(b"x", "image/png")

    monkeypatch.setattr(_httpx, "AsyncClient", _Boom)

    r = await client.post(f"/api/deck/{job_id}/assets/from-url",
                          json={"url": "http://localhost:8000/api/auth/me"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "ERR-IMG-005"
    assert called == []   # fetch 자체를 안 함


@pytest.mark.asyncio
async def test_import_stock_rejects_non_image(client, monkeypatch):
    """이미지 아닌 응답(text/html)은 거부 — 임의 파일 임포트 차단."""
    uid = await _mk_user("badmime@test")
    job_id = "job-bm"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))
    monkeypatch.setattr(_httpx, "AsyncClient", _fake_httpx(b"<html>", "text/html"))

    r = await client.post(f"/api/deck/{job_id}/assets/from-url",
                          json={"url": "https://images.unsplash.com/photo-1/x"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "ERR-IMG-001"
