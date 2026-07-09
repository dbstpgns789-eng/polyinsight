# L1 — BLOB → 파일시스템 (Storage 경계) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 무거운 바이너리 3종(card PNG·export ZIP·deck asset)을 SQLite BLOB에서 파일시스템으로 빼고 DB엔 `storage_key`만 남긴다. 파일 입출력은 단일 `Storage` 창구(async·원자적) 뒤로 숨긴다.

**Architecture:** `backend/core/storage.py`에 `Storage` 프로토콜 + `FilesystemStorage`(무상태·`os.replace` 원자 쓰기) 신설. `db.py`의 3개 save/get 함수가 `get_storage()`를 경유해 파일을 쓰고, 반환 dict의 BLOB 키(`zip_bytes`·`bytes`·`{card_num: bytes}`)를 storage.get 결과로 재조립해 라우터·`deck_renderer`를 무손상 유지. 하드 컷오버: 신규 DB는 `storage_key` 스키마로 생성, 기존 dev DB는 일회성 멱등 이주 스크립트로 데이터 이동 후 BLOB 컬럼 DROP.

**Tech Stack:** Python 3.10 · FastAPI · aiosqlite(SQLite 3.45) · pydantic-settings · pytest/pytest-asyncio.

**설계 스펙:** `docs/superpowers/specs/2026-07-09-l1-blob-to-filesystem-design.md` (v1.1, 적대 진단 17건 반영). 범위 = **실사용 3개 BLOB만** (`researchers.photo_bytes`는 읽기/쓰기 함수 없는 유령 컬럼 → 제외).

**테스트 실행 규칙:** 반드시 `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/ ...` (bare `pytest` 금지 — 죽은 스위트 실행). Windows Git Bash.

**커밋 규칙:** docs 변경 → 코드 변경 순서 엄수. 커밋 태그 `[DOCS]`/`[BE]`. 브랜치 `feat/emerald-redesign`(main 미머지). 커밋 푸시는 사용자 지시 시에만. 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Structure

| 파일 | 책임 | 작업 |
|---|---|---|
| `docs/contracts/07_api_data_model.md` | API·DB 스키마 정본 | Modify (BLOB→storage_key 표) |
| `docs/contracts/04_architecture.md` | 파이프라인·DDL | Modify (CREATE TABLE DDL) |
| `backend/core/config.py` | 설정 | Modify (STORAGE_DIR 필드) |
| `.gitignore` | | Modify (blobstore 제외) |
| `backend/core/storage.py` | **신설** — Storage 창구 | Create |
| `backend/core/db.py` | DB 접근 | Modify (스키마·3 save/get·delete·cleanup) |
| `backend/scripts/migrate_blobs_to_disk.py` | **신설** — 일회성 이주 | Create |
| `backend/scripts/backup_db.py` | 백업 | Modify (STORAGE_DIR 자산 백업) |
| `backend/tests/test_storage.py` | **신설** — Storage 단위 | Create |
| `backend/tests/test_blob_migration.py` | **신설** — 이주 스크립트 | Create |
| `backend/tests/test_api.py`·`test_events.py`·`test_security_hardening.py`·`test_deck_pipeline.py` | 픽스처 | Modify (STORAGE_DIR 주입) |

---

## Task 0: 계약 문서 먼저 (docs-first)

> 헌법 §4·§6·§7(docs-먼저). L0 교훈(문서 표류) 반복 금지. **코드보다 먼저 커밋.**

**Files:**
- Modify: `docs/contracts/07_api_data_model.md` (BLOB 스키마 표)
- Modify: `docs/contracts/04_architecture.md:328,337` (CREATE TABLE DDL)

- [ ] **Step 1: 07의 deck_assets/card_images/exports BLOB 표기를 storage_key로 갱신**

`07_api_data_model.md`에서 `deck_assets.bytes = BLOB`(주변 :444) 및 card_images/exports 스키마 표를 찾아, BLOB 컬럼 행을 다음처럼 정정하고 각 표 위에 1줄 주석 추가:
```
> L1(2026-07-09): 바이너리는 파일시스템(Storage)로 이주. 이 컬럼은 storage_key TEXT(파일 주소)다.
```
- `card_images.png_bytes BLOB` → `card_images.storage_key TEXT  # 파일: jobs/{job_id}/cards/{n}.png`
- `exports.zip_bytes BLOB` → `exports.storage_key TEXT  # 파일: jobs/{job_id}/exports/{id}.zip`
- `deck_assets.bytes BLOB` → `deck_assets.storage_key TEXT  # 파일: jobs/{job_id}/assets/{id}`

- [ ] **Step 2: 04의 CREATE TABLE DDL 갱신**

`04_architecture.md`의 `card_images ( ... png_bytes BLOB ... )`(:328 부근)·`exports ( ... zip_bytes BLOB ... )`(:337 부근) DDL에서 BLOB 컬럼을 `storage_key TEXT`로 바꾸고, 표 근처에 1줄:
```
# L1(2026-07-09): 바이너리는 Storage(파일시스템)로 이관. DB엔 storage_key(주소)만. researchers.photo_bytes는 미사용 유령 컬럼(범위 밖).
```

- [ ] **Step 3: Commit**

```bash
git add docs/contracts/07_api_data_model.md docs/contracts/04_architecture.md
git commit -m "$(printf '[DOCS] L1 — 계약문서 BLOB→storage_key 반영 (코드 선행)\n\n07/04의 card_images·exports·deck_assets 스키마를 storage_key로 갱신.\nL1 구현의 docs-먼저 단계(헌법 §4/§7).\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 1: config STORAGE_DIR + .gitignore

**Files:**
- Modify: `backend/core/config.py:22` 부근 (EXPORT_TTL_HOURS 근처)
- Modify: `.gitignore`

- [ ] **Step 1: STORAGE_DIR 필드 추가**

`backend/core/config.py`의 `Settings` 안, `EXPORT_TTL_HOURS: int = 24` 다음 줄에 추가:
```python
    # L1(2026-07-09): 바이너리 파일 저장 루트. 프로덕션은 레포 밖 마운트 볼륨으로 .env override
    # (예: /var/lib/polyinsight/blobstore — 24_system_architecture §4 "호스트 디스크 볼륨").
    STORAGE_DIR: str = "backend/var/blobstore"
```

- [ ] **Step 2: .gitignore에 blobstore 추가**

`.gitignore` 끝에 추가:
```
# L1 파일 스토리지 (유저 업로드·렌더 산출물 — git 대상 아님)
backend/var/
```

- [ ] **Step 3: import 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -c "from backend.core.config import settings; print(settings.STORAGE_DIR)"`
Expected: `backend/var/blobstore`

- [ ] **Step 4: Commit**

```bash
git add backend/core/config.py .gitignore
git commit -m "$(printf '[BE] L1 — STORAGE_DIR 설정 + blobstore gitignore\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 2: Storage 창구 (`storage.py`) — TDD

**Files:**
- Create: `backend/core/storage.py`
- Test: `backend/tests/test_storage.py`

- [ ] **Step 1: 실패 테스트 작성**

Create `backend/tests/test_storage.py`:
```python
"""Storage 창구 단위 테스트 — 파일시스템 라운드트립·원자성·안전성."""
from __future__ import annotations

import asyncio

import pytest

from backend.core import storage as storage_mod
from backend.core.config import settings


@pytest.fixture(autouse=True)
def tmp_storage(tmp_path, monkeypatch):
    # 무상태 접근자라 settings 라이브 read → 테스트별 tmp 격리.
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))


@pytest.mark.asyncio
async def test_put_get_roundtrip():
    s = storage_mod.get_storage()
    await s.put("jobs/j1/cards/1.png", b"\x89PNG-hello")
    assert await s.get("jobs/j1/cards/1.png") == b"\x89PNG-hello"


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    s = storage_mod.get_storage()
    assert await s.get("nope/missing.bin") is None


@pytest.mark.asyncio
async def test_delete_is_idempotent():
    s = storage_mod.get_storage()
    await s.put("a/b.bin", b"x")
    await s.delete("a/b.bin")
    await s.delete("a/b.bin")  # 두 번째도 예외 없이 통과
    assert await s.get("a/b.bin") is None


@pytest.mark.asyncio
async def test_delete_prefix_removes_subtree_only():
    s = storage_mod.get_storage()
    await s.put("jobs/j1/cards/1.png", b"a")
    await s.put("jobs/j1/exports/e.zip", b"b")
    await s.put("jobs/j2/cards/1.png", b"c")
    await s.delete_prefix("jobs/j1")
    assert await s.get("jobs/j1/cards/1.png") is None
    assert await s.get("jobs/j1/exports/e.zip") is None
    assert await s.get("jobs/j2/cards/1.png") == b"c"  # 다른 job은 무사


@pytest.mark.asyncio
async def test_concurrent_put_same_key_no_torn_file():
    # 원자적 쓰기(temp+os.replace)라 동시 put에도 온전한 한 파일만 남는다.
    s = storage_mod.get_storage()
    payloads = [bytes([i]) * 100_000 for i in range(1, 9)]
    await asyncio.gather(*(s.put("jobs/j/cards/1.png", p) for p in payloads))
    result = await s.get("jobs/j/cards/1.png")
    assert result in payloads          # 찢어진 혼합 바이트가 아니라 어느 하나의 완전본
    assert len(result) == 100_000


@pytest.mark.asyncio
async def test_key_traversal_blocked():
    s = storage_mod.get_storage()
    with pytest.raises(ValueError):
        await s.put("../escape.bin", b"x")
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_storage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.core.storage'`

- [ ] **Step 3: storage.py 구현**

Create `backend/core/storage.py`:
```python
"""파일 저장 단일 창구 (L1 — Storage 경계).

async 시그니처 = R2 등 네트워크 백엔드가 나중에 같은 계약으로 끼워지게 하는 이유(L5).
get_storage()는 무상태 — 매 호출 settings.STORAGE_DIR 라이브 read (db._db_path 패턴).
이 무캐시 속성이 테스트 격리(monkeypatch로 tmp 주입)를 성립시킨다.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from pathlib import Path
from typing import Protocol

from .config import settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> None: ...
    async def delete_prefix(self, prefix: str) -> None: ...


class FilesystemStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        # 키는 앱이 uuid로 생성하지만 '..' 탈출 방어.
        dest = (self._root / key).resolve()
        if dest != self._root and self._root not in dest.parents:
            raise ValueError(f"unsafe storage key: {key!r}")
        return dest

    def _put_sync(self, key: str, data: bytes) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f"{dest.name}.{uuid.uuid4().hex}.tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)  # 같은 파일시스템 내 rename = 원자적(POSIX·Windows)

    def _get_sync(self, key: str) -> bytes | None:
        try:
            with open(self._path(key), "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _delete_sync(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass

    def _delete_prefix_sync(self, prefix: str) -> None:
        shutil.rmtree(self._path(prefix), ignore_errors=True)

    async def put(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(self._put_sync, key, data)

    async def get(self, key: str) -> bytes | None:
        return await asyncio.to_thread(self._get_sync, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_sync, key)

    async def delete_prefix(self, prefix: str) -> None:
        await asyncio.to_thread(self._delete_prefix_sync, prefix)


def get_storage() -> FilesystemStorage:
    return FilesystemStorage(settings.STORAGE_DIR)
```

> 참고: `_path`는 동기 함수라 `put`이 스레드에 들어가기 전(traversal 검증)에도, 스레드 안에서도 동작한다. `test_key_traversal_blocked`는 `to_thread` 안에서 `ValueError`가 전파되는지 확인한다(asyncio가 스레드 예외를 재던짐).

- [ ] **Step 4: 통과 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_storage.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/core/storage.py backend/tests/test_storage.py
git commit -m "$(printf '[BE] L1 — Storage 창구(FilesystemStorage) + 단위테스트\n\n무상태 get_storage(settings 라이브 read) + 원자적 put(temp+os.replace).\nasync 계약으로 L5(R2) 박스교체 대비.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 3: 테스트 픽스처에 STORAGE_DIR 주입

> db.py를 storage 경유로 바꾸기 전에, 기존 라운드트립 테스트가 tmp 디스크를 쓰도록 픽스처부터 준비. 이 단계 후엔 기존 테스트가 (아직 db가 안 바뀌었으니) 여전히 통과해야 한다.

**Files:**
- Modify: `backend/tests/test_api.py` (`use_memory_db` 픽스처)
- Modify: `backend/tests/test_events.py` (`mem_db` 픽스처)
- Modify: `backend/tests/test_security_hardening.py` (`mem_db` 픽스처)
- Modify: `backend/tests/test_deck_pipeline.py` (DB 픽스처 — 있으면)

- [ ] **Step 1: 각 DB 픽스처에 STORAGE_DIR 주입**

각 파일에서 `monkeypatch.setattr(settings, "DATABASE_URL", ...)` 줄 바로 아래에 추가:
```python
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blobstore"))
```
(`test_deck_pipeline.py`에 tmp_path 기반 DB 픽스처가 있으면 동일 적용. 없고 `_db`를 직접 쓰면 그 픽스처의 tmp_path에 맞춰 주입.)

- [ ] **Step 2: 전체 스위트 여전히 green 확인 (db 미변경 상태)**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/ -q`
Expected: PASS (기존 개수 그대로 — STORAGE_DIR 주입은 아직 아무 db 함수도 안 씀)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_api.py backend/tests/test_events.py backend/tests/test_security_hardening.py backend/tests/test_deck_pipeline.py
git commit -m "$(printf '[BE] L1 — 테스트 픽스처에 STORAGE_DIR(tmp) 주입 (db 라우팅 준비)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 4: db card_images → storage_key

**Files:**
- Modify: `backend/core/db.py` — CREATE TABLE card_images(:67-73), idempotent ALTER(:177 부근), `save_card_image`(:479-498), `get_card_images`(:511-528), `delete_card_images_above`(:501-508)
- Test: `backend/tests/test_api.py::test_card_image_returns_png` (기존, 회귀 가드)

- [ ] **Step 1: 실패 테스트 — storage_key 저장 검증 추가**

`backend/tests/test_api.py`의 `test_card_image_returns_png` 아래에 추가:
```python
@pytest.mark.asyncio
async def test_card_image_stored_on_disk_not_blob(tmp_path):
    """L1: save_card_image는 파일로 쓰고 DB엔 storage_key만 — png_bytes 컬럼 미사용."""
    from backend.core import storage as _storage
    job_id = await _new_job()
    await _db.save_card_image(job_id, card_num=1, png_bytes=b"\x89PNG-disk")
    # 파일이 결정적 키에 존재
    assert await _storage.get_storage().get(f"jobs/{job_id}/cards/1.png") == b"\x89PNG-disk"
    # get_card_images는 여전히 {card_num: bytes} 반환
    imgs = await _db.get_card_images(job_id)
    assert imgs == {1: b"\x89PNG-disk"}
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py::test_card_image_stored_on_disk_not_blob -q`
Expected: FAIL (아직 png_bytes BLOB에 저장, storage 파일 없음 → get None)

- [ ] **Step 3: CREATE TABLE + ALTER 갱신**

`db.py`의 `CREATE TABLE IF NOT EXISTS card_images (`(:67) 블록에서 `png_bytes BLOB,` 줄을 `storage_key TEXT,` 로 교체.

`migrate()`의 idempotent 블록(:191 `email_verified` ALTER 다음, `await conn.commit()` 앞)에 추가:
```python
        # L1(2026-07-09): BLOB→파일시스템. 기존 DB에 storage_key 없으면 추가(멱등).
        for _tbl in ("card_images", "exports", "deck_assets"):
            async with conn.execute(f"PRAGMA table_info({_tbl})") as cur:
                _cols = [row[1] for row in await cur.fetchall()]
            if "storage_key" not in _cols:
                await conn.execute(f"ALTER TABLE {_tbl} ADD COLUMN storage_key TEXT")
```

- [ ] **Step 4: save_card_image / get_card_images / delete_card_images_above 교체**

`save_card_image`(:479-498) 본문을 교체:
```python
async def save_card_image(
    job_id: str,
    card_num: int,
    png_bytes: bytes,
    ttl_hours: int = 24,
) -> None:
    key = f"jobs/{job_id}/cards/{card_num}.png"
    await get_storage().put(key, png_bytes)   # 원자적 — 동시 재렌더 same-key 안전
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with _connect() as conn:
        await conn.execute(
            "DELETE FROM card_images WHERE job_id = ? AND card_num = ?",
            (job_id, card_num),
        )
        await conn.execute(
            "INSERT INTO card_images (job_id, card_num, storage_key, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (job_id, card_num, key, expires_at),
        )
        await conn.commit()
```

`get_card_images`(:511-528) 교체:
```python
async def get_card_images(job_id: str) -> dict[int, bytes]:
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT card_num, storage_key FROM card_images "
            "WHERE job_id = ? AND expires_at > ?",
            (job_id, now),
        ) as cursor:
            rows = await cursor.fetchall()
    storage = get_storage()
    images: dict[int, bytes] = {}
    for row in rows:
        if row["storage_key"]:
            data = await storage.get(row["storage_key"])
            if data is not None:
                images[row["card_num"]] = data
    return images
```

`delete_card_images_above`(:501-508) 교체 (파일도 삭제):
```python
async def delete_card_images_above(job_id: str, max_card_num: int) -> None:
    """card_num > max_card_num 카드 삭제(편집으로 카드 수 감소 시 잔재 정리) — 파일도 제거."""
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT storage_key FROM card_images WHERE job_id = ? AND card_num > ?",
            (job_id, max_card_num),
        ) as cur:
            keys = [r["storage_key"] for r in await cur.fetchall() if r["storage_key"]]
        await conn.execute(
            "DELETE FROM card_images WHERE job_id = ? AND card_num > ?",
            (job_id, max_card_num),
        )
        await conn.commit()
    storage = get_storage()
    for k in keys:
        await storage.delete(k)
```

`db.py` 상단 import에 추가 (파일 맨 위 `from .config import settings` 아래):
```python
from .storage import get_storage
```

- [ ] **Step 5: 통과 확인 (신규 + 기존 회귀)**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py -q -k "card_image or partial_render"`
Expected: PASS (신규 disk 테스트 + 기존 `test_card_image_returns_png` + `test_partial_render_does_not_delete_valid_higher_card`)

- [ ] **Step 6: Commit**

```bash
git add backend/core/db.py backend/tests/test_api.py
git commit -m "$(printf '[BE] L1 — card_images BLOB→storage_key (파일시스템 라우팅)\n\nsave/get/delete_above가 Storage 경유. get_card_images 반환형 {card_num: bytes} 보존.\n원자적 put으로 자가치유 동시 재렌더 same-key 안전.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 5: db exports → storage_key (반환 `zip_bytes` 키 보존)

**Files:**
- Modify: `backend/core/db.py` — CREATE TABLE exports(:75-82), `save_export`(:531-555), `get_export`(:558-570)
- Test: `backend/tests/test_api.py::test_export_download_returns_zip` (기존, 회귀 가드)

- [ ] **Step 1: 실패 테스트 — export 디스크 저장 + zip_bytes 키 보존**

`test_export_download_returns_zip` 아래에 추가:
```python
@pytest.mark.asyncio
async def test_export_stored_on_disk_and_key_preserved():
    """L1: save_export는 파일로, get_export는 여전히 dict['zip_bytes']로 바이트 반환."""
    job_id = await _new_job()
    await _db.save_export("exp1", job_id, b"PK-zipdata", "out.zip")
    row = await _db.get_export("exp1")
    assert row["zip_bytes"] == b"PK-zipdata"   # export.py download_zip이 쓰는 키
    assert row["filename"] == "out.zip"
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py::test_export_stored_on_disk_and_key_preserved -q`
Expected: FAIL

- [ ] **Step 3: CREATE TABLE + save/get 교체**

CREATE TABLE exports(:78)의 `zip_bytes BLOB,` → `storage_key TEXT,`.

`save_export`(:531-555) 교체:
```python
async def save_export(
    export_job_id: str,
    job_id: str,
    zip_bytes: bytes,
    filename: str,
    ttl_hours: int = 24,
) -> None:
    key = f"jobs/{job_id}/exports/{export_job_id}.zip"
    await get_storage().put(key, zip_bytes)
    now = _utc_now_iso()
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO exports (
                export_job_id, job_id, storage_key, filename, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(export_job_id) DO UPDATE SET
                job_id = excluded.job_id,
                storage_key = excluded.storage_key,
                filename = excluded.filename,
                expires_at = excluded.expires_at,
                created_at = excluded.created_at
            """,
            (export_job_id, job_id, key, filename, expires_at, now),
        )
        await conn.commit()
```

`get_export`(:558-570) 교체 (반환 dict에 `zip_bytes` 키 재조립):
```python
async def get_export(export_job_id: str) -> dict | None:
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT export_job_id, job_id, storage_key, filename, expires_at, created_at "
            "FROM exports WHERE export_job_id = ? AND expires_at > ?",
            (export_job_id, now),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["zip_bytes"] = await get_storage().get(row["storage_key"]) if row["storage_key"] else None
    return d
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py -q -k "export"`
Expected: PASS (신규 + `test_export_download_returns_zip` + `test_export_download_expired`)

- [ ] **Step 5: Commit**

```bash
git add backend/core/db.py backend/tests/test_api.py
git commit -m "$(printf '[BE] L1 — exports BLOB→storage_key (반환 zip_bytes 키 보존)\n\nget_export가 storage.get 결과를 dict[zip_bytes]로 재조립 → export.py download_zip 무수정.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 6: db deck_assets → storage_key (반환 `bytes`/`mime` 키 보존)

**Files:**
- Modify: `backend/core/db.py` — CREATE TABLE deck_assets(:161-174), `save_deck_asset`(:381-411), `get_deck_asset`(:414-425)
- Test: `backend/tests/test_api.py::test_upload_deck_asset_and_serve` (기존, 회귀 가드)

- [ ] **Step 1: 실패 테스트 — deck_asset 디스크 저장 + bytes/mime 키 보존**

`test_upload_deck_asset_and_serve` 아래에 추가:
```python
@pytest.mark.asyncio
async def test_deck_asset_stored_on_disk_and_keys_preserved():
    """L1: save_deck_asset는 파일로, get_deck_asset는 dict['bytes']/['mime'] 보존."""
    job_id = await _new_job()
    await _db.save_deck_asset(job_id, "a1", b"\x89PNG-asset", "image/png")
    row = await _db.get_deck_asset(job_id, "a1")
    assert row["bytes"] == b"\x89PNG-asset"   # deck.py·deck_renderer가 쓰는 키
    assert row["mime"] == "image/png"
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py::test_deck_asset_stored_on_disk_and_keys_preserved -q`
Expected: FAIL

- [ ] **Step 3: CREATE TABLE + save/get 교체**

CREATE TABLE deck_assets(:164)의 `bytes BLOB,` → `storage_key TEXT,`.

`save_deck_asset`(:381-411) 본문 교체 (시그니처 유지, 저장만 storage로):
```python
async def save_deck_asset(
    job_id: str,
    asset_id: str,
    data: bytes,
    mime: str,
    source_type: str = "upload-owned",
    source_url: str | None = None,
    provider: str | None = None,
    credit: str | None = None,
    credit_url: str | None = None,
    ttl_hours: int = 24 * 30,  # 덱 수명 정합. 재편집까지 생존.
) -> None:
    key = f"jobs/{job_id}/assets/{asset_id}"
    await get_storage().put(key, data)
    now = _utc_now_iso()
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with _connect() as conn:
        await conn.execute(
            """
            INSERT INTO deck_assets (
                asset_id, job_id, storage_key, mime, source_type, source_url,
                provider, credit, credit_url, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, asset_id) DO UPDATE SET
                storage_key = excluded.storage_key, mime = excluded.mime,
                source_type = excluded.source_type, source_url = excluded.source_url,
                provider = excluded.provider, credit = excluded.credit,
                credit_url = excluded.credit_url, expires_at = excluded.expires_at
            """,
            (asset_id, job_id, key, mime, source_type, source_url,
             provider, credit, credit_url, now, expires_at),
        )
        await conn.commit()
```

`get_deck_asset`(:414-425) 교체 (반환 dict에 `bytes` 키 재조립):
```python
async def get_deck_asset(job_id: str, asset_id: str) -> dict | None:
    now = _utc_now_iso()
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT asset_id, storage_key, mime, source_type, source_url, provider, "
            "credit, credit_url FROM deck_assets "
            "WHERE job_id = ? AND asset_id = ? AND expires_at > ?",
            (job_id, asset_id, now),
        ) as cursor:
            row = await cursor.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["bytes"] = await get_storage().get(row["storage_key"]) if row["storage_key"] else None
    return d
```

> `list_deck_assets`(:428-437)는 바이트를 반환하지 않으므로 **무수정**(storage_key 컬럼과 무관, mime/source_type만 SELECT).

- [ ] **Step 4: 통과 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py -q -k "deck_asset"`
Expected: PASS (신규 + `test_upload_deck_asset_and_serve` + reject/oversized/404 등 기존)

- [ ] **Step 5: Commit**

```bash
git add backend/core/db.py backend/tests/test_api.py
git commit -m "$(printf '[BE] L1 — deck_assets BLOB→storage_key (반환 bytes/mime 키 보존)\n\nget_deck_asset가 storage.get을 dict[bytes]로 재조립 → deck.py 서빙·deck_renderer 인라인 무수정.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 7: delete_job 통삭제 + cleanup 파일삭제 + deck_assets 만료

**Files:**
- Modify: `backend/core/db.py` — `delete_job`(:466-476), `cleanup_expired_blobs`(:573-600)
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 실패 테스트 — delete_job 파일 제거 + cleanup 파일 제거**

`test_api.py`에 추가:
```python
@pytest.mark.asyncio
async def test_delete_job_removes_files():
    """L1: delete_job은 job 하위 파일(cards·assets)을 delete_prefix로 통삭제."""
    from backend.core import storage as _storage
    job_id = await _new_job()
    await _db.save_card_image(job_id, 1, b"\x89PNG")
    await _db.save_deck_asset(job_id, "a1", b"asset", "image/png")
    s = _storage.get_storage()
    assert await s.get(f"jobs/{job_id}/cards/1.png") is not None
    await _db.delete_job(job_id)
    assert await s.get(f"jobs/{job_id}/cards/1.png") is None
    assert await s.get(f"jobs/{job_id}/assets/a1") is None


@pytest.mark.asyncio
async def test_cleanup_expired_deletes_card_and_asset_files():
    """L1: cleanup_expired_blobs는 만료 card·export·deck_asset 행과 파일을 함께 제거."""
    from backend.core import storage as _storage
    job_id = await _new_job()
    # 이미 만료된 카드·자산(ttl 음수)
    await _db.save_card_image(job_id, 1, b"\x89PNG", ttl_hours=-1)
    await _db.save_deck_asset(job_id, "a1", b"asset", "image/png", ttl_hours=-1)
    s = _storage.get_storage()
    await _db.cleanup_expired_blobs()
    assert await s.get(f"jobs/{job_id}/cards/1.png") is None
    assert await s.get(f"jobs/{job_id}/assets/a1") is None
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py -q -k "removes_files or cleanup_expired_deletes"`
Expected: FAIL

- [ ] **Step 3: delete_job 교체**

`delete_job`(:466-476)에서 `return` 앞(commit 뒤)에 파일 통삭제 추가:
```python
async def delete_job(job_id: str) -> bool:
    """job과 연관 데이터(card_data·card_images·exports·authored_deck·deck_assets) 일괄 삭제 + 파일."""
    async with _connect() as conn:
        await conn.execute("DELETE FROM card_images WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM deck_assets WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM card_data WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM exports WHERE job_id = ?", (job_id,))
        await conn.execute("DELETE FROM authored_deck WHERE job_id = ?", (job_id,))
        cursor = await conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        await conn.commit()
        existed = (cursor.rowcount or 0) > 0
    await get_storage().delete_prefix(f"jobs/{job_id}")   # cards·exports·assets 파일 통삭제
    return existed
```

- [ ] **Step 4: cleanup_expired_blobs 교체 (파일 삭제 + deck_assets 만료)**

`cleanup_expired_blobs`(:573-600) 교체:
```python
async def cleanup_expired_blobs() -> int:
    now = _utc_now_iso()
    storage = get_storage()
    deleted = 0
    async with _connect() as conn:
        conn.row_factory = aiosqlite.Row
        # 만료 파일 키를 먼저 수집(행 삭제 전) — card_images·exports·deck_assets.
        keys: list[str] = []
        for _tbl in ("card_images", "exports", "deck_assets"):
            async with conn.execute(
                f"SELECT storage_key FROM {_tbl} WHERE expires_at <= ?", (now,)
            ) as cur:
                keys += [r["storage_key"] for r in await cur.fetchall() if r["storage_key"]]
        for _tbl in ("card_images", "exports", "deck_assets"):
            cursor = await conn.execute(
                f"DELETE FROM {_tbl} WHERE expires_at <= ?", (now,)
            )
            deleted += cursor.rowcount or 0
        # 만료 세션·인증 토큰 정리(기존 유지).
        cursor = await conn.execute(
            "DELETE FROM sessions WHERE expires_at <= ?", (now,)
        )
        deleted += cursor.rowcount or 0
        cursor = await conn.execute(
            "DELETE FROM auth_tokens WHERE expires_at <= ? OR used_at IS NOT NULL", (now,)
        )
        deleted += cursor.rowcount or 0
        await conn.commit()
    for k in keys:
        await storage.delete(k)
    return deleted
```

- [ ] **Step 5: 통과 확인 (신규 + 기존 delete_job cascade)**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_api.py -q -k "delete_job or cleanup_expired"`
Expected: PASS (신규 2 + 기존 `test_delete_job_cascade`)

- [ ] **Step 6: Commit**

```bash
git add backend/core/db.py backend/tests/test_api.py
git commit -m "$(printf '[BE] L1 — delete_job 파일 통삭제 + cleanup 파일삭제/deck_assets 만료\n\ndelete_prefix로 job 하위 통삭제. cleanup_expired_blobs가 key SELECT 후 파일 삭제,\ndeck_assets 만료도 처리(기존 누락 표면화).\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 8: 이주 스크립트 (기존 dev DB — 멱등) + 테스트

**Files:**
- Create: `backend/scripts/migrate_blobs_to_disk.py`
- Test: `backend/tests/test_blob_migration.py`

- [ ] **Step 1: 실패 테스트 작성**

Create `backend/tests/test_blob_migration.py`:
```python
"""BLOB→파일 이주 스크립트 — 구스키마 BLOB 행을 디스크로 옮기고 storage_key 세팅, 멱등."""
from __future__ import annotations

import aiosqlite
import pytest

from backend.core import db as _db
from backend.core import storage as _storage
from backend.core.config import settings
from backend.scripts.migrate_blobs_to_disk import migrate_blobs


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{tmp_path/'m.db'}")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "blob"))


async def _seed_old_card_row(job_id: str, card_num: int, png: bytes):
    # 구스키마: png_bytes 컬럼이 있고 storage_key는 비어있는 상태를 재현.
    async with aiosqlite.connect(_db._db_path()) as conn:
        await conn.execute("ALTER TABLE card_images ADD COLUMN png_bytes BLOB")
        await conn.execute(
            "INSERT INTO card_images (job_id, card_num, png_bytes, storage_key, expires_at) "
            "VALUES (?, ?, ?, NULL, ?)",
            (job_id, card_num, png, "2999-01-01T00:00:00"),
        )
        await conn.commit()


@pytest.mark.asyncio
async def test_migrate_moves_blob_to_disk_and_is_idempotent():
    await _db.migrate()
    await _db.create_job("j1", "p.pdf", user_id=1)
    await _seed_old_card_row("j1", 1, b"\x89PNG-old")

    moved = await migrate_blobs()
    assert moved >= 1
    # 파일이 디스크에, storage_key 세팅, BLOB 컬럼 제거됨
    assert await _storage.get_storage().get("jobs/j1/cards/1.png") == b"\x89PNG-old"
    imgs = await _db.get_card_images("j1")
    assert imgs == {1: b"\x89PNG-old"}
    async with aiosqlite.connect(_db._db_path()) as conn:
        async with conn.execute("PRAGMA table_info(card_images)") as cur:
            cols = [r[1] for r in await cur.fetchall()]
    assert "png_bytes" not in cols     # 컬럼 drop 확인

    # 재실행 멱등 — 이미 이주됨, 예외 없이 0건
    again = await migrate_blobs()
    assert again == 0
```

- [ ] **Step 2: 실패 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_blob_migration.py -q`
Expected: FAIL — `ModuleNotFoundError: ... migrate_blobs_to_disk`

- [ ] **Step 3: 이주 스크립트 구현**

Create `backend/scripts/migrate_blobs_to_disk.py`:
```python
"""L1 일회성 이주 — SQLite BLOB(card_images·exports·deck_assets)을 Storage(파일)로 이동.

멱등: storage_key가 이미 있는 행은 skip. 전 행 이주 후 BLOB 컬럼 DROP.
운영: 서버 정지 → (backup_db) → 이 스크립트 → 새 코드 배포 → 기동.

사용법(루트에서): PYTHONUTF8=1 .venv/Scripts/python.exe -m backend.scripts.migrate_blobs_to_disk
"""
from __future__ import annotations

import asyncio

import aiosqlite

from backend.core import db as _db
from backend.core.storage import get_storage

# (테이블, BLOB 컬럼, 키 생성기(row)->key)
_SPECS = [
    ("card_images", "png_bytes", lambda r: f"jobs/{r['job_id']}/cards/{r['card_num']}.png"),
    ("exports", "zip_bytes", lambda r: f"jobs/{r['job_id']}/exports/{r['export_job_id']}.zip"),
    ("deck_assets", "bytes", lambda r: f"jobs/{r['job_id']}/assets/{r['asset_id']}"),
]


async def _has_column(conn: aiosqlite.Connection, table: str, col: str) -> bool:
    async with conn.execute(f"PRAGMA table_info({table})") as cur:
        return col in [row[1] for row in await cur.fetchall()]


async def migrate_blobs() -> int:
    """BLOB 행을 파일로 이동. 반환=이동 건수. 멱등(재실행 시 남은 것만)."""
    await _db.migrate()   # storage_key 컬럼 보장(멱등 ALTER)
    storage = get_storage()
    moved = 0
    for table, blob_col, keyfn in _SPECS:
        async with aiosqlite.connect(_db._db_path()) as conn:
            conn.row_factory = aiosqlite.Row
            if not await _has_column(conn, table, blob_col):
                continue  # 이미 이주 완료(컬럼 drop됨)
            async with conn.execute(
                f"SELECT * FROM {table} "
                f"WHERE storage_key IS NULL AND {blob_col} IS NOT NULL"
            ) as cur:
                rows = [dict(r) for r in await cur.fetchall()]
            for r in rows:
                key = keyfn(r)
                await storage.put(key, r[blob_col])
                moved += 1
            # storage_key 세팅 (PK로 각 행 지목). 테이블별 PK 다름.
            if rows:
                async with aiosqlite.connect(_db._db_path()) as wconn:
                    for r in rows:
                        if table == "card_images":
                            await wconn.execute(
                                "UPDATE card_images SET storage_key=? WHERE job_id=? AND card_num=?",
                                (keyfn(r), r["job_id"], r["card_num"]),
                            )
                        elif table == "exports":
                            await wconn.execute(
                                "UPDATE exports SET storage_key=? WHERE export_job_id=?",
                                (keyfn(r), r["export_job_id"]),
                            )
                        else:  # deck_assets
                            await wconn.execute(
                                "UPDATE deck_assets SET storage_key=? WHERE job_id=? AND asset_id=?",
                                (keyfn(r), r["job_id"], r["asset_id"]),
                            )
                    await wconn.commit()
            # 전 행 이주 후 BLOB 컬럼 DROP(sqlite ≥3.35).
            async with aiosqlite.connect(_db._db_path()) as dconn:
                async with dconn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {blob_col} IS NOT NULL AND storage_key IS NULL"
                ) as cur:
                    remaining = (await cur.fetchone())[0]
                if remaining == 0:
                    await dconn.execute(f"ALTER TABLE {table} DROP COLUMN {blob_col}")
                    await dconn.commit()
    return moved


async def _main() -> None:
    n = await migrate_blobs()
    print(f"이주 완료: {n}건 파일로 이동, BLOB 컬럼 정리됨.")


if __name__ == "__main__":
    asyncio.run(_main())
```

- [ ] **Step 4: 통과 확인**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/test_blob_migration.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/migrate_blobs_to_disk.py backend/tests/test_blob_migration.py
git commit -m "$(printf '[BE] L1 — BLOB→파일 일회성 이주 스크립트(멱등) + 테스트\n\ncard_images·exports·deck_assets BLOB을 Storage로 이동, storage_key 세팅, BLOB 컬럼 DROP.\n재실행 멱등(이주된 행 skip). researchers는 유령이라 범위 밖.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 9: 백업 확장 (STORAGE_DIR 영속 자산)

**Files:**
- Modify: `backend/scripts/backup_db.py`

- [ ] **Step 1: 자산 백업 함수 추가**

`backup_db.py`의 `backup(...)` 함수 다음에 추가 (표준 라이브러리만 사용):
```python
def backup_assets(storage_dir: str, dest: str) -> str | None:
    """영속 자산(jobs/*/assets/)만 tar.gz 스냅샷. TTL 재생성 가능한 cards/·exports/는 제외.
    반환=스냅샷 경로 또는 대상 없음 시 None."""
    import tarfile
    src_root = os.path.join(storage_dir, "jobs")
    if not os.path.isdir(src_root):
        print(f"자산 백업 대상 없음: {src_root}")
        return None
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, f"assets_{datetime.now():%Y%m%d_%H%M%S}.tar.gz")
    count = 0
    with tarfile.open(out, "w:gz") as tar:
        for job in os.listdir(src_root):
            adir = os.path.join(src_root, job, "assets")
            if os.path.isdir(adir):
                tar.add(adir, arcname=os.path.join("jobs", job, "assets"))
                count += 1
    print(f"자산 백업: {out} (job {count}개 assets)")
    return out
```

- [ ] **Step 2: __main__에서 자산 백업도 호출 + 복원 런북 갱신**

`backup_db.py`의 `if __name__ == "__main__":` 블록에서 `backup(...)` 호출 성공 뒤에 추가:
```python
        from backend.core.config import settings as _settings
        backup_assets(_settings.STORAGE_DIR, args.dest)
```
docstring "복원 리허설" 6단계 뒤에 추가:
```
  7. (L1) backups/assets_*.tar.gz 를 STORAGE_DIR에 풀기: tar xzf assets_YYYYMMDD_HHMMSS.tar.gz -C <STORAGE_DIR>
     ⚠️ DB 스냅샷과 같은 시점 쌍으로 복원 — storage_key(DB)와 파일이 어긋나면 dangling.
```

- [ ] **Step 3: 스모크 확인 (수동 실행 — 자산 폴더 없으면 None)**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -c "from backend.scripts.backup_db import backup_assets; print(backup_assets('backend/var/blobstore', 'backups'))"`
Expected: `자산 백업 대상 없음: ...` → `None` (아직 자산 없음 — 정상)

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/backup_db.py
git commit -m "$(printf '[BE] L1 — 백업에 STORAGE_DIR 영속 자산(assets) 포함\n\nL1이 유저 업로드를 DB 밖으로 빼며 생긴 백업 공백 차단.\ncards/exports는 TTL 재생성 가능이라 제외. 복원 런북에 파일 복원 단계 추가.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 10: 전체 검증 + 라이브 E2E

**Files:** (없음 — 통합 검증만)

- [ ] **Step 1: 전체 스위트 green**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m pytest backend/tests/ -q`
Expected: PASS (기존 + 신규 storage/migration/roundtrip 테스트 전부)

- [ ] **Step 2: 앱 import + tsc**

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -c "import backend.main; print('OK')"`
Expected: `OK`
Run (web 무관하지만 회귀 확인): `cd web && npx tsc --noEmit; echo exit=$?`
Expected: `exit=0` (프론트는 L1과 무관 — 참고 확인)

- [ ] **Step 3: 라이브 E2E — 업로드→렌더→서빙→export가 디스크 경유로 실동작**

verify 스킬로 실제 앱 구동해 확인 (backend 8000 + web 3000 기동, DEV_MOCK_LLM 사용 가능). 관찰 포인트:
- deck 업로드 후 카드 PNG가 `backend/var/blobstore/jobs/<job>/cards/*.png`에 파일로 생김 (DB엔 BLOB 없음)
- deck 뷰어에서 카드 이미지 정상 표시 (get_deck_card → get_card_images → storage.get)
- deck asset 업로드 후 `.../assets/<id>` 파일 생성 + 뷰어 인라인 정상
- export 후 다운로드 ZIP 정상 (get_export → zip_bytes 재조립)

Run(파일 생성 확인 예): `ls backend/var/blobstore/jobs/*/cards/ 2>/dev/null && echo "files on disk OK"`

- [ ] **Step 4: 이주 스크립트 실행(로컬 dev DB) — 선택**

> 로컬 dev DB(`./polyinsight.db`)에 기존 BLOB이 있으면 이주. 배포 미실행이라 대개 폐기 가능하나, 보존하려면:

Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m backend.scripts.backup_db --min-bytes 1000`
Run: `PYTHONUTF8=1 .venv/Scripts/python.exe -m backend.scripts.migrate_blobs_to_disk`
Expected: `이주 완료: N건 ...` (또는 신규 스키마면 0건)

- [ ] **Step 5: 마무리 커밋 (있으면) + 메모리 갱신**

검증 로그 외 코드 변경이 없으면 커밋 불필요. 세션 마무리 시 메모리 `project_system_architecture_northstar.md`에 L1 완료 반영.

---

## Self-Review 체크 (계획 작성자 수행)

- **스펙 커버리지**: §1 범위3(researchers 제외)=Task4-6·8 · §3-1 무상태/원자=Task2 · §4 키계약=Task4-6 · §4 TTL파일삭제+deck_assets만료=Task7 · §5 멱등이주=Task8 · §7 파일백업=Task9 · §8 docs먼저=Task0 · config STORAGE_DIR=Task1 · OSError정책=upload 라우터는 기존 400/500 경로 유지(별도 하드닝 불요, put 실패는 500으로 표면화 — 스펙 §3-2 렌더 경로 이미 try/except). ✅ 전 항목 태스크 존재.
- **플레이스홀더**: 없음(모든 코드 블록 실체).
- **타입 일관성**: `get_storage()`·`FilesystemStorage`·키 스킴(`jobs/{job_id}/cards/{n}.png` 등) Task 전반 동일. 반환 키(`zip_bytes`/`bytes`/`{card_num: bytes}`) 소비자와 일치.
- **주의(구현자)**: Task4-6는 같은 CREATE TABLE executescript 블록을 순차 편집한다 — 각 BLOB 줄만 바꾸고 다른 줄 건드리지 말 것. `db.py` 상단 `from .storage import get_storage` import는 Task4에서 1회만 추가.
