# 인스타그램 자동 발행 슬라이스 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 완성된 논문 카드 덱 한 세트를 앱이 유저의 인스타그램 비즈니스 계정에 캐러셀로 직접 발행한다 (Phase B 최소 슬라이스).

**Architecture:** Instagram Login(신규 API, `graph.instagram.com`). 유저가 IG 계정 연동(OAuth) → long-lived 토큰을 **암호화 저장** → 발행 시 카드 PNG를 **서명된 공개 URL**로 노출 → Graph API 캐러셀 발행 → 크레딧 차감. 기존 수동 발행(캡션복사+다운)은 폴백으로 존치. 검증은 코드가(fidelity 해자), 저작은 AI가 — 이 슬라이스는 배관만.

**Tech Stack:** FastAPI · aiosqlite · httpx · `cryptography`(Fernet, 신규 dep) · Playwright(기존 렌더) · Next.js/React 프론트.

**설계 근거:** `docs/superpowers/specs/2026-07-22-instagram-publish-slice-design.md`

**⚠️ 착수 전 필수:**
- **origin/main(07c2473 이상)에서 새 브랜치 분기.** 워킹트리는 멀티세션 오염 + 뒤처짐(save_authored_deck 경계strip이 origin에만 있음). `git worktree add ../polyinsight-igpub -b feat/instagram-publish origin/main` 로 격리 워크트리에서 작업 권장.
- 테스트는 **항상 `pytest backend/tests/`** (bare pytest = 죽은 스위트). Windows는 `PYTHONUTF8=1`.
- 커밋 포맷: 백엔드 `[BE]`, 프론트 `[WEB]`.
- **실 LLM/실 Graph API 호출은 실행 전 허락** (Task 8·9의 mock 테스트는 예외). Task 11(라이브 발행)만 실호출.
- **Graph API 스코프·엔드포인트는 Task 4 착수 시 Meta 최신문서로 재확인** (자주 바뀜). 아래는 설계 시점 기준.

---

### Task 1: Config 추가 + 토큰 암호화 헬퍼

**Files:**
- Modify: `backend/core/config.py` (GOOGLE_CLIENT_ID 옆에 신규 env 필드)
- Modify: `backend/requirements.txt` (+`cryptography`)
- Create: `backend/core/crypto.py`
- Test: `backend/tests/test_crypto.py`

- [ ] **Step 1: `cryptography` 의존성 추가**

`backend/requirements.txt` 끝에 추가:
```
cryptography>=42.0
```
Run: `pip install cryptography>=42.0`

- [ ] **Step 2: config 필드 추가**

`backend/core/config.py`의 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`와 **동일한 env-read 방식**으로 옆에 추가:
```python
INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_CLIENT_ID", "")
INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_CLIENT_SECRET", "")
SOCIAL_TOKEN_KEY = os.getenv("SOCIAL_TOKEN_KEY", "")          # Fernet 키(urlsafe base64 32B). 비면 IG 연동 dormant
PUBLIC_CARD_URL_SECRET = os.getenv("PUBLIC_CARD_URL_SECRET", "")  # 공개 카드URL HMAC 서명키
PUBLISH_CREDIT_COST = int(os.getenv("PUBLISH_CREDIT_COST", "5"))  # 발행 1회 크레딧(튜닝값)
```
(config.py가 pydantic BaseSettings면 그 스타일로 필드 선언. 핵심 = 위 5개 이름·기본값.)

- [ ] **Step 3: 실패 테스트 작성**

`backend/tests/test_crypto.py`:
```python
import importlib
from backend.core import config, crypto


def _set_key(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", Fernet.generate_key().decode())


def test_encrypt_decrypt_roundtrip(monkeypatch):
    _set_key(monkeypatch)
    secret = "IGQVJ...long-lived-token"
    enc = crypto.encrypt(secret)
    assert enc != secret                 # 암호문은 원문과 다르다
    assert crypto.decrypt(enc) == secret  # 왕복 복원


def test_enabled_reflects_key(monkeypatch):
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", "")
    assert crypto.enabled() is False
    _set_key(monkeypatch)
    assert crypto.enabled() is True
```

- [ ] **Step 4: 실패 확인**

Run: `pytest backend/tests/test_crypto.py -v`
Expected: FAIL (`ModuleNotFoundError: backend.core.crypto`)

- [ ] **Step 5: 구현**

`backend/core/crypto.py`:
```python
"""소셜 토큰 대칭 암호화 (2026-07-23). IG 토큰은 발행 때 되돌려 써야 해 단방향 해시 불가.
키(SOCIAL_TOKEN_KEY) 없으면 dormant — 호출 전 enabled()로 가드."""
from __future__ import annotations

from cryptography.fernet import Fernet

from .config import settings


def enabled() -> bool:
    return bool(settings.SOCIAL_TOKEN_KEY)


def _fernet() -> Fernet:
    return Fernet(settings.SOCIAL_TOKEN_KEY.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
```

- [ ] **Step 6: 통과 확인**

Run: `pytest backend/tests/test_crypto.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add backend/core/crypto.py backend/core/config.py backend/requirements.txt backend/tests/test_crypto.py
git commit -m "[BE] 소셜 토큰 암호화 헬퍼 + IG 연동 config 필드 (crypto.py, Fernet)"
```

---

### Task 2: `social_accounts` 테이블 + DB 헬퍼

**Files:**
- Modify: `backend/core/db.py` (migrate에 CREATE TABLE + 신규 헬퍼)
- Test: `backend/tests/test_social_accounts.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_social_accounts.py`:
```python
import pytest
from backend.core import db


@pytest.fixture
async def _tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    await db.migrate()
    uid = await db.create_user("u@x.io", "")
    return uid


async def test_upsert_then_get(_tmpdb):
    uid = _tmpdb
    await db.upsert_social_account(uid, "instagram", "ig123", "myshop", "ENC_TOKEN", "2026-09-01T00:00:00")
    acct = await db.get_social_account(uid, "instagram")
    assert acct["ig_user_id"] == "ig123"
    assert acct["ig_username"] == "myshop"
    assert acct["access_token"] == "ENC_TOKEN"


async def test_upsert_overwrites(_tmpdb):
    uid = _tmpdb
    await db.upsert_social_account(uid, "instagram", "ig123", "old", "T1", "2026-09-01T00:00:00")
    await db.upsert_social_account(uid, "instagram", "ig123", "new", "T2", "2026-10-01T00:00:00")
    acct = await db.get_social_account(uid, "instagram")
    assert acct["ig_username"] == "new" and acct["access_token"] == "T2"


async def test_get_missing_returns_none(_tmpdb):
    assert await db.get_social_account(_tmpdb, "instagram") is None


async def test_delete(_tmpdb):
    uid = _tmpdb
    await db.upsert_social_account(uid, "instagram", "ig123", "s", "T", "2026-09-01T00:00:00")
    await db.delete_social_account(uid, "instagram")
    assert await db.get_social_account(uid, "instagram") is None
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_social_accounts.py -v`
Expected: FAIL (`AttributeError: ... upsert_social_account`)

- [ ] **Step 3: 테이블 생성 (migrate 안에 추가)**

`backend/core/db.py`의 `migrate()` 함수 안, 다른 `CREATE TABLE IF NOT EXISTS` 블록들과 나란히 추가:
```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS social_accounts (
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                ig_user_id TEXT NOT NULL,
                ig_username TEXT,
                access_token TEXT NOT NULL,
                token_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, provider)
            )
        """)
```

- [ ] **Step 4: 헬퍼 추가 (db.py, oauth_accounts 헬퍼 근처)**

```python
async def upsert_social_account(user_id: int, provider: str, ig_user_id: str,
                                ig_username: str | None, access_token: str,
                                token_expires_at: str | None) -> None:
    now = _utc_now_iso()
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO social_accounts
                (user_id, provider, ig_user_id, ig_username, access_token, token_expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, provider) DO UPDATE SET
                ig_user_id = excluded.ig_user_id,
                ig_username = excluded.ig_username,
                access_token = excluded.access_token,
                token_expires_at = excluded.token_expires_at,
                updated_at = excluded.updated_at
            """,
            (user_id, provider, ig_user_id, ig_username, access_token, token_expires_at, now, now),
        )
        await conn.commit()


async def get_social_account(user_id: int, provider: str) -> dict | None:
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM social_accounts WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_social_account(user_id: int, provider: str) -> None:
    async with _connect() as conn:
        await conn.execute(
            "DELETE FROM social_accounts WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
        await conn.commit()
```

- [ ] **Step 5: 통과 확인**

Run: `pytest backend/tests/test_social_accounts.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/core/db.py backend/tests/test_social_accounts.py
git commit -m "[BE] social_accounts 테이블 + get/upsert/delete 헬퍼 (IG 연동 토큰 저장)"
```

---

### Task 3: `users.credits` 컬럼 + 크레딧 헬퍼

**Files:**
- Modify: `backend/core/db.py` (idempotent ALTER + 헬퍼)
- Test: `backend/tests/test_credits.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_credits.py`:
```python
import pytest
from backend.core import db


@pytest.fixture
async def _uid(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    await db.migrate()
    return await db.create_user("c@x.io", "")


async def test_default_zero(_uid):
    assert await db.get_credits(_uid) == 0


async def test_add_and_deduct(_uid):
    await db.add_credits(_uid, 20)
    assert await db.get_credits(_uid) == 20
    ok = await db.deduct_credits(_uid, 5)
    assert ok is True and await db.get_credits(_uid) == 15


async def test_deduct_insufficient_returns_false(_uid):
    await db.add_credits(_uid, 3)
    ok = await db.deduct_credits(_uid, 5)   # 잔액 부족
    assert ok is False and await db.get_credits(_uid) == 3   # 차감 안 됨
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_credits.py -v`
Expected: FAIL (`AttributeError: get_credits`)

- [ ] **Step 3: idempotent ALTER (migrate 안, paper_text ALTER 패턴 그대로)**

`backend/core/db.py` `migrate()` 안, 기존 `PRAGMA table_info` 마이그레이션들 근처:
```python
        async with conn.execute("PRAGMA table_info(users)") as cur:
            ucols = {r[1] for r in await cur.fetchall()}
        if "credits" not in ucols:
            await conn.execute("ALTER TABLE users ADD COLUMN credits INTEGER NOT NULL DEFAULT 0")
```

- [ ] **Step 4: 헬퍼 추가 (db.py)**

```python
async def get_credits(user_id: int) -> int:
    async with _connect() as conn:
        async with conn.execute("SELECT credits FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def add_credits(user_id: int, amount: int) -> None:
    async with _connect() as conn:
        await conn.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
        await conn.commit()


async def deduct_credits(user_id: int, amount: int) -> bool:
    """잔액 >= amount일 때만 차감하고 True. 부족하면 미차감 False (원자적: WHERE 가드)."""
    async with _connect() as conn:
        cur = await conn.execute(
            "UPDATE users SET credits = credits - ? WHERE id = ? AND credits >= ?",
            (amount, user_id, amount),
        )
        await conn.commit()
        return (cur.rowcount or 0) > 0
```

- [ ] **Step 5: 통과 확인**

Run: `pytest backend/tests/test_credits.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/core/db.py backend/tests/test_credits.py
git commit -m "[BE] users.credits 컬럼 + get/add/deduct 헬퍼 (발행 크레딧 카운터)"
```

---

### Task 4: Instagram OAuth 메커니즘

**Files:**
- Modify: `backend/core/oauth.py` (instagram_* 함수 추가)
- Test: `backend/tests/test_oauth_instagram.py`

⚠️ 착수 시 Meta 공식문서로 authorize/token 엔드포인트·스코프명 재확인.

- [ ] **Step 1: 실패 테스트 작성 (httpx mock)**

`backend/tests/test_oauth_instagram.py`:
```python
import pytest
from backend.core import config, oauth


def test_authorize_url_has_scope_state(monkeypatch):
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "cid")
    url = oauth.instagram_authorize_url("st8")
    assert "instagram_business_content_publish" in url
    assert "state=st8" in url and "client_id=cid" in url


def test_enabled(monkeypatch):
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "")
    assert oauth.instagram_enabled() is False


async def test_exchange_returns_account(monkeypatch, respx_mock):
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "cid")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "sec")
    respx_mock.post("https://api.instagram.com/oauth/access_token").respond(
        json={"access_token": "SHORT", "user_id": "ig123"})
    respx_mock.get("https://graph.instagram.com/access_token").respond(
        json={"access_token": "LONG", "expires_in": 5184000})
    respx_mock.get("https://graph.instagram.com/me").respond(
        json={"user_id": "ig123", "username": "myshop"})
    acct = await oauth.instagram_exchange("CODE")
    assert acct["ig_user_id"] == "ig123"
    assert acct["access_token"] == "LONG"
    assert acct["ig_username"] == "myshop"
    assert acct["expires_in"] == 5184000
```
(테스트 의존성: `respx`. 없으면 `pip install respx` + requirements-dev.txt에 추가.)

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_oauth_instagram.py -v`
Expected: FAIL (`AttributeError: instagram_authorize_url`)

- [ ] **Step 3: 구현 (oauth.py 끝에 추가)**

```python
_IG_AUTH = "https://www.instagram.com/oauth/authorize"
_IG_TOKEN = "https://api.instagram.com/oauth/access_token"
_IG_GRAPH = "https://graph.instagram.com"
_IG_SCOPES = "instagram_business_basic,instagram_business_content_publish"


def instagram_enabled() -> bool:
    return bool(settings.INSTAGRAM_CLIENT_ID and settings.INSTAGRAM_CLIENT_SECRET)


def instagram_authorize_url(state: str) -> str:
    q = urlencode({
        "client_id": settings.INSTAGRAM_CLIENT_ID,
        "redirect_uri": redirect_uri("instagram"),
        "response_type": "code",
        "scope": _IG_SCOPES,
        "state": state,
    })
    return f"{_IG_AUTH}?{q}"


async def instagram_exchange(code: str) -> dict:
    """code → short-lived → long-lived(60d) → username. 반환:
    {ig_user_id, access_token(long), expires_in, ig_username}. 실패 시 예외."""
    async with httpx.AsyncClient(timeout=15) as client:
        tok = await client.post(_IG_TOKEN, data={
            "client_id": settings.INSTAGRAM_CLIENT_ID,
            "client_secret": settings.INSTAGRAM_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri("instagram"),
            "code": code,
        })
        tok.raise_for_status()
        short = tok.json()
        ig_user_id = str(short["user_id"])
        ll = await client.get(f"{_IG_GRAPH}/access_token", params={
            "grant_type": "ig_exchange_token",
            "client_secret": settings.INSTAGRAM_CLIENT_SECRET,
            "access_token": short["access_token"],
        })
        ll.raise_for_status()
        long_tok = ll.json()
        me = await client.get(f"{_IG_GRAPH}/me", params={
            "fields": "user_id,username",
            "access_token": long_tok["access_token"],
        })
        me.raise_for_status()
        prof = me.json()
    return {
        "ig_user_id": ig_user_id,
        "access_token": long_tok["access_token"],
        "expires_in": long_tok.get("expires_in"),
        "ig_username": prof.get("username"),
    }
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_oauth_instagram.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/core/oauth.py backend/tests/test_oauth_instagram.py backend/requirements-dev.txt
git commit -m "[BE] Instagram Login OAuth 메커니즘 (authorize/exchange, graph.instagram.com)"
```

---

### Task 5: Instagram 연동 라우트 (start/callback)

**Files:**
- Modify: `backend/routers/auth.py` (google 라우트 미러링, 단 세션생성 아님=연동)
- Test: `backend/tests/test_ig_connect_routes.py`

**핵심 차이:** google callback은 세션을 만든다. instagram callback은 **이미 로그인한 유저**(get_current_user)에 IG 계정을 붙인다(토큰 암호화 저장). 세션 안 만듦.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_ig_connect_routes.py`:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from backend.core import config, db, crypto, oauth
from backend.main import app


@pytest.fixture
async def _client(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "cid")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "sec")
    await db.migrate()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def test_callback_stores_encrypted_token(_client, monkeypatch):
    # 로그인 유저 + 세션 쿠키
    uid = await db.create_user("i@x.io", "")
    # (테스트 헬퍼로 세션 발급 — 기존 test_api.py의 로그인 헬퍼 재사용)
    from backend.tests.conftest import login_cookie   # 프로젝트 로그인 헬퍼(있으면)
    _client.cookies.update(await login_cookie(uid))
    async def fake_exchange(code):
        return {"ig_user_id": "ig9", "access_token": "LONGTOK", "expires_in": 5184000, "ig_username": "shop"}
    monkeypatch.setattr(oauth, "instagram_exchange", fake_exchange)
    # state 쿠키 세팅 후 콜백
    r = await _client.get("/api/auth/oauth/instagram/start", follow_redirects=False)
    state = _client.cookies.get("oauth_state")
    r2 = await _client.get(f"/api/auth/oauth/instagram/callback?code=C&state={state}", follow_redirects=False)
    assert r2.status_code == 302
    acct = await db.get_social_account(uid, "instagram")
    assert acct is not None and acct["ig_user_id"] == "ig9"
    assert acct["access_token"] != "LONGTOK"          # 암호화 저장
    assert crypto.decrypt(acct["access_token"]) == "LONGTOK"
```
(로그인 헬퍼 이름은 기존 `backend/tests/` 관례에 맞춤 — test_api.py의 세션 발급 방식 재사용.)

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_ig_connect_routes.py -v`
Expected: FAIL (404 — 라우트 없음)

- [ ] **Step 3: 구현 (auth.py, google 라우트 아래)**

```python
@router.get("/oauth/instagram/start")
async def oauth_instagram_start(user: dict = Depends(get_current_user)):
    """IG 연동 시작 — 로그인 유저만. 세션 아님, 발행권한 연동."""
    if not oauth_core.instagram_enabled() or not crypto.enabled():
        return RedirectResponse(url=f"{_web_base()}/dashboard?error=ig_disabled", status_code=302)
    state = secrets.token_urlsafe(24)
    resp = RedirectResponse(url=oauth_core.instagram_authorize_url(state), status_code=302)
    resp.set_cookie(OAUTH_STATE_COOKIE, state, max_age=600, httponly=True,
                    samesite="lax", secure=settings.COOKIE_SECURE, path="/")
    return resp


@router.get("/oauth/instagram/callback")
async def oauth_instagram_callback(request: Request, user: dict = Depends(get_current_user),
                                   code: str = "", state: str = ""):
    """IG 콜백 → 토큰 교환 → 암호화 저장(로그인 유저에 연동). 세션 안 만듦."""
    web = _web_base()
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not code or not state or not cookie_state or state != cookie_state:
        return RedirectResponse(url=f"{web}/dashboard?error=ig_state", status_code=302)
    try:
        acct = await oauth_core.instagram_exchange(code)
    except Exception:
        logging.getLogger(__name__).exception("instagram oauth 교환 실패")
        return RedirectResponse(url=f"{web}/dashboard?error=ig_failed", status_code=302)
    exp = None
    if acct.get("expires_in"):
        from datetime import timedelta
        exp = (db._utc_now() + timedelta(seconds=int(acct["expires_in"]))).isoformat()
    await db.upsert_social_account(user["id"], "instagram", acct["ig_user_id"],
                                   acct.get("ig_username"), crypto.encrypt(acct["access_token"]), exp)
    resp = RedirectResponse(url=f"{web}/dashboard?ig=connected", status_code=302)
    resp.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    await db.log_event("instagram_connected", user_id=user["id"])
    return resp
```
파일 상단 import에 `from ..core import crypto` 추가.

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_ig_connect_routes.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/routers/auth.py backend/tests/test_ig_connect_routes.py
git commit -m "[BE] Instagram 연동 라우트 start/callback (세션 아닌 연동, 토큰 암호화 저장)"
```

---

### Task 6: 소셜 상태/해제 라우터

**Files:**
- Create: `backend/routers/social.py`
- Modify: `backend/main.py` (라우터 등록)
- Test: `backend/tests/test_social_router.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_social_router.py`:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from backend.core import db
from backend.main import app


@pytest.fixture
async def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    await db.migrate()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def test_status_not_connected(_client):
    uid = await db.create_user("s@x.io", "")
    from backend.tests.conftest import login_cookie
    _client.cookies.update(await login_cookie(uid))
    r = await _client.get("/api/social/instagram/status")
    assert r.status_code == 200 and r.json() == {"connected": False, "username": None}


async def test_status_connected_then_disconnect(_client):
    uid = await db.create_user("s2@x.io", "")
    from backend.tests.conftest import login_cookie
    _client.cookies.update(await login_cookie(uid))
    await db.upsert_social_account(uid, "instagram", "ig9", "shop", "ENC", None)
    r = await _client.get("/api/social/instagram/status")
    assert r.json() == {"connected": True, "username": "shop"}
    r2 = await _client.delete("/api/social/instagram")
    assert r2.status_code == 200
    assert (await _client.get("/api/social/instagram/status")).json()["connected"] is False
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_social_router.py -v`
Expected: FAIL (404)

- [ ] **Step 3: 라우터 구현**

`backend/routers/social.py`:
```python
"""소셜 계정 연동 상태 관리 (2026-07-23). 발행 OAuth는 auth.py, 여기는 상태/해제."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..core import db
from ..core.auth import get_current_user

router = APIRouter(prefix="/api/social", tags=["social"])


@router.get("/instagram/status")
async def instagram_status(user: dict = Depends(get_current_user)):
    acct = await db.get_social_account(user["id"], "instagram")
    return {"connected": acct is not None, "username": acct["ig_username"] if acct else None}


@router.delete("/instagram")
async def instagram_disconnect(user: dict = Depends(get_current_user)):
    await db.delete_social_account(user["id"], "instagram")
    await db.log_event("instagram_disconnected", user_id=user["id"])
    return {"ok": True}
```

- [ ] **Step 4: main.py에 등록**

`backend/main.py`의 라우터 등록부(auth.router 등록 근처)에 추가:
```python
from .routers import social as social_router
app.include_router(social_router.router)
```

- [ ] **Step 5: 통과 확인**

Run: `pytest backend/tests/test_social_router.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/routers/social.py backend/main.py backend/tests/test_social_router.py
git commit -m "[BE] 소셜 상태/해제 라우터 (GET status, DELETE instagram)"
```

---

### Task 7: 서명된 공개 카드 URL

**Files:**
- Create: `backend/core/signing.py`
- Modify: `backend/routers/deck.py` (공개 라우트 추가)
- Test: `backend/tests/test_card_public_url.py`

- [ ] **Step 1: 실패 테스트 작성 (서명 로직)**

`backend/tests/test_card_public_url.py`:
```python
import time
import pytest
from backend.core import config, signing


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setattr(config.settings, "PUBLIC_CARD_URL_SECRET", "test-secret")


def test_valid_sig_passes():
    exp, sig = signing.sign_card("job1", 2)
    assert signing.verify_card("job1", 2, exp, sig) is True


def test_expired_fails():
    exp, sig = signing.sign_card("job1", 2, ttl_s=-1)   # 이미 만료
    assert signing.verify_card("job1", 2, exp, sig) is False


def test_forged_sig_fails():
    exp, _ = signing.sign_card("job1", 2)
    assert signing.verify_card("job1", 2, exp, "deadbeef") is False


def test_wrong_card_fails():
    exp, sig = signing.sign_card("job1", 2)
    assert signing.verify_card("job1", 3, exp, sig) is False   # 다른 카드 번호
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_card_public_url.py -v`
Expected: FAIL (`ModuleNotFoundError: signing`)

- [ ] **Step 3: 서명 헬퍼 구현**

`backend/core/signing.py`:
```python
"""공개 카드 URL HMAC 서명 (2026-07-23). Meta가 쿠키 없이 카드 PNG를 긁게 하되,
서명+만료로 무제한 노출 방지. 발행 순간에만 소유자에게 발급."""
from __future__ import annotations

import hashlib
import hmac
import time

from .config import settings


def _mac(job_id: str, card_num: int, exp: int) -> str:
    msg = f"{job_id}:{card_num}:{exp}".encode()
    return hmac.new(settings.PUBLIC_CARD_URL_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def sign_card(job_id: str, card_num: int, ttl_s: int = 600) -> tuple[int, str]:
    exp = int(time.time()) + ttl_s
    return exp, _mac(job_id, card_num, exp)


def verify_card(job_id: str, card_num: int, exp: int, sig: str) -> bool:
    if exp < int(time.time()):
        return False
    return hmac.compare_digest(_mac(job_id, card_num, exp), sig)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_card_public_url.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 공개 라우트 추가 (deck.py, get_deck_asset 근처)**

```python
from ..core import signing


@router.get("/deck/{job_id}/cards/{card_num}/public")
async def get_card_public(job_id: str, card_num: int, exp: int = 0, sig: str = ""):
    """서명·만료 검증된 무인증 카드 PNG (Meta Graph API image_url용, 스펙 §5).
    발행 시 소유자에게만 서명 URL 발급. self-heal은 기존 _heal_card_images 재사용."""
    if not signing.verify_card(job_id, card_num, exp, sig):
        raise HTTPException(404, detail={"code": "ERR-IMG-004", "message": "not found"})
    png = await _heal_card_images(job_id, card_num)
    if png is None:
        raise HTTPException(404, detail={"code": "ERR-IMG-004", "message": "not found"})
    return Response(content=png, media_type="image/png")
```
(deck.router는 per-route self-gate라 글로벌 get_current_user 안 걸림 — get_deck_asset과 동일하게 무인증 OK.)

- [ ] **Step 6: 라우트 통합 테스트 추가**

`backend/tests/test_card_public_url.py`에 추가:
```python
async def test_public_route_rejects_bad_sig(tmp_path, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from backend.core import db
    from backend.main import app
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setattr(config.settings, "PUBLIC_CARD_URL_SECRET", "s")
    await db.migrate()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/deck/j/cards/1/public?exp=9999999999&sig=bad")
        assert r.status_code == 404
```

Run: `pytest backend/tests/test_card_public_url.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: 커밋**

```bash
git add backend/core/signing.py backend/routers/deck.py backend/tests/test_card_public_url.py
git commit -m "[BE] 서명된 공개 카드 URL (HMAC+만료, Meta image_url용, self-heal 재사용)"
```

---

### Task 8: Instagram 발행 클라이언트 (Graph API 캐러셀)

**Files:**
- Create: `backend/agents/deck/ig_publish.py`
- Test: `backend/tests/test_ig_publish.py`

⚠️ 엔드포인트·필드명 Meta 최신문서 재확인.

- [ ] **Step 1: 실패 테스트 작성 (httpx respx mock)**

`backend/tests/test_ig_publish.py`:
```python
import pytest
from backend.agents.deck import ig_publish


async def test_publish_carousel_sequence(respx_mock):
    G = "https://graph.instagram.com"
    # 카드 2장 → item 컨테이너 2개
    respx_mock.post(f"{G}/ig9/media").mock(side_effect=[
        _json({"id": "item1"}), _json({"id": "item2"}), _json({"id": "carousel1"}),
    ])
    respx_mock.get(f"{G}/carousel1").respond(json={"status_code": "FINISHED"})
    respx_mock.post(f"{G}/ig9/media_publish").respond(json={"id": "pub1"})
    respx_mock.get(f"{G}/pub1").respond(json={"permalink": "https://instagram.com/p/ABC"})

    permalink = await ig_publish.publish_carousel(
        "ig9", "TOKEN", ["https://u/1.png", "https://u/2.png"], "caption #a")
    assert permalink == "https://instagram.com/p/ABC"


def _json(payload):
    import httpx
    return httpx.Response(200, json=payload)
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_ig_publish.py -v`
Expected: FAIL (`ModuleNotFoundError: ig_publish`)

- [ ] **Step 3: 구현**

`backend/agents/deck/ig_publish.py`:
```python
"""Instagram 캐러셀 발행 (2026-07-23, graph.instagram.com).
공개 URL 리스트 + 캡션 → 게시글 permalink. 실패는 예외로 표면화(호출자가 크레딧 미차감)."""
from __future__ import annotations

import asyncio

import httpx

_G = "https://graph.instagram.com"
_POLL_MAX = 10
_POLL_INTERVAL_S = 2.0


async def publish_carousel(ig_user_id: str, access_token: str,
                           image_urls: list[str], caption: str) -> str:
    """캐러셀 발행 → permalink. 카드마다 item 컨테이너 → 캐러셀 컨테이너 → 폴링 → publish."""
    async with httpx.AsyncClient(timeout=30) as client:
        # 1) item 컨테이너
        child_ids: list[str] = []
        for url in image_urls:
            r = await client.post(f"{_G}/{ig_user_id}/media", data={
                "image_url": url, "is_carousel_item": "true", "access_token": access_token})
            r.raise_for_status()
            child_ids.append(r.json()["id"])
        # 2) 캐러셀 컨테이너
        r = await client.post(f"{_G}/{ig_user_id}/media", data={
            "media_type": "CAROUSEL", "children": ",".join(child_ids),
            "caption": caption, "access_token": access_token})
        r.raise_for_status()
        container_id = r.json()["id"]
        # 3) 컨테이너 준비 폴링
        for _ in range(_POLL_MAX):
            s = await client.get(f"{_G}/{container_id}", params={
                "fields": "status_code", "access_token": access_token})
            s.raise_for_status()
            if s.json().get("status_code") == "FINISHED":
                break
            await asyncio.sleep(_POLL_INTERVAL_S)
        else:
            raise RuntimeError("carousel container not FINISHED after polling")
        # 4) 발행
        p = await client.post(f"{_G}/{ig_user_id}/media_publish", data={
            "creation_id": container_id, "access_token": access_token})
        p.raise_for_status()
        published_id = p.json()["id"]
        # 5) permalink
        pl = await client.get(f"{_G}/{published_id}", params={
            "fields": "permalink", "access_token": access_token})
        pl.raise_for_status()
        return pl.json()["permalink"]
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_ig_publish.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/agents/deck/ig_publish.py backend/tests/test_ig_publish.py
git commit -m "[BE] Instagram 캐러셀 발행 클라이언트 (item→컨테이너→폴링→publish→permalink)"
```

---

### Task 9: 발행 엔드포인트

**Files:**
- Modify: `backend/routers/deck.py` (POST publish)
- Test: `backend/tests/test_publish_endpoint.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_publish_endpoint.py`:
```python
import json
import pytest
from httpx import ASGITransport, AsyncClient
from backend.core import config, db, crypto
from backend.agents.deck import ig_publish
from backend.main import app


@pytest.fixture
async def _ctx(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(db.settings, "DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config.settings, "PUBLIC_CARD_URL_SECRET", "s")
    monkeypatch.setattr(config.settings, "PUBLIC_BASE_URL", "https://app.test")
    monkeypatch.setattr(config.settings, "PUBLISH_CREDIT_COST", 5)
    await db.migrate()
    return tmp_path


async def test_publish_happy_path(_ctx, monkeypatch):
    uid = await db.create_user("p@x.io", "")
    from backend.tests.conftest import login_cookie
    # 덱 + 연동 + 크레딧
    await db.save_authored_deck("jP", '<div data-screen-label="01" style="width:1080px"></div>', "[]", 1, "paper")
    await db.upsert_social_account(uid, "instagram", "ig9", "shop", crypto.encrypt("TOK"), None)
    await db.add_credits(uid, 10)
    # 잡 소유권 (기존 헬퍼로 uid 소유 잡 등록 — test_api.py 관례)
    await db.set_job_owner("jP", uid)   # 프로젝트 관례에 맞는 소유권 지정 헬퍼

    captured = {}
    async def fake_pub(ig_user_id, token, urls, caption):
        captured["urls"] = urls; captured["token"] = token
        return "https://instagram.com/p/OK"
    monkeypatch.setattr(ig_publish, "publish_carousel", fake_pub)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        r = await c.post("/api/deck/jP/publish/instagram")
    assert r.status_code == 200 and r.json()["permalink"] == "https://instagram.com/p/OK"
    assert captured["token"] == "TOK"                     # 복호화된 토큰 전달
    assert captured["urls"][0].startswith("https://app.test/api/deck/jP/cards/1/public?exp=")
    assert await db.get_credits(uid) == 5                  # 10 - 5 차감


async def test_publish_blocks_without_connection(_ctx):
    uid = await db.create_user("p2@x.io", "")
    from backend.tests.conftest import login_cookie
    await db.save_authored_deck("jN", "<div data-screen-label='01'></div>", "[]", 1, "p")
    await db.set_job_owner("jN", uid)
    await db.add_credits(uid, 10)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        r = await c.post("/api/deck/jN/publish/instagram")
    assert r.status_code == 400   # 미연동


async def test_publish_blocks_insufficient_credits(_ctx, monkeypatch):
    uid = await db.create_user("p3@x.io", "")
    from backend.tests.conftest import login_cookie
    await db.save_authored_deck("jC", "<div data-screen-label='01'></div>", "[]", 1, "p")
    await db.set_job_owner("jC", uid)
    await db.upsert_social_account(uid, "instagram", "ig9", "shop", crypto.encrypt("TOK"), None)
    await db.add_credits(uid, 2)   # < 5
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.cookies.update(await login_cookie(uid))
        r = await c.post("/api/deck/jC/publish/instagram")
    assert r.status_code == 402   # 크레딧 부족
    assert await db.get_credits(uid) == 2   # 미차감
```
(`set_job_owner`/`login_cookie`는 기존 test_api.py의 잡 소유권·세션 발급 관례에 맞춤 — 그 헬퍼명 사용.)

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_publish_endpoint.py -v`
Expected: FAIL (404 — 라우트 없음)

- [ ] **Step 3: 캡션 텍스트 헬퍼 + 발행 라우트 (deck.py)**

get_deck_caption 근처에 헬퍼 + 라우트 추가:
```python
from ..core import crypto, signing
from ..agents.deck import ig_publish


async def _deck_caption_text(job_id: str, deck: dict) -> str:
    """발행용 캡션 문자열(캡션+해시태그). 캐시 있으면 사용, 없으면 생성. 검증수치만(해자)."""
    cached = deck.get("caption_json")
    if cached:
        data = json.loads(cached)
    else:
        data = await generate_caption(deck["html"], deck.get("paper_text"))
        await db.set_deck_caption(job_id, json.dumps(data, ensure_ascii=False))
    tags = " ".join(data.get("hashtags", []))
    return (data.get("caption", "") + ("\n\n" + tags if tags else "")).strip()


@router.post("/deck/{job_id}/publish/instagram")
async def publish_instagram(job_id: str, user: dict = Depends(get_current_user)):
    """덱을 유저 IG에 캐러셀 발행. 연동·크레딧 확인 → 서명 공개URL → Graph 발행 → 성공 시 차감."""
    await require_owned_job(job_id, user)
    acct = await db.get_social_account(user["id"], "instagram")
    if not acct:
        raise HTTPException(400, detail={"code": "ERR-IG-001", "message": "인스타 계정을 먼저 연동해 주세요."})
    if await db.get_credits(user["id"]) < settings.PUBLISH_CREDIT_COST:
        raise HTTPException(402, detail={"code": "ERR-IG-002", "message": "크레딧이 부족합니다."})
    deck = await db.get_authored_deck(job_id)
    if not deck:
        raise HTTPException(404, detail={"code": "ERR-IG-003", "message": "덱을 찾을 수 없습니다."})

    base = (settings.PUBLIC_BASE_URL or settings.WEB_BASE_URL).rstrip("/")
    urls: list[str] = []
    for n in range(1, int(deck["card_count"]) + 1):
        exp, sig = signing.sign_card(job_id, n)
        urls.append(f"{base}/api/deck/{job_id}/cards/{n}/public?exp={exp}&sig={sig}")

    caption = await _deck_caption_text(job_id, deck)
    token = crypto.decrypt(acct["access_token"])
    try:
        permalink = await ig_publish.publish_carousel(acct["ig_user_id"], token, urls, caption)
    except Exception:
        logging.getLogger(__name__).exception("instagram 발행 실패")
        raise HTTPException(502, detail={"code": "ERR-IG-004", "message": "인스타 발행에 실패했습니다. 잠시 후 다시 시도해 주세요."})

    await db.deduct_credits(user["id"], settings.PUBLISH_CREDIT_COST)   # 성공 시에만
    await db.log_event("instagram_publish", user_id=user["id"], job_id=job_id)
    return {"permalink": permalink}
```
파일 상단에 `import logging` 확인(없으면 추가).

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_publish_endpoint.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 전체 백엔드 스위트 회귀 확인**

Run: `pytest backend/tests/`
Expected: 전부 PASS (신규 테스트 포함, 기존 무영향)

- [ ] **Step 6: 커밋**

```bash
git add backend/routers/deck.py backend/tests/test_publish_endpoint.py
git commit -m "[BE] 발행 엔드포인트 POST /deck/{id}/publish/instagram (연동·크레딧 가드→캐러셀→차감)"
```

---

### Task 10: 프론트 — DeckExportModal 확장 + api.ts

**Files:**
- Modify: `web/src/lib/api.ts` (신규 API 함수)
- Modify: `web/src/components/deck/DeckExportModal.tsx` (인스타 모드에 연동/자동발행 추가, 수동 폴백 존치)
- Test: `web/src/lib/__tests__/instagramPublish.test.ts` (api 함수 단위, vitest)

- [ ] **Step 1: api.ts 함수 추가**

`web/src/lib/api.ts`에 추가(기존 fetch 래퍼 패턴에 맞춤):
```typescript
export async function getInstagramStatus(): Promise<{ connected: boolean; username: string | null }> {
  const r = await fetch('/api/social/instagram/status', { credentials: 'include' })
  if (!r.ok) return { connected: false, username: null }
  return r.json()
}

export async function publishInstagram(jobId: string): Promise<{ ok: boolean; permalink?: string; error?: string }> {
  const r = await fetch(`/api/deck/${jobId}/publish/instagram`, { method: 'POST', credentials: 'include' })
  const body = await r.json().catch(() => ({}))
  if (!r.ok) return { ok: false, error: body?.detail?.message || '발행 실패' }
  return { ok: true, permalink: body.permalink }
}

export function instagramConnectUrl(): string {
  return '/api/auth/oauth/instagram/start'   // 브라우저 네비게이션(OAuth 리다이렉트)
}
```

- [ ] **Step 2: DeckExportModal 인스타 모드 확장**

`web/src/components/deck/DeckExportModal.tsx`의 `mode === 'instagram'` 뷰(현재 수동 3단계)에 **연동 상태 UI 추가**. 기존 수동 3단계(캡션복사·다운·인스타 열기)는 **아래에 폴백으로 유지**:
- 컴포넌트 진입 시 `getInstagramStatus()` 호출해 `igStatus` state 저장
- `enterInstagram` 뒤에 상태 로드:
```typescript
const [ig, setIg] = useState<{ connected: boolean; username: string | null } | null>(null)
const [publishing, setPublishing] = useState(false)
const [publishedUrl, setPublishedUrl] = useState<string | null>(null)
// enterInstagram 안에서:
getInstagramStatus().then(setIg)
```
- 인스타 모드 상단에 블록 추가(수동 3단계 위):
```tsx
{ig?.connected ? (
  <div className="rounded-lg border border-border p-3 mb-3">
    <p className="text-[12px] text-ink-3 mb-2">@{ig.username} 연동됨 · 앱에서 바로 발행</p>
    {publishedUrl ? (
      <a href={publishedUrl} target="_blank" rel="noopener"
         className="btn btn-primary w-full text-center">게시됨 — 인스타에서 보기 ↗</a>
    ) : (
      <button className="btn btn-primary w-full" disabled={publishing}
        onClick={async () => {
          setPublishing(true)
          const res = await publishInstagram(jobId)
          setPublishing(false)
          if (res.ok && res.permalink) setPublishedUrl(res.permalink)
          else alert(res.error || '발행 실패')
        }}>
        {publishing ? '발행 중…' : '📸 인스타에 자동 발행'}
      </button>
    )}
  </div>
) : (
  <div className="rounded-lg border border-border p-3 mb-3">
    <p className="text-[12px] text-ink-3 mb-2">인스타 계정을 연동하면 앱에서 바로 발행할 수 있어요</p>
    <a href={instagramConnectUrl()} className="btn btn-ghost w-full text-center">인스타 계정 연동</a>
  </div>
)}
{/* ↓ 기존 수동 3단계(캡션복사·이미지다운·인스타 열기) 그대로 유지 = 폴백 */}
```
import에 `getInstagramStatus, publishInstagram, instagramConnectUrl` 추가.

- [ ] **Step 3: api 함수 단위 테스트 (vitest)**

`web/src/lib/__tests__/instagramPublish.test.ts`:
```typescript
import { describe, it, expect, vi, afterEach } from 'vitest'
import { publishInstagram, getInstagramStatus } from '../api'

afterEach(() => vi.restoreAllMocks())

describe('publishInstagram', () => {
  it('returns permalink on 200', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      JSON.stringify({ permalink: 'https://instagram.com/p/X' }), { status: 200 })))
    const r = await publishInstagram('j1')
    expect(r).toEqual({ ok: true, permalink: 'https://instagram.com/p/X' })
  })
  it('returns error message on failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(
      JSON.stringify({ detail: { message: '크레딧 부족' } }), { status: 402 })))
    const r = await publishInstagram('j1')
    expect(r.ok).toBe(false)
    expect(r.error).toBe('크레딧 부족')
  })
})

describe('getInstagramStatus', () => {
  it('falls back to disconnected on error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 500 })))
    expect(await getInstagramStatus()).toEqual({ connected: false, username: null })
  })
})
```

- [ ] **Step 4: 프론트 테스트 통과 확인**

Run: `cd web && npm test`
Expected: PASS (신규 3 테스트 포함, 기존 무영향)

- [ ] **Step 5: 커밋**

```bash
git add web/src/lib/api.ts web/src/components/deck/DeckExportModal.tsx web/src/lib/__tests__/instagramPublish.test.ts
git commit -m "[WEB] DeckExportModal 인스타 자동발행 + 연동 버튼 (수동 폴백 존치)"
```

---

### Task 11: 라이브 발행 검증 (실호출 — 실행 전 허락)

**Files:** 없음(수동 검증). 이게 Meta 심사 요건 "30일 내 성공 API 콜"도 충족.

- [ ] **Step 1: 환경 준비**
  - Meta 앱(개발 모드) 생성, Instagram Login 설정, 리디렉트 URI = `{PUBLIC_BASE_URL}/api/auth/oauth/instagram/callback` 등록
  - `.env`: `INSTAGRAM_CLIENT_ID/SECRET`, `SOCIAL_TOKEN_KEY`(=`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`), `PUBLIC_CARD_URL_SECRET`(랜덤), 테스트 유저 크레딧 시드(`db.add_credits`)
  - IG 비즈니스/크리에이터 테스트 계정 준비

- [ ] **Step 2: E2E 수동 검증 (실 Graph 호출 — 허락 필수)**
  - 로그인 → 덱 생성 → export 모달 → "인스타 계정 연동"(OAuth 왕복) → "자동 발행"
  - **실물 확인:** 실제 IG 계정에 캐러셀 게시글이 뜨는지 permalink로 육안 확인(코드 "성공"만으로 증명 안 함 — 산출물 실물을 잰다)
  - 크레딧이 정확히 차감됐는지 확인

- [ ] **Step 3: 개인정보처리방침 IG 항목 추가**
  - `web/src/app/privacy/page.tsx`에 "인스타그램 계정 접근·유저 대신 게시" 항목 추가(Meta 심사 요건). 배포.

- [ ] **Step 4: 커밋**

```bash
git add web/src/app/privacy/page.tsx
git commit -m "[WEB] 개인정보처리방침에 인스타 데이터 접근·게시 항목 추가 (Meta 심사 요건)"
```

---

## Self-Review

**Spec coverage (스펙 §별 → Task 매핑):**
- §2 Instagram Login API → Task 4 ✓
- §4 OAuth + 토큰 저장(암호화) → Task 1(crypto)·2(테이블)·5(연동 라우트) ✓
- §5 서명 공개 카드 URL(A안) → Task 7 ✓
- §6 Graph 캐러셀 발행 → Task 8 ✓
- §7 크레딧 최소 카운터 → Task 3·9(가드·차감) ✓
- §8 엔드포인트 전부(start/callback/status/disconnect/public/publish) → Task 5·6·7·9 ✓
- §10 UI(연동/자동발행 + 수동 폴백 존치) → Task 10 ✓
- §12 테스트(목킹 유닛 + 라이브 1회) → 각 Task TDD + Task 11 ✓
- §13 privacy IG 항목 → Task 11 Step 3 ✓

**Placeholder scan:** 코드 스텝 전부 실제 코드. "기존 관례에 맞춤"으로 남긴 3곳(`login_cookie`·`set_job_owner` 테스트 헬퍼, config.py 필드 선언 방식)은 **기존 파일에 실물이 있는** 항목이라 구현자가 test_api.py/config.py에서 바로 확인 — 착수 시 그 헬퍼명만 grep으로 맞출 것.

**Type consistency:** `publish_carousel(ig_user_id, access_token, image_urls, caption)` (Task 8) ↔ 호출(Task 9) 시그니처 일치. `get_social_account`/`upsert_social_account`/`delete_social_account`(Task 2) ↔ Task 5·6·9 사용 일치. `sign_card`/`verify_card`(Task 7) ↔ Task 9 사용 일치. `get_credits`/`deduct_credits`(Task 3) ↔ Task 9 일치.

**착수 전 확정 필요(스펙 §14):** Meta 스코프·엔드포인트 재확인(Task 4·8) / `PUBLISH_CREDIT_COST` 값(현 5) / 폴링 상한(현 10회·2초).
