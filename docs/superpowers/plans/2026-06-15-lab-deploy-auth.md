# 인증(Auth) Implementation Plan — 연구실 배포 Plan 1/3

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 공개 URL 배포 전에 백엔드에 실제 로그인(이메일/비밀번호 세션) + 초대코드 가입 + 시드 계정을 구현하고, 기존 API를 보호한다.

**Architecture:** 서버사이드 세션 토큰(DB `sessions` 테이블) + httpOnly 쿠키. argon2 비밀번호 해싱. 기존 라우터(`jobs`/`projects`/`export`)는 `main.py`의 `include_router(dependencies=[Depends(get_current_user)])`로 일괄 보호. **S7 렌더(Playwright)는 세션 쿠키가 없으므로 내부 `X-Render-Token` 헤더로 인증을 우회**한다(브라우저 컨텍스트 헤더 → Next rewrite → 백엔드 통과).

**Tech Stack:** FastAPI, aiosqlite, argon2-cffi, Next.js 15(App Router, client components), httpx 테스트.

**상위 스펙:** `docs/superpowers/specs/2026-06-15-lab-deployment-design.md`

**브랜치:** 이 작업은 새 브랜치 `feat/lab-deploy-auth`에서 진행한다(현재 `feat/s6-digest`와 분리). 첫 커밋 전에 생성.

---

## 파일 구조 (생성/수정)

- 수정 `backend/requirements.txt` — argon2-cffi 추가
- 수정 `backend/core/config.py` — 세션/쿠키/렌더토큰 설정
- 수정 `backend/core/db.py` — users/sessions/invites 테이블 + DB 헬퍼
- 생성 `backend/core/auth.py` — 해싱 + `get_current_user` 의존성
- 생성 `backend/routers/auth.py` — signup/login/logout/me 엔드포인트
- 수정 `backend/main.py` — auth 라우터 등록 + 기존 라우터 보호
- 수정 `backend/agents/s7_renderer.py` — 렌더 컨텍스트에 X-Render-Token 헤더
- 생성 `backend/scripts/seed_user.py` — 박사님 계정 시드 CLI
- 생성 `backend/scripts/create_invite.py` — 초대코드 생성 CLI
- 생성 `backend/tests/test_auth.py` — 인증 테스트(보호/우회 포함)
- 수정 `backend/tests/test_api.py` — 기존 테스트에 auth 우회 override
- 수정 `web/src/components/auth/AuthForm.tsx` — 실제 엔드포인트 연동 + invite 필드
- 생성 `web/src/components/auth/AuthGuard.tsx` — /api/auth/me 가드
- 생성 `web/src/components/auth/LogoutButton.tsx` — 로그아웃 버튼
- 수정 `web/src/app/dashboard/page.tsx` — AuthGuard 래핑 + 로그아웃
- 수정 `web/src/app/editor/[jobId]/page.tsx` — AuthGuard 래핑

---

## Task 1: 의존성 + 설정 추가

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/core/config.py`

- [ ] **Step 1: requirements에 argon2 추가**

`backend/requirements.txt` 마지막 줄(`python-dotenv==1.0.0`) 다음에 추가:

```
argon2-cffi==23.1.0
```

- [ ] **Step 2: 설치**

Run: `pip install argon2-cffi==23.1.0`
Expected: `Successfully installed argon2-cffi`

- [ ] **Step 3: config.py에 설정 추가**

`backend/core/config.py`의 `Settings` 클래스에서 `DEV_MOCK_LLM` 줄 다음에 추가:

```python
    SESSION_TTL_HOURS: int = 72         # 세션 쿠키/DB 만료
    COOKIE_SECURE: bool = False         # 프로덕션(HTTPS/터널)에서 True
    RENDER_TOKEN: str = ""              # 내부 렌더(Playwright) 서비스 우회 토큰. 프로덕션 필수.
```

- [ ] **Step 4: 설정 로드 확인**

Run: `python -c "from backend.core.config import settings; print(settings.SESSION_TTL_HOURS, settings.COOKIE_SECURE, repr(settings.RENDER_TOKEN))"`
Expected: `72 False ''`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/core/config.py
git commit -m "[BE] auth: argon2 의존성 + 세션/쿠키/렌더토큰 설정"
```

---

## Task 2: DB 스키마 (users / sessions / invites)

**Files:**
- Modify: `backend/core/db.py:30-81` (migrate의 executescript)
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_auth.py` 생성:

```python
"""인증 테스트 — auth 우회 override 없이 실제 세션/보호 동작 검증."""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core import db as _db
from backend.core.config import settings
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def mem_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "auth.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setattr(settings, "SESSION_TTL_HOURS", 72)
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "RENDER_TOKEN", "")
    await _db.migrate()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_migrate_creates_auth_tables():
    import aiosqlite
    from backend.core.db import _db_path
    async with aiosqlite.connect(_db_path()) as conn:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cur:
            names = {row[0] for row in await cur.fetchall()}
    assert {"users", "sessions", "invites"} <= names
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_auth.py::test_migrate_creates_auth_tables -v`
Expected: FAIL — `users`/`sessions`/`invites` 없음

- [ ] **Step 3: migrate에 테이블 추가**

`backend/core/db.py`의 `executescript(...)` 문자열 안, `researchers` 테이블 정의 다음(닫는 `"""` 직전)에 추가:

```sql

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS invites (
                code TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                used_by INTEGER REFERENCES users(id),
                used_at TEXT
            );
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_auth.py::test_migrate_creates_auth_tables -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/db.py backend/tests/test_auth.py
git commit -m "[BE] auth: users/sessions/invites 스키마 + migrate 테스트"
```

---

## Task 3: 비밀번호 해싱 (core/auth.py)

**Files:**
- Create: `backend/core/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_auth.py` 끝에 추가:

```python
def test_hash_and_verify_password():
    from backend.core.auth import hash_password, verify_password
    h = hash_password("correct horse")
    assert h != "correct horse"          # 평문 저장 금지
    assert verify_password(h, "correct horse") is True
    assert verify_password(h, "wrong") is False
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_auth.py::test_hash_and_verify_password -v`
Expected: FAIL — `backend.core.auth` 없음

- [ ] **Step 3: core/auth.py 생성 (해싱 부분)**

`backend/core/auth.py` 생성:

```python
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _ph.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_auth.py::test_hash_and_verify_password -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/auth.py backend/tests/test_auth.py
git commit -m "[BE] auth: argon2 비밀번호 해싱"
```

---

## Task 4: 사용자/세션/초대 DB 헬퍼 (db.py)

**Files:**
- Modify: `backend/core/db.py` (끝에 함수 추가)
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_auth.py` 끝에 추가:

```python
import pytest


@pytest.mark.asyncio
async def test_user_db_helpers():
    from backend.core import db
    uid = await db.create_user("a@b.com", "hash1")
    assert isinstance(uid, int)
    by_email = await db.get_user_by_email("a@b.com")
    assert by_email["id"] == uid and by_email["password_hash"] == "hash1"
    by_id = await db.get_user_by_id(uid)
    assert by_id["email"] == "a@b.com"
    assert await db.get_user_by_email("missing@x.com") is None


@pytest.mark.asyncio
async def test_session_db_helpers():
    from backend.core import db
    uid = await db.create_user("s@b.com", "h")
    await db.create_session("tok-123", uid, ttl_hours=72)
    sess = await db.get_valid_session("tok-123")
    assert sess["user_id"] == uid
    await db.delete_session("tok-123")
    assert await db.get_valid_session("tok-123") is None


@pytest.mark.asyncio
async def test_expired_session_not_returned():
    from backend.core import db
    uid = await db.create_user("e@b.com", "h")
    await db.create_session("tok-exp", uid, ttl_hours=-1)  # 이미 만료
    assert await db.get_valid_session("tok-exp") is None


@pytest.mark.asyncio
async def test_invite_consume_once():
    from backend.core import db
    await db.create_invite("INV1")
    assert (await db.get_invite("INV1"))["used_by"] is None
    uid = await db.create_user("i@b.com", "h")
    assert await db.consume_invite("INV1", uid) is True
    assert await db.consume_invite("INV1", uid) is False  # 재사용 불가
    assert (await db.get_invite("INV1"))["used_by"] == uid
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_auth.py -k "db_helpers or invite or expired_session" -v`
Expected: FAIL — `create_user` 등 없음

- [ ] **Step 3: db.py에 헬퍼 추가**

`backend/core/db.py` 끝에 추가:

```python
# ── 인증: users / sessions / invites ──────────────────────────────────────

async def create_user(email: str, password_hash: str, role: str = "user") -> int:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        cursor = await conn.execute(
            "INSERT INTO users (email, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (email, password_hash, role, now),
        )
        await conn.commit()
        return int(cursor.lastrowid)


async def get_user_by_email(email: str) -> dict | None:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users WHERE email = ?", (email,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_by_id(user_id: int) -> dict | None:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_session(token: str, user_id: int, ttl_hours: int) -> None:
    now = _utc_now()
    expires_at = (now + timedelta(hours=ttl_hours)).isoformat()
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now.isoformat(), expires_at),
        )
        await conn.commit()


async def get_valid_session(token: str) -> dict | None:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT * FROM sessions WHERE token = ? AND expires_at > ?", (token, now)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_session(token: str) -> None:
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        await conn.commit()


async def create_invite(code: str) -> None:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            "INSERT INTO invites (code, created_at, used_by, used_at) VALUES (?, ?, NULL, NULL)",
            (code, now),
        )
        await conn.commit()


async def get_invite(code: str) -> dict | None:
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM invites WHERE code = ?", (code,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def consume_invite(code: str, user_id: int) -> bool:
    """미사용 초대코드면 사용 처리하고 True. 없거나 이미 사용됐으면 False."""
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        cursor = await conn.execute(
            "UPDATE invites SET used_by = ?, used_at = ? WHERE code = ? AND used_by IS NULL",
            (user_id, now, code),
        )
        await conn.commit()
        return (cursor.rowcount or 0) > 0
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_auth.py -k "db_helpers or invite or expired_session" -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/core/db.py backend/tests/test_auth.py
git commit -m "[BE] auth: users/sessions/invites DB 헬퍼"
```

---

## Task 5: get_current_user 의존성 (렌더 토큰 우회 포함)

**Files:**
- Modify: `backend/core/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_auth.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_get_current_user_with_valid_session():
    from starlette.requests import Request
    from backend.core import db
    from backend.core.auth import get_current_user
    uid = await db.create_user("c@b.com", "h")
    await db.create_session("sess-ok", uid, ttl_hours=72)
    scope = {"type": "http", "headers": [(b"cookie", b"session=sess-ok")]}
    user = await get_current_user(Request(scope))
    assert user["email"] == "c@b.com"


@pytest.mark.asyncio
async def test_get_current_user_no_cookie_raises_401():
    from fastapi import HTTPException
    from starlette.requests import Request
    from backend.core.auth import get_current_user
    scope = {"type": "http", "headers": []}
    with pytest.raises(HTTPException) as exc:
        await get_current_user(Request(scope))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_render_token_bypass(monkeypatch):
    from starlette.requests import Request
    from backend.core.config import settings
    from backend.core.auth import get_current_user
    monkeypatch.setattr(settings, "RENDER_TOKEN", "rt-secret")
    scope = {"type": "http", "headers": [(b"x-render-token", b"rt-secret")]}
    user = await get_current_user(Request(scope))
    assert user["role"] == "service"
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_auth.py -k "get_current_user" -v`
Expected: FAIL — `get_current_user` 없음

- [ ] **Step 3: auth.py에 의존성 추가**

`backend/core/auth.py` 끝에 추가:

```python
from fastapi import HTTPException, Request

from . import db
from .config import settings

_UNAUTH = HTTPException(
    status_code=401,
    detail={"code": "ERR-AUTH-001", "message": "인증이 필요합니다."},
)


async def get_current_user(request: Request) -> dict:
    # 내부 렌더 서비스(Playwright) 우회: 유효한 X-Render-Token이면 서비스 사용자로 통과
    rt = request.headers.get("x-render-token")
    if settings.RENDER_TOKEN and rt == settings.RENDER_TOKEN:
        return {"id": 0, "email": "__render__", "role": "service"}

    token = request.cookies.get("session")
    if not token:
        raise _UNAUTH
    sess = await db.get_valid_session(token)
    if sess is None:
        raise _UNAUTH
    user = await db.get_user_by_id(sess["user_id"])
    if user is None:
        raise _UNAUTH
    return user
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_auth.py -k "get_current_user" -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/core/auth.py backend/tests/test_auth.py
git commit -m "[BE] auth: get_current_user 의존성 + 렌더 토큰 우회"
```

---

## Task 6: auth 라우터 (signup/login/logout/me)

**Files:**
- Create: `backend/routers/auth.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_auth.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_signup_requires_valid_invite(client):
    resp = await client.post("/api/auth/signup", json={
        "email": "new@b.com", "password": "password1", "invite": "BAD"})
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ERR-AUTH-004"


@pytest.mark.asyncio
async def test_signup_with_invite_sets_cookie(client):
    from backend.core import db
    await db.create_invite("GOODCODE")
    resp = await client.post("/api/auth/signup", json={
        "email": "new@b.com", "password": "password1", "invite": "GOODCODE"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@b.com"
    assert "session" in resp.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email(client):
    from backend.core import db
    await db.create_invite("C1")
    await db.create_invite("C2")
    await client.post("/api/auth/signup", json={
        "email": "dup@b.com", "password": "password1", "invite": "C1"})
    resp = await client.post("/api/auth/signup", json={
        "email": "dup@b.com", "password": "password1", "invite": "C2"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "ERR-AUTH-003"


@pytest.mark.asyncio
async def test_login_success_and_me(client):
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("doc@b.com", hash_password("password1"))
    login = await client.post("/api/auth/login", json={
        "email": "doc@b.com", "password": "password1"})
    assert login.status_code == 200
    assert "session" in login.cookies
    me = await client.get("/api/auth/me")  # AsyncClient가 쿠키 유지
    assert me.status_code == 200
    assert me.json()["email"] == "doc@b.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("doc2@b.com", hash_password("password1"))
    resp = await client.post("/api/auth/login", json={
        "email": "doc2@b.com", "password": "WRONG"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "ERR-AUTH-005"


@pytest.mark.asyncio
async def test_me_without_login_401(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_session(client):
    from backend.core import db
    from backend.core.auth import hash_password
    await db.create_user("lo@b.com", hash_password("password1"))
    await client.post("/api/auth/login", json={"email": "lo@b.com", "password": "password1"})
    assert (await client.get("/api/auth/me")).status_code == 200
    await client.post("/api/auth/logout")
    assert (await client.get("/api/auth/me")).status_code == 401
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_auth.py -k "signup or login or logout or me" -v`
Expected: FAIL — `/api/auth/*` 404

- [ ] **Step 3: routers/auth.py 생성**

`backend/routers/auth.py` 생성:

```python
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from ..core import auth as auth_core
from ..core import db
from ..core.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "session"


class SignupBody(BaseModel):
    email: str
    password: str
    invite: str


class LoginBody(BaseModel):
    email: str
    password: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )


async def _start_session(response: Response, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    await db.create_session(token, user_id, settings.SESSION_TTL_HOURS)
    _set_session_cookie(response, token)
    return token


@router.post("/signup")
async def signup(body: SignupBody, response: Response):
    if len(body.password) < 8:
        raise HTTPException(400, detail={"code": "ERR-AUTH-002", "message": "비밀번호는 8자 이상이어야 합니다."})
    if await db.get_user_by_email(body.email) is not None:
        raise HTTPException(400, detail={"code": "ERR-AUTH-003", "message": "이미 사용 중인 이메일입니다."})
    invite = await db.get_invite(body.invite)
    if invite is None or invite["used_by"] is not None:
        raise HTTPException(403, detail={"code": "ERR-AUTH-004", "message": "유효하지 않은 초대코드입니다."})
    user_id = await db.create_user(body.email, auth_core.hash_password(body.password))
    await db.consume_invite(body.invite, user_id)
    await _start_session(response, user_id)
    return {"email": body.email}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    user = await db.get_user_by_email(body.email)
    if user is None or not auth_core.verify_password(user["password_hash"], body.password):
        raise HTTPException(401, detail={"code": "ERR-AUTH-005", "message": "이메일 또는 비밀번호가 올바르지 않습니다."})
    await _start_session(response, user["id"])
    return {"email": user["email"]}


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await db.delete_session(token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(auth_core.get_current_user)):
    return {"email": user["email"], "role": user["role"]}
```

- [ ] **Step 4: main.py에 auth 라우터 등록**

`backend/main.py`의 import 블록에서:

```python
from backend.routers import export, jobs, projects
```

을 다음으로 교체:

```python
from backend.routers import auth, export, jobs, projects
```

그리고 `app.include_router(jobs.router)` 줄 **위에** 추가:

```python
app.include_router(auth.router)
```

- [ ] **Step 5: 통과 확인**

Run: `pytest backend/tests/test_auth.py -k "signup or login or logout or me" -v`
Expected: PASS (7 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/routers/auth.py backend/main.py backend/tests/test_auth.py
git commit -m "[BE] auth: signup(초대코드)/login/logout/me 라우터"
```

---

## Task 7: 기존 라우터 보호 + 렌더 토큰 헤더 + 기존 테스트 우회

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/agents/s7_renderer.py:30-34`
- Modify: `backend/tests/test_api.py:25-31`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 실패 테스트 추가 (보호 + 우회)**

`backend/tests/test_auth.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_projects_requires_auth(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_render_token_bypasses_protected_route(client, monkeypatch):
    from backend.core.config import settings
    monkeypatch.setattr(settings, "RENDER_TOKEN", "rt-secret")
    resp = await client.get("/api/projects", headers={"X-Render-Token": "rt-secret"})
    assert resp.status_code == 200
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_auth.py -k "requires_auth or render_token_bypasses" -v`
Expected: FAIL — `/api/projects`가 아직 200(보호 안 됨)

- [ ] **Step 3: main.py에서 기존 라우터 보호**

`backend/main.py` 상단 import에 추가(`from fastapi import FastAPI` 아래):

```python
from fastapi import Depends

from backend.core.auth import get_current_user
```

그리고 라우터 등록부를 다음으로 교체:

```python
app.include_router(auth.router)
app.include_router(jobs.router, dependencies=[Depends(get_current_user)])
app.include_router(projects.router, dependencies=[Depends(get_current_user)])
app.include_router(export.router, dependencies=[Depends(get_current_user)])
```

- [ ] **Step 4: s7_renderer에 렌더 토큰 헤더 추가**

`backend/agents/s7_renderer.py`의 `browser_ctx = await browser.new_context(...)` 블록을 다음으로 교체:

```python
        extra_headers = {"X-Render-Token": settings.RENDER_TOKEN} if settings.RENDER_TOKEN else {}
        browser_ctx = await browser.new_context(
            viewport={"width": 1080, "height": 1200},  # 1080 클립 + 하단 여유 → dev 인디케이터가 클립 밖
            device_scale_factor=1,
            extra_http_headers=extra_headers,
        )
```

- [ ] **Step 5: 기존 API 테스트에 auth 우회 override 추가**

`backend/tests/test_api.py`의 `use_memory_db` 픽스처(25-31줄)를 다음으로 교체:

```python
@pytest_asyncio.fixture(autouse=True)
async def use_memory_db(tmp_path, monkeypatch):
    """각 테스트마다 독립된 SQLite 파일 사용 + auth 의존성 우회."""
    from backend.core.auth import get_current_user
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{db_file}")
    await _db.migrate()
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "test@test", "role": "user"}
    yield
    app.dependency_overrides.pop(get_current_user, None)
```

- [ ] **Step 6: 전체 백엔드 테스트 통과 확인**

Run: `pytest backend/tests/test_auth.py backend/tests/test_api.py -v`
Expected: PASS (test_auth 전체 + test_api 전체 — 401 없음)

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/agents/s7_renderer.py backend/tests/test_api.py backend/tests/test_auth.py
git commit -m "[BE] auth: 기존 라우터 보호 + S7 렌더 토큰 헤더 + 기존 테스트 우회"
```

---

## Task 8: 시드 / 초대코드 CLI 스크립트

**Files:**
- Create: `backend/scripts/seed_user.py`
- Create: `backend/scripts/create_invite.py`

- [ ] **Step 1: seed_user.py 생성**

`backend/scripts/seed_user.py` 생성:

```python
"""박사님 계정 시드.

사용법: python -m backend.scripts.seed_user <email> <password>
"""
from __future__ import annotations

import asyncio
import sys

from backend.core import db
from backend.core.auth import hash_password


async def main(email: str, password: str) -> None:
    await db.migrate()
    if await db.get_user_by_email(email) is not None:
        print(f"이미 존재: {email}")
        return
    uid = await db.create_user(email, hash_password(password), role="user")
    print(f"생성됨: id={uid} email={email}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python -m backend.scripts.seed_user <email> <password>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2]))
```

- [ ] **Step 2: create_invite.py 생성**

`backend/scripts/create_invite.py` 생성:

```python
"""초대코드 1개 생성 후 출력.

사용법: python -m backend.scripts.create_invite
"""
from __future__ import annotations

import asyncio
import secrets

from backend.core import db


async def main() -> None:
    await db.migrate()
    code = secrets.token_urlsafe(8)
    await db.create_invite(code)
    print(f"초대코드: {code}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: 시드 동작 확인 (임시 DB)**

Run (PowerShell): `$env:DATABASE_URL="sqlite:///seed_test.db"; python -m backend.scripts.seed_user doc@kitech.re.kr password123; python -m backend.scripts.create_invite; Remove-Item seed_test.db`
Expected: `생성됨: id=1 email=doc@kitech.re.kr` 그리고 `초대코드: <임의문자열>`

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/seed_user.py backend/scripts/create_invite.py
git commit -m "[BE] auth: 시드 계정/초대코드 CLI 스크립트"
```

---

## Task 9: 프론트 AuthForm 실연동 + invite 필드

**Files:**
- Modify: `web/src/components/auth/AuthForm.tsx`

- [ ] **Step 1: Errors 인터페이스에 invite 추가**

`web/src/components/auth/AuthForm.tsx`의 `interface Errors`에 `invite?: string;` 추가:

```tsx
interface Errors {
  email?: string;
  password?: string;
  confirm?: string;
  invite?: string;
  form?: string;
}
```

- [ ] **Step 2: invite 상태 추가**

`const [confirm, setConfirm] = useState('');` 다음 줄에 추가:

```tsx
  const [invite, setInvite]     = useState('');
```

- [ ] **Step 3: handleSubmit을 실제 fetch로 교체**

기존 `handleSubmit` 함수 전체를 다음으로 교체:

```tsx
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (!isLogin && !invite.trim()) {
      errs.invite = '초대코드를 입력해 주세요.';
    }
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/signup';
      const payload = isLogin
        ? { email, password }
        : { email, password, invite };
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data?.detail?.message
          ?? (isLogin ? '이메일 또는 비밀번호가 올바르지 않습니다.' : '회원가입에 실패했습니다.');
        setErrors({ form: msg });
        setLoading(false);
        return;
      }
      router.push('/dashboard');
    } catch {
      setErrors({ form: '서버에 연결할 수 없습니다.' });
      setLoading(false);
    }
  }
```

- [ ] **Step 4: invite 입력 필드 추가 (회원가입 전용)**

`비밀번호 확인` 필드 블록(`{!isLogin && ( ... )}`으로 감싼 `auth-confirm` div) 다음에 추가:

```tsx
        {!isLogin && (
          <div className="auth-field">
            <label htmlFor="auth-invite" className="auth-field__label">초대코드</label>
            <input
              id="auth-invite"
              type="text"
              className="auth-input"
              placeholder="발급받은 초대코드"
              value={invite}
              onChange={e => { setInvite(e.target.value); clearFieldError('invite'); }}
              aria-invalid={!!errors.invite || undefined}
              aria-describedby={errors.invite ? 'err-invite' : undefined}
            />
            {errors.invite && (
              <p className="auth-field__error" id="err-invite" role="alert">{errors.invite}</p>
            )}
          </div>
        )}
```

- [ ] **Step 5: 빌드/타입 확인**

Run: `npm run build --workspace=web`
Expected: 빌드 성공 (TypeScript 0 errors)

> 참고: "Google로 계속하기" 버튼은 v1 미구현이다. 지금은 그대로 두되 동작은 없음(스펙 Out of Scope). 별도 제거는 Plan 외 폴리시에서 처리.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/auth/AuthForm.tsx
git commit -m "[FE] auth: AuthForm 실제 로그인/가입 연동 + 초대코드 필드"
```

---

## Task 10: 프론트 AuthGuard + 로그아웃

**Files:**
- Create: `web/src/components/auth/AuthGuard.tsx`
- Create: `web/src/components/auth/LogoutButton.tsx`
- Modify: `web/src/app/dashboard/page.tsx`
- Modify: `web/src/app/editor/[jobId]/page.tsx`

- [ ] **Step 1: AuthGuard 컴포넌트 생성**

`web/src/components/auth/AuthGuard.tsx` 생성:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

// /api/auth/me로 세션 확인. 401이면 /login으로 리다이렉트.
// httpOnly 쿠키라 JS가 직접 못 읽으므로 서버에 확인 요청한다.
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => {
        if (cancelled) return;
        if (r.ok) setOk(true);
        else router.replace('/login');
      })
      .catch(() => { if (!cancelled) router.replace('/login'); });
    return () => { cancelled = true; };
  }, [router]);

  if (!ok) return null;
  return <>{children}</>;
}
```

- [ ] **Step 2: LogoutButton 컴포넌트 생성**

`web/src/components/auth/LogoutButton.tsx` 생성:

```tsx
'use client';

import { useRouter } from 'next/navigation';

export default function LogoutButton() {
  const router = useRouter();
  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    router.replace('/login');
  }
  return (
    <button type="button" className="btn btn-outline" onClick={handleLogout}>
      로그아웃
    </button>
  );
}
```

- [ ] **Step 3: dashboard 페이지를 AuthGuard로 래핑**

`web/src/app/dashboard/page.tsx` 상단 import에 추가:

```tsx
import AuthGuard from '@/components/auth/AuthGuard';
import LogoutButton from '@/components/auth/LogoutButton';
```

그리고 `export default function DashboardPage() {`를 다음으로 변경:

```tsx
function DashboardPageInner() {
```

파일 맨 끝에 래퍼 export 추가:

```tsx
export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardPageInner />
    </AuthGuard>
  );
}
```

`DashboardPageInner`의 최상위 헤더 영역(대시보드 제목이 있는 곳, 134줄 `return (` 이후 헤더 컨테이너)에 `<LogoutButton />`을 한 번 렌더한다.

- [ ] **Step 4: editor 페이지를 AuthGuard로 래핑**

`web/src/app/editor/[jobId]/page.tsx` 상단 import에 추가:

```tsx
import AuthGuard from '@/components/auth/AuthGuard'
```

그리고 `export default function EditorPage() {`를 다음으로 변경:

```tsx
function EditorPageInner() {
```

파일 맨 끝에 래퍼 export 추가:

```tsx
export default function EditorPage() {
  return (
    <AuthGuard>
      <EditorPageInner />
    </AuthGuard>
  )
}
```

- [ ] **Step 5: 빌드 확인**

Run: `npm run build --workspace=web`
Expected: 빌드 성공

- [ ] **Step 6: 수동 E2E 검증 (로컬)**

1. 백엔드 기동: `python -m uvicorn backend.main:app --port 8000` (별도 터미널)
2. 시드: `python -m backend.scripts.seed_user doc@kitech.re.kr password123`
3. 프론트 기동: `npm run dev --workspace=web`
4. 브라우저에서 `/dashboard` 접속 → `/login`으로 리다이렉트되는지 확인
5. `doc@kitech.re.kr` / `password123` 로그인 → 대시보드 진입 확인
6. 로그아웃 → 다시 `/login`으로 가는지 확인

Expected: 미로그인 시 차단, 로그인 시 진입, 로그아웃 동작

- [ ] **Step 7: Commit**

```bash
git add web/src/components/auth/AuthGuard.tsx web/src/components/auth/LogoutButton.tsx web/src/app/dashboard/page.tsx "web/src/app/editor/[jobId]/page.tsx"
git commit -m "[FE] auth: AuthGuard 라우트 가드 + 로그아웃 버튼"
```

---

## 후속 (이 플랜 범위 밖, 배포 시 필수 체크)

- 프로덕션에서 `.env`에 `COOKIE_SECURE=True`, `RENDER_TOKEN=<랜덤32자>` 설정 (Plan 3 배포에서 처리)
- S7 렌더가 프로덕션에서 동작하려면 `RENDER_TOKEN`이 백엔드 env와 Playwright 컨텍스트(같은 설정값) 모두에 적용됨 — 단일 프로세스라 자동 일치
- Next rewrite가 `X-Render-Token` 헤더를 백엔드로 전달하는지 배포 후 1회 E2E 확인(렌더 PNG 정상 생성)

## 다음 플랜

- Plan 2: 행동 로깅(`events` 테이블 + PostHog) — 사용자 귀속은 본 플랜의 `get_current_user` 사용
- Plan 3: 컨테이너화 + Oracle VM + Cloudflare Tunnel 배포
