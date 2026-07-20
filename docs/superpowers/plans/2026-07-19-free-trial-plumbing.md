# 무료체험 배관 (Export-Gate 순수잠금) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 신규 유저가 가입 즉시 카드뉴스 1덱을 **끝까지 만들어 보고 검증까지 확인**할 수 있게 하되, **파일로 내보내는 것과 2번째 덱 생성은 결제 뒤로 잠근다**.

**Architecture:** users 테이블에 영속 컬럼 3개(`plan` / `free_decks_used` / `onboarded_at`)를 추가하고, 게이트 판정을 `backend/core/plans.py` 단일 모듈에 모은다. 게이트는 두 지점에만 붙는다 — **생성 진입점 1곳**(원가 방어)과 **파일이 실제로 나가는 export 경로 4곳**(가치 벽). 뷰어가 카드를 화면에 보여주는 inline 이미지 경로는 **의도적으로 열어둔다**(순수잠금 = 다 보이되 못 가져감). 무료 1덱은 업로드 시 선차감하고 파이프라인이 ERROR로 끝나면 환불한다(아하 보장).

**Tech Stack:** FastAPI + aiosqlite(ORM 없음, raw SQL) / Next.js 15 App Router + TypeScript / pytest(backend/tests) + vitest(web, node 환경·순수 로직만)

---

## 이 플랜이 **하지 않는** 것 (명시적 스코프 밖)

| 항목 | 이유 |
|---|---|
| Creem 결제 연동 (체크아웃·웹훅·구독 상태 동기화) | API 키 없음 + 가격 미확정. `/upgrade`는 이번엔 **정적 안내 페이지**까지만. 플랜 결제 성공 시 `plan` 컬럼을 바꾸는 건 후속 플랜. |
| 가격 숫자 확정 | "원가부터 낮추고 결정"(2026-07-16). `/upgrade`엔 `가안` 칩 + 금액 자리표시 유지. |
| 월 리셋 쿼터 / 크레딧 탑업 | 유료 플랜 내부 규칙. 무료=평생 1회만 이번 스코프. |

### ✅ 해소됨 — "알려진 구멍"(원본 해상도 유출)은 Task 13에서 막는다

> **2026-07-20 개정.** 최초 작성 시 이 구멍을 스코프 밖에 뒀으나, 재검토 결과 **렌더 파이프라인을 건드릴 필요가 없었다.** 서빙 레이어에서 리사이즈하면 된다(Pillow는 `backend/agents/deck/layout_audit.py:23`에서 이미 쓰는 기존 의존성). Task 13 참조.

`GET /api/cards/{job_id}/image/{card_num}`(`backend/routers/export.py:39`)와 `GET /api/deck/{job_id}/cards/{card_num}`(`backend/routers/deck.py:251`)는 **뷰어가 화면에 카드를 보여주는 경로**라 402 게이트를 걸지 않는다(걸면 무료 유저 뷰어가 빈 화면이 되고 아하가 죽는다). 그런데 이 둘은 현재 **export와 동일한 원본 해상도 PNG**를 그대로 서빙한다 — URL을 직접 열어 우클릭 저장하면 유료 산출물과 같은 파일을 얻는다.

"화질 격차가 방어막"이라는 무료체험 모델의 전제가 **코드에서 성립하지 않는 상태**이므로, Task 13에서 무료 유저에게만 축소본을 서빙해 전제를 성립시킨다. 게이트(402)가 아니라 **해상도 차등**이라는 점이 핵심 — 보이는 건 그대로 다 보인다.

### 🚨 배포 전 필수 확인 — 백필이 실유저를 영구 면제시킬 수 있다

Task 1의 마이그레이션은 **`plan` 컬럼이 없던 DB의 모든 유저를 `plan='lab'`(게이트 영구 면제)으로 백필**한다. 근거는 "컬럼이 없는 DB = 게이트 도입 전부터 쓰던 내부·테스트 계정"이라는 가정이다.

그런데 이 서비스는 **이미 프로덕션에 떠 있고**(Azure VM `20.210.112.15`, `https://polyinsight.japaneast.cloudapp.azure.com`) 실유저가 `/signup`으로 가입 중이다. `migrate()`는 `backend/main.py:53`에서 **매 startup마다 자동 호출**되므로, 이 코드가 포함된 배포가 프로덕션에서 처음 뜨는 순간 **그때까지 가입한 전원**이 조건 없이 평생 무제한 무료가 된다. 코드는 이 가정을 강제하지 않는다 — 배포 타이밍에 전적으로 의존한다.

**배포 전에 반드시 할 것:**

```bash
ssh -i ~/Downloads/polyinsight_key.pem azureuser@20.210.112.15 \
  "sqlite3 ~/polyinsight/polyinsight.db 'SELECT id, email, role, created_at FROM users ORDER BY id;'"
```

명단을 눈으로 보고 판단한다:
- 전부 내부·테스트 계정이면 → 그대로 배포 (백필 의도대로)
- 실유저가 섞여 있으면 → 배포 **전에** 백필 대상을 좁히거나(예: 특정 id 목록만 `lab`), 배포 직후 SQL로 정정한다

이 확인 없이 배포하면 되돌리기 어렵다(누가 원래 `lab`이었는지 사후에 구분 불가).

---

## File Structure

| 파일 | 상태 | 책임 |
|---|---|---|
| `docs/contracts/07_api_data_model.md` | 수정 | users 스키마 3컬럼 + `402` 에러코드 + `/api/auth/me` 응답 확장 기록 |
| `web/CLAUDE.md` | 수정 | §7 NEVER의 "Export 하드블록 금지"를 **fidelity 축**으로 한정, **플랜 게이트 축**을 신설 |
| `backend/core/db.py` | 수정 | DDL 3컬럼 + 멱등 ALTER + 백필 + 헬퍼 3개 |
| `backend/core/plans.py` | **신규** | 게이트 판정 단일 소스 (`can_author` / `can_export` / `require_*`) |
| `backend/routers/deck.py` | 수정 | 생성 게이트 + 선차감, export 게이트 |
| `backend/routers/export.py` | 수정 | export 게이트 2곳 |
| `backend/routers/jobs.py` | 수정 | 레거시 export 게이트 |
| `backend/agents/deck/pipeline.py` | 수정 | 실패 시 무료 1덱 환불 (`_log_done` 한 곳) |
| `backend/routers/auth.py` | 수정 | `/me` 응답 확장 + `POST /api/auth/onboarded` |
| `backend/tests/test_free_trial.py` | **신규** | 게이트·차감·환불 전 경로 |
| `backend/tests/test_api.py` | 수정 | 의존성 오버라이드 유저에 `plan` 추가 (기존 테스트 보호) |
| `web/src/lib/plan.ts` | **신규** | 플랜 상태 파생 로직 (순수 함수 — vitest 대상) |
| `web/src/lib/plan.test.ts` | **신규** | 위 로직 테스트 |
| `web/src/lib/api.ts` | 수정 | 인터셉터가 `code`/`status` 보존 |
| `web/src/app/onboarding/page.tsx` | **신규** | 첫 방문 환영 화면 (1회) |
| `web/src/components/auth/AuthGuard.tsx` | 수정 | 온보딩 미시청이면 `/onboarding`으로 |
| `web/src/app/dashboard/page.tsx` | 수정 | 무료 미터 + 덱 카드 잠금 배지 + 게이트된 새 덱 |
| `web/src/components/deck/DeckExportModal.tsx` | 수정 | 402면 페이월 렌더 |
| `web/src/app/upgrade/page.tsx` | **신규** | 요금 안내 (가안) |
| `backend/main.py` | 수정 | **Task 12** — 402 예외 핸들러에서 `plan_gate_hit` 단일 기록 |
| `backend/scripts/funnel_report.py` | **신규** | **Task 12** — 퍼널 판독(가입→업로드→완성→벽 히트). T1 트리거 숫자 산출 |
| `backend/core/images.py` | **신규** | **Task 13** — 무료 유저용 PNG 축소(서빙 레이어, Pillow) |

---

## Task 0: docs 먼저 (헌법 §4 — docs 변경 → 코드 변경 순서 엄수)

**Files:**
- Modify: `web/CLAUDE.md:112` (§7 NEVER 블록)
- Modify: `docs/contracts/07_api_data_model.md`

이 태스크에 테스트는 없다. 문서가 코드보다 먼저 나가야 한다는 헌법 규칙(`CLAUDE.md` §4, §7 `NEVER skip docs/ update before code change`)을 지키기 위한 선행 태스크다.

- [ ] **Step 1: `web/CLAUDE.md` §7 NEVER 항목을 두 축으로 분리**

현재 `web/CLAUDE.md`의 §7 NEVER 블록에 이 줄이 있다:

```
NEVER  Export에 하드블록 구현 — 경고 후 진행만 허용
```

이 줄을 **아래 두 줄로 교체**한다:

```
NEVER  Export에 **fidelity 하드블록** 구현 (CRITICAL 리스크·미검토 항목) — 경고 후 진행만 허용, 최종 판단은 사용자
NEVER  **플랜 게이트**(무료체험 export 잠금)를 fidelity 경고와 같은 UI로 취급 — 전자는 의도된 벽(결제로 열림), 후자는 사용자 판단권(막으면 안 됨)
```

같은 파일 §2 "핵심 규칙"의 이 줄:

```
- Export preflight는 CRITICAL/unreviewed 항목에 **경고**만, 하드블록 금지 — 최종 판단은 사용자
```

바로 아래에 한 줄 추가:

```
- **플랜 게이트는 별개 축** — 무료 플랜의 export 잠금은 하드블록이 정상(결제로 열리는 벽). fidelity 경고와 섞지 말 것
```

그리고 같은 파일 맨 아래 `⚠️ Learned Mistakes` 표에 행 추가:

```
| 2026-07-19 | 무료체험 배관 | §7 NEVER "Export 하드블록 금지"가 fidelity 축 규칙인데 문구가 일반적이라, 결제 게이트 구현이 헌법 위반처럼 보였음 | 규칙을 쓸 땐 **어느 축에 대한 금지인지** 명시한다. "하드블록 금지"는 사용자 판단권(fidelity) 이야기지 비즈니스 게이트 금지가 아니다 |
```

- [ ] **Step 2: `docs/contracts/07_api_data_model.md`에 스키마·에러·엔드포인트 기록**

먼저 파일을 읽어 users 테이블 스키마가 기술된 섹션과 에러코드 표를 찾는다. 해당 users 스키마 정의에 컬럼 3개를 추가 기술한다:

```
plan             TEXT NOT NULL DEFAULT 'free'   -- free | pro | lab
free_decks_used  INTEGER NOT NULL DEFAULT 0     -- 무료 체험 소진 카운터 (평생 리셋 없음)
onboarded_at     TEXT                            -- NULL이면 환영 온보딩 미시청
```

에러코드 표에 2행 추가:

```
| ERR-PLAN-AUTHOR | 402 | 무료 체험 1덱 소진 — 추가 생성은 업그레이드 필요 |
| ERR-PLAN-EXPORT | 402 | 무료 플랜 — 파일 내보내기는 업그레이드 필요 |
```

API 목록에 `GET /api/auth/me` 응답 확장과 신규 엔드포인트를 기술한다:

```
GET  /api/auth/me
  응답: { email, role, emailVerified, plan, freeDecksUsed, freeDeckLimit, canAuthor, canExport, onboarded }

POST /api/auth/onboarded
  환영 온보딩 시청 완료 표시 (멱등 — 이미 표시됐으면 그대로 200)
  응답: { ok: true }
```

문서 하단에 설계 근거 한 단락 추가:

```
무료체험 게이트 (2026-07-19) — 무료 = 1덱 "보기 전용". 생성·뷰어·편집·검증 배지는 전부 열려
있고(아하 = 검증 완료 배지, 이것은 게이팅 금지), 파일이 실제로 나가는 export 경로만 잠근다.
뷰어의 inline 카드 이미지 경로(`/api/cards/{job}/image/{n}`, `/api/deck/{job}/cards/{n}`)는
화면 표시용이므로 게이트하지 않는다. 무료 1덱은 업로드 시 선차감하고, 파이프라인이 ERROR로
끝나면 환불한다 — 실패로 아하를 못 본 유저가 영구히 막히는 것을 막기 위함.
```

- [ ] **Step 3: 커밋**

```bash
git add web/CLAUDE.md docs/contracts/07_api_data_model.md
git commit -m "[DOCS] 무료체험 게이트 계약 — users 3컬럼·402 에러·플랜게이트를 fidelity 하드블록과 분리"
```

---

## Task 1: DB 컬럼 3개 + 헬퍼

**Files:**
- Modify: `backend/core/db.py:99-106` (users DDL), `backend/core/db.py:198-202` 뒤 (멱등 ALTER)
- Modify: `backend/core/db.py` 끝부분 (헬퍼 3개 추가)
- Test: `backend/tests/test_free_trial.py` (신규)

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_free_trial.py`를 새로 만든다:

```python
"""무료체험 배관 — 스키마·차감·환불·게이트."""
from __future__ import annotations

import pytest
import pytest_asyncio

from backend.core import db as _db
from backend.core.config import settings


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
    """유료 유저는 무료 카운터를 소비하지 않는다 (게이트 대상이 아님)."""
    uid = await _mk_user("pro@test")
    await _db.set_plan(uid, "pro")
    await _db.consume_free_deck(uid)
    assert (await _db.get_user_by_id(uid))["free_decks_used"] == 0


@pytest.mark.asyncio
async def test_mark_onboarded_is_idempotent():
    uid = await _mk_user()
    await _db.mark_onboarded(uid)
    first = (await _db.get_user_by_id(uid))["onboarded_at"]
    assert first is not None
    await _db.mark_onboarded(uid)
    assert (await _db.get_user_by_id(uid))["onboarded_at"] == first
```

**주의:** `create_user`의 실제 시그니처를 `backend/core/db.py`에서 먼저 확인하고, 위 `_mk_user` 헬퍼를 실제 시그니처에 맞춘다(인자 개수·이름이 다르면 그에 맞게 수정). 시그니처만 맞추고 나머지 단언은 그대로 둔다.

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest backend/tests/test_free_trial.py -v
```

기대: 5개 전부 FAIL. `test_new_user_defaults_to_free_with_zero_used`는 `KeyError: 'plan'`, 나머지는 `AttributeError: module 'backend.core.db' has no attribute 'consume_free_deck'`.

- [ ] **Step 3: DDL에 컬럼 추가**

`backend/core/db.py:99-106`의 users DDL을 아래로 교체한다 (기존 6컬럼 뒤에 3줄 추가):

```python
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                free_decks_used INTEGER NOT NULL DEFAULT 0,
                onboarded_at TEXT
            );
```

- [ ] **Step 4: 멱등 ALTER + 기존 유저 백필 추가**

`backend/core/db.py:202`의 `email_verified` ALTER 블록 **바로 뒤**, `storage_key` 루프(`db.py:203`) **앞**에 삽입한다:

```python
        # 무료체험 게이트(2026-07-19) — users에 plan/free_decks_used/onboarded_at 멱등 추가.
        # ★기존 유저 백필: 이 컬럼들이 없던 DB = 게이트 도입 전부터 쓰던 계정(내부·테스트).
        #   전원 plan='lab'(게이트 면제) + onboarded_at=now(환영 온보딩 안 뜸)로 백필한다.
        #   안 하면 기존 유저가 전부 무료로 강등되고 온보딩을 다시 본다.
        async with conn.execute("PRAGMA table_info(users)") as cur:
            ucols2 = [row[1] for row in await cur.fetchall()]
        if "plan" not in ucols2:
            await conn.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
            await conn.execute("UPDATE users SET plan = 'lab'")
        if "free_decks_used" not in ucols2:
            await conn.execute("ALTER TABLE users ADD COLUMN free_decks_used INTEGER NOT NULL DEFAULT 0")
        if "onboarded_at" not in ucols2:
            await conn.execute("ALTER TABLE users ADD COLUMN onboarded_at TEXT")
            await conn.execute("UPDATE users SET onboarded_at = ?", (_utc_now_iso(),))
```

- [ ] **Step 5: 헬퍼 4개 추가**

`backend/core/db.py`의 `set_email_verified`(`db.py:893-896`) 바로 아래에 추가한다:

```python
async def consume_free_deck(user_id: int, limit: int = 1) -> bool:
    """무료 체험 1회를 원자적으로 소비. 성공하면 True.

    UPDATE 한 문장 안에서 잔여 검사까지 하므로 check-then-act 레이스가 없다
    (동시 업로드 2건이 둘 다 통과하면 원가 방어 벽이 뚫린다).
    free 플랜이 아니거나 잔여가 없으면 아무 것도 바꾸지 않고 False.
    """
    async with _connect() as conn:
        cur = await conn.execute(
            "UPDATE users SET free_decks_used = free_decks_used + 1 "
            "WHERE id = ? AND plan = 'free' AND free_decks_used < ?",
            (user_id, limit),
        )
        await conn.commit()
        return cur.rowcount > 0


async def refund_free_deck(user_id: int) -> None:
    """파이프라인 실패 시 선차감 환불. 0 아래로 내려가지 않는다."""
    async with _connect() as conn:
        await conn.execute(
            "UPDATE users SET free_decks_used = MAX(0, free_decks_used - 1) "
            "WHERE id = ? AND plan = 'free'",
            (user_id,),
        )
        await conn.commit()


async def set_plan(user_id: int, plan: str) -> None:
    async with _connect() as conn:
        await conn.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, user_id))
        await conn.commit()


async def mark_onboarded(user_id: int) -> None:
    """환영 온보딩 시청 표시. 이미 표시됐으면 시각을 덮어쓰지 않는다(멱등)."""
    async with _connect() as conn:
        await conn.execute(
            "UPDATE users SET onboarded_at = ? WHERE id = ? AND onboarded_at IS NULL",
            (_utc_now_iso(), user_id),
        )
        await conn.commit()
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
pytest backend/tests/test_free_trial.py -v
```

기대: 5 passed.

- [ ] **Step 7: 전체 스위트 회귀 확인**

```bash
pytest backend/tests/
```

기대: 기존 통과 개수 + 5. 실패가 있으면 다음 태스크로 넘어가지 말고 원인을 보고할 것.

- [ ] **Step 8: 커밋**

```bash
git add backend/core/db.py backend/tests/test_free_trial.py
git commit -m "[BE] users에 plan/free_decks_used/onboarded_at — 멱등 ALTER + 기존유저 lab 백필"
```

---

## Task 2: 게이트 판정 코어 (`plans.py`)

**Files:**
- Create: `backend/core/plans.py`
- Test: `backend/tests/test_free_trial.py` (append)

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_free_trial.py` 맨 아래에 추가한다:

```python
# ── 게이트 판정 ────────────────────────────────────────────────────────────
from fastapi import HTTPException

from backend.core import plans


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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest backend/tests/test_free_trial.py -v
```

기대: 새 테스트 8개가 `ModuleNotFoundError: No module named 'backend.core.plans'`로 수집 단계에서 실패.

- [ ] **Step 3: `backend/core/plans.py` 작성**

```python
"""플랜 게이트 — 무료체험(export-gate 순수잠금)의 판정 단일 소스.

무료 = 1덱 "보기 전용". 생성·뷰어·편집·검증 배지는 전부 열려 있고(아하),
파일이 실제로 나가는 export 경로만 잠근다. 벽은 두 겹이고 역할이 다르다:
  - export 게이트   = 가치 벽 (WTP가 최고조인 지점)
  - 생성 1회 상한   = 원가 방어 (덱 1건 ≈ $1)

주의: 유저 dict는 항상 DB row라고 가정하지 않는다. X-Render-Token 서비스 유저
(backend/core/auth.py:69)는 {"id","email","role"} 3키뿐이라 plan 키가 없다.
전부 .get()으로 읽고, 서비스 롤은 게이트 면제다.
"""
from __future__ import annotations

from fastapi import HTTPException

FREE_DECK_LIMIT = 1
PAID_PLANS = ("pro", "lab")


def _is_exempt(user: dict) -> bool:
    """내부 렌더 서비스 — 게이트 대상 아님."""
    return user.get("role") == "service"


def plan_of(user: dict) -> str:
    return user.get("plan") or "free"


def free_decks_used(user: dict) -> int:
    return int(user.get("free_decks_used") or 0)


def can_author(user: dict) -> bool:
    """새 덱을 만들 수 있나 — 무료는 평생 FREE_DECK_LIMIT회."""
    if _is_exempt(user) or plan_of(user) in PAID_PLANS:
        return True
    return free_decks_used(user) < FREE_DECK_LIMIT


def can_export(user: dict) -> bool:
    """파일로 내보낼 수 있나 — 무료는 절대 불가(순수잠금, 워터마크 타협 없음)."""
    if _is_exempt(user):
        return True
    return plan_of(user) in PAID_PLANS


def author_gate_error() -> HTTPException:
    """생성 게이트 402. 읽기 판정(require_can_author)과 원자적 소비 실패가
    같은 응답을 내야 프론트가 한 가지 분기만 다루면 된다."""
    return HTTPException(
        status_code=402,
        detail={
            "code": "ERR-PLAN-AUTHOR",
            "message": "무료 체험 1덱을 모두 사용했어요. 업그레이드하면 계속 만들 수 있어요.",
        },
    )


def export_gate_error() -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "code": "ERR-PLAN-EXPORT",
            "message": "내보내기는 업그레이드 후 이용할 수 있어요. 만든 카드뉴스는 그대로 보관돼요.",
        },
    )


def require_can_author(user: dict) -> None:
    if not can_author(user):
        raise author_gate_error()


def require_can_export(user: dict) -> None:
    if not can_export(user):
        raise export_gate_error()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest backend/tests/test_free_trial.py -v
```

기대: 13 passed.

- [ ] **Step 5: 커밋**

```bash
git add backend/core/plans.py backend/tests/test_free_trial.py
git commit -m "[BE] plans.py — 무료체험 게이트 판정 단일 소스(402 ERR-PLAN-*)"
```

---

## Task 3: 생성 게이트 배선 + 선차감

**Files:**
- Modify: `backend/routers/deck.py:17` (import), `backend/routers/deck.py:64` (게이트), `backend/routers/deck.py:77` 뒤 (선차감)
- Test: `backend/tests/test_free_trial.py` (append)

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_free_trial.py` 맨 아래에 추가한다. 이 테스트는 HTTP 레이어를 타므로 `client` 픽스처와 의존성 오버라이드가 필요하다:

```python
# ── 생성 게이트 (HTTP) ─────────────────────────────────────────────────────
import io

from httpx import ASGITransport, AsyncClient

from backend.core.auth import get_current_user
from backend.main import app


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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest backend/tests/test_free_trial.py -v -k upload
```

기대: `test_free_user_first_upload_accepted`가 선차감 단언에서 FAIL(`0 == 1`), `test_free_user_second_upload_blocked_with_402`가 402 대신 202를 받아 FAIL.

- [ ] **Step 3: 게이트와 선차감 배선**

`backend/routers/deck.py:17`의 import를 수정한다:

```python
from ..core import db, plans, ratelimit
```

`backend/routers/deck.py:64` (`ratelimit.enforce_upload_quota(user)` 줄)를 아래 2줄로 교체한다:

```python
    plans.require_can_author(user)         # 플랜 게이트 — 무료 1덱 상한(원가 방어)
    ratelimit.enforce_upload_quota(user)   # 유저별 일일 쿼터(재정 DoS) — 플랜과 별개 축
```

`backend/routers/deck.py:77`의 `await db.create_job(...)` **바로 뒤**에 선차감을 넣는다:

```python
    await db.create_job(job_id, title=file.filename, user_id=user["id"])
    # 무료 체험 선차감 — **원자적**으로 소비한다.
    # require_can_author는 읽은 스냅샷 기반이라 동시 요청 2건이 둘 다 통과할 수 있다
    # (check-then-act). 실제 상한 강제는 이 UPDATE 한 문장이 담당한다.
    # 파이프라인이 ERROR로 끝나면 pipeline._log_done에서 환불한다(아하 보장).
    if plans.plan_of(user) == "free":
        if not await db.consume_free_deck(user["id"], plans.FREE_DECK_LIMIT):
            raise plans.author_gate_error()   # 레이스에서 진 요청
```

**주의:** `consume_free_deck`은 `bool`을 반환한다(Task 1에서 원자적 조건부 소비로 구현됨 — `WHERE ... AND free_decks_used < ?` + `rowcount`). 유료 유저에게는 호출하지 않는다(호출해도 `False`가 나오는데 그건 실패가 아니라 no-op이라 의미가 뒤섞인다).

`plans.author_gate_error()`는 Task 2에서 `require_can_author`가 던지는 것과 **같은 402 예외 객체**를 반환하는 헬퍼다. Task 2 구현 시 예외 생성을 헬퍼로 분리해 두 곳이 같은 응답을 내도록 한다.

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest backend/tests/test_free_trial.py -v
```

기대: 15 passed.

- [ ] **Step 5: 커밋**

```bash
git add backend/routers/deck.py backend/tests/test_free_trial.py
git commit -m "[BE] 생성 게이트 — 무료 1덱 상한 + 업로드 시 선차감"
```

---

## Task 4: 실패 시 환불

**Files:**
- Modify: `backend/agents/deck/pipeline.py:108-127` (`_log_done`)
- Test: `backend/tests/test_free_trial.py` (append)

`_log_done`은 파이프라인 종료 경로 **5곳 전부**(실패 4 + 성공 1)에서 호출되고 이미 `final = await db.get_job(job_id)`로 최종 상태를 읽는다. 환불 훅을 여기 한 곳에만 넣으면 모든 실패 경로가 커버된다.

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_free_trial.py` 맨 아래에 추가한다:

```python
# ── 실패 환불 ──────────────────────────────────────────────────────────────
from backend.agents.deck import pipeline as _pipeline
from backend.core.models import JobStatus


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
```

**주의:** `db.update_job`의 실제 시그니처를 `backend/core/db.py:273` 근처에서 확인하고 인자를 맞춘다.

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest backend/tests/test_free_trial.py -v -k refund
```

기대: `test_failed_pipeline_refunds_the_free_deck`가 `1 == 0`으로 FAIL. `test_successful_pipeline_does_not_refund`는 이미 PASS(환불 코드가 없으니).

- [ ] **Step 3: `_log_done`에 환불 추가**

`backend/agents/deck/pipeline.py:110`의 `final = await db.get_job(job_id)` 바로 뒤에 삽입한다:

```python
    final = await db.get_job(job_id)
    # 무료 체험 환불 — 실패로 끝난 잡은 선차감을 되돌린다.
    # 저작 실패(크레딧 소진·스캔본 등)로 아하를 못 본 유저가 영구히 막히면 안 된다.
    if user_id and final and final["status"] == JobStatus.ERROR:
        await db.refund_free_deck(user_id)
```

`JobStatus`가 이미 import돼 있는지 확인하고, 없으면 파일 상단 import에 추가한다 (`from ...core.models import JobStatus` — 파일의 기존 import 스타일을 따를 것). `JobStatus`는 `str` Enum(`backend/core/models.py:224`)이라 DB에서 온 문자열과 `==` 비교가 성립한다.

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest backend/tests/test_free_trial.py -v
```

기대: 17 passed.

- [ ] **Step 5: 커밋**

```bash
git add backend/agents/deck/pipeline.py backend/tests/test_free_trial.py
git commit -m "[BE] 저작 실패 시 무료 1덱 환불 — _log_done 단일 훅"
```

---

## Task 5: Export 게이트 (파일이 나가는 4경로)

**Files:**
- Modify: `backend/routers/deck.py:265-286` (`export_deck`)
- Modify: `backend/routers/export.py:24-36` (`download_zip`), `backend/routers/export.py:55-78` (`download_card_png`)
- Modify: `backend/routers/jobs.py:108-139` (`trigger_export`)
- Modify: `backend/tests/test_api.py:38` (기존 테스트 보호)
- Test: `backend/tests/test_free_trial.py` (append)

**게이트를 거는 곳 / 안 거는 곳:**

| 경로 | 게이트 | 이유 |
|---|---|---|
| `POST /api/deck/{job_id}/export` | ✅ | ZIP 생성 = 원가 발생. 만들기 전에 막는다 |
| `GET /api/export/{export_job_id}/download` | ✅ | 바이트가 나가는 최종 관문(이중 방어) |
| `GET /api/cards/{job_id}/download/{card_num}` | ✅ | 단일 PNG 첨부 다운로드 — **놓치면 우회 구멍** |
| `POST /api/cards/{job_id}/export` (레거시) | ✅ | 레거시 경로로 새는 것 방지 |
| `GET /api/cards/{job_id}/image/{card_num}` | ❌ | 뷰어 화면 표시용 — 순수잠금은 "보이되 못 가져감" |
| `GET /api/deck/{job_id}/cards/{card_num}` | ❌ | 동일 (뷰어 카드 피드) |

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_free_trial.py` 맨 아래에 추가한다:

```python
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
    """순수잠금 = 다 보이되 못 가져감. 뷰어 표시 경로는 402가 아니어야 한다.

    이미지가 아직 없으니 404가 정상 — 중요한 건 402가 아니라는 것.
    """
    uid = await _mk_user("canview@test")
    job_id = "job-z"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get(f"/api/cards/{job_id}/image/1")
    assert r.status_code != 402


@pytest.mark.asyncio
async def test_paid_user_export_not_blocked_by_plan(client):
    """유료는 플랜 게이트를 통과한다(그 뒤 단계에서 404가 나는 건 무방)."""
    uid = await _mk_user("paid@test")
    await _db.set_plan(uid, "pro")
    job_id = "job-p"
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post(f"/api/deck/{job_id}/export")
    assert r.status_code != 402
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest backend/tests/test_free_trial.py -v -k "export or card"
```

기대: 앞의 두 테스트가 402 대신 다른 코드를 받아 FAIL.

- [ ] **Step 3: 4경로에 게이트 배선**

`backend/routers/deck.py`의 `export_deck` 함수(`deck.py:265`) 본문 첫 줄에 추가한다. `require_owned_job` 호출보다 **먼저** 온다:

```python
    plans.require_can_export(user)
```

`backend/routers/export.py`는 import를 먼저 추가한다 (`export.py:11`의 `from ..core import db`를 교체):

```python
from ..core import db, plans
```

그리고 `download_zip`(`export.py:25`)과 `download_card_png`(`export.py:56`) **각각의 본문 첫 줄**에 추가한다:

```python
    plans.require_can_export(user)
```

`backend/routers/jobs.py`도 동일하게 — 파일 상단 import에 `plans`를 추가하고(기존 `from ..core import ...` 줄에 합류), `trigger_export`(`jobs.py:108`) 본문 첫 줄에 추가한다:

```python
    plans.require_can_export(user)
```

**`get_card_image`(`export.py:40`)와 `get_deck_card`(`deck.py:251`)에는 절대 넣지 않는다** — 넣으면 무료 유저 뷰어가 빈 화면이 되고 아하가 죽는다.

- [ ] **Step 4: 기존 테스트 보호 — 오버라이드 유저에 plan 추가**

`backend/tests/test_api.py:38`의 의존성 오버라이드를 수정한다. 현재:

```python
    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "test@test", "role": "user"}
```

교체:

```python
    # plan='lab' — 이 스위트는 플랜 게이트가 아니라 API 동작을 검증한다(게이트 테스트는 test_free_trial.py).
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1, "email": "test@test", "role": "user", "plan": "lab", "free_decks_used": 0,
    }
```

- [ ] **Step 5: 테스트 통과 + 전체 회귀 확인**

```bash
pytest backend/tests/test_free_trial.py -v
pytest backend/tests/
```

기대: `test_free_trial.py` 21 passed. 전체 스위트에서 **402로 새로 깨지는 테스트가 있으면**, 그 테스트의 의존성 오버라이드 유저에도 Step 4와 같은 방식으로 `"plan": "lab"`을 추가해 고친다(게이트 로직을 약화시키지 말 것).

- [ ] **Step 6: 커밋**

```bash
git add backend/routers/deck.py backend/routers/export.py backend/routers/jobs.py backend/tests/
git commit -m "[BE] export 게이트 4경로 — 파일 반출만 잠금, 뷰어 inline은 개방(순수잠금)"
```

---

## Task 6: `/me` 확장 + 온보딩 완료 엔드포인트

**Files:**
- Modify: `backend/routers/auth.py:159-165`
- Test: `backend/tests/test_free_trial.py` (append)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
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
async def test_post_onboarded_marks_and_is_idempotent(client):
    uid = await _mk_user("onb@test")
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post("/api/auth/onboarded")
    assert r.status_code == 200
    assert (await _db.get_user_by_id(uid))["onboarded_at"] is not None

    r2 = await client.post("/api/auth/onboarded")
    assert r2.status_code == 200
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest backend/tests/test_free_trial.py -v -k "me_exposes or onboarded"
```

기대: `KeyError: 'plan'` / `405` 또는 `404`로 FAIL.

- [ ] **Step 3: `/me` 확장 + 신규 엔드포인트**

`backend/routers/auth.py` 상단 import에 `plans`를 추가한다 (기존 `from ..core import ...` 줄에 합류).

`backend/routers/auth.py:159-165`의 `me`를 교체한다:

```python
@router.get("/me")
async def me(user: dict = Depends(auth_core.get_current_user)):
    return {
        "email": user["email"],
        "role": user["role"],
        "emailVerified": bool(user.get("email_verified")),
        # 플랜 상태 — 프론트가 미터·잠금·페이월을 그리는 데 쓴다.
        "plan": plans.plan_of(user),
        "freeDecksUsed": plans.free_decks_used(user),
        "freeDeckLimit": plans.FREE_DECK_LIMIT,
        "canAuthor": plans.can_author(user),
        "canExport": plans.can_export(user),
        "onboarded": user.get("onboarded_at") is not None,
    }


@router.post("/onboarded")
async def mark_onboarded(user: dict = Depends(auth_core.get_current_user)):
    """환영 온보딩 시청 완료. 멱등 — 두 번 불러도 처음 시각을 유지한다."""
    await db.mark_onboarded(user["id"])
    return {"ok": True}
```

`auth.py`가 `db`를 어떤 이름으로 import하는지 확인하고 맞춘다(파일 상단 import 블록 참조).

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest backend/tests/test_free_trial.py -v
pytest backend/tests/
```

기대: `test_free_trial.py` 23 passed, 전체 스위트 green.

- [ ] **Step 5: 커밋**

```bash
git add backend/routers/auth.py backend/tests/test_free_trial.py
git commit -m "[BE] /me에 플랜 상태 노출 + POST /api/auth/onboarded(멱등)"
```

---

## Task 7: 프론트 — 에러 `code` 보존 + 플랜 로직

**Files:**
- Modify: `web/src/lib/api.ts:9-16`
- Create: `web/src/lib/plan.ts`, `web/src/lib/plan.test.ts`

현재 인터셉터(`api.ts:12-14`)는 `detail.message`만 남기고 **status code와 `detail.code`를 버린다.** 그래서 프론트가 "체험 소진(402)"과 "브루트포스 차단(429)"을 구분할 수 없다. 이걸 먼저 고쳐야 페이월을 띄울 수 있다.

`web/vitest.config.mts`는 `environment: 'node'` + `include: ['src/**/*.test.ts']`라 **`.tsx` 컴포넌트 테스트는 불가능**하다. 따라서 판정 로직을 `plan.ts`(순수 함수)로 빼서 테스트하고, UI는 이후 태스크에서 실브라우저로 검증한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`web/src/lib/plan.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { isPlanGateError, planGateKind, trialLabel } from './plan'

describe('플랜 게이트 에러 식별', () => {
  it('402 ERR-PLAN-EXPORT는 export 게이트로 식별된다', () => {
    const err = Object.assign(new Error('내보내기는 업그레이드 후'), {
      status: 402,
      code: 'ERR-PLAN-EXPORT',
    })
    expect(isPlanGateError(err)).toBe(true)
    expect(planGateKind(err)).toBe('export')
  })

  it('402 ERR-PLAN-AUTHOR는 author 게이트로 식별된다', () => {
    const err = Object.assign(new Error('무료 체험 1덱을 모두'), {
      status: 402,
      code: 'ERR-PLAN-AUTHOR',
    })
    expect(planGateKind(err)).toBe('author')
  })

  it('★429 브루트포스는 플랜 게이트가 아니다 — 페이월 띄우면 안 됨', () => {
    const err = Object.assign(new Error('너무 많은 시도입니다'), {
      status: 429,
      code: 'ERR-AUTH-429',
    })
    expect(isPlanGateError(err)).toBe(false)
    expect(planGateKind(err)).toBe(null)
  })

  it('status가 없는 평범한 에러도 안전하게 처리한다', () => {
    expect(isPlanGateError(new Error('네트워크 오류'))).toBe(false)
    expect(planGateKind(new Error('네트워크 오류'))).toBe(null)
  })
})

describe('무료 체험 라벨', () => {
  it('무료 미사용', () => {
    expect(trialLabel({ plan: 'free', freeDecksUsed: 0, freeDeckLimit: 1 })).toBe('무료 체험 · 0 / 1 덱 사용')
  })

  it('무료 소진', () => {
    expect(trialLabel({ plan: 'free', freeDecksUsed: 1, freeDeckLimit: 1 })).toBe('무료 체험 · 1 / 1 덱 사용')
  })

  it('유료는 무료 미터를 보여주지 않는다', () => {
    expect(trialLabel({ plan: 'pro', freeDecksUsed: 1, freeDeckLimit: 1 })).toBe(null)
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd web && npm test -- plan
```

기대: `Failed to resolve import "./plan"`.

- [ ] **Step 3: `web/src/lib/plan.ts` 작성**

```ts
/**
 * 플랜 게이트 — 무료체험(export-gate 순수잠금)의 프론트 판정.
 *
 * ★402(플랜 벽)와 429(브루트포스 차단)를 반드시 구분한다. 429에 페이월을 띄우면
 * 잘못된 유저에게 결제를 요구하게 된다.
 */

export type PlanGateKind = 'author' | 'export'

export type PlanState = {
  plan: string
  freeDecksUsed: number
  freeDeckLimit: number
}

type MaybeApiError = Error & { status?: number; code?: string }

export function planGateKind(err: unknown): PlanGateKind | null {
  const e = err as MaybeApiError
  if (!e || e.status !== 402) return null
  if (e.code === 'ERR-PLAN-EXPORT') return 'export'
  if (e.code === 'ERR-PLAN-AUTHOR') return 'author'
  return null
}

export function isPlanGateError(err: unknown): boolean {
  return planGateKind(err) !== null
}

/** 무료 유저에게만 보여줄 사용량 라벨. 유료면 null(미터 자체를 감춘다). */
export function trialLabel(state: PlanState): string | null {
  if (state.plan !== 'free') return null
  return `무료 체험 · ${state.freeDecksUsed} / ${state.freeDeckLimit} 덱 사용`
}
```

- [ ] **Step 4: 인터셉터가 status/code를 보존하도록 수정**

`web/src/lib/api.ts:9-16`을 교체한다:

```ts
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail
    const message = typeof detail === 'object' ? detail.message : detail
    // ★status/code를 보존한다 — 402(플랜 벽)와 429(브루트포스)를 구분해야 페이월을 정확히 띄운다.
    const wrapped = new Error(message || err.message) as Error & { status?: number; code?: string }
    wrapped.status = err.response?.status
    if (typeof detail === 'object' && detail?.code) wrapped.code = detail.code
    return Promise.reject(wrapped)
  }
)
```

- [ ] **Step 5: 테스트 통과 + 타입 확인**

```bash
cd web && npm test
cd web && npx tsc --noEmit
```

기대: vitest 전부 green(기존 + 신규 7), tsc 에러 없음.

- [ ] **Step 6: 커밋**

```bash
git add web/src/lib/plan.ts web/src/lib/plan.test.ts web/src/lib/api.ts
git commit -m "[FE] api 에러에 status/code 보존 + plan.ts 게이트 판정(402≠429)"
```

---

## Task 8: `/onboarding` 화면 + 진입 라우팅

**Files:**
- Create: `web/src/app/onboarding/page.tsx`
- Modify: `web/src/components/auth/AuthGuard.tsx`

**진입 로직 (2026-07-16 확정):**
- 환영 온보딩 = **처음 온 사람만**(`onboarded === false`), **정확히 1회**. 재방문 무료 유저에겐 안 뜬다.
- 전환 넛지 = **결제 안 한 사람**(지속) — 이건 온보딩이 아니라 대시보드 미터·export 벽·`/upgrade`가 담당한다. 축이 다르다.
- 이메일 인증은 **무료 덱 뒤**로 미룬다 — 아하 도달이 전환의 전부라 인증 마찰로 앞을 막지 않는다.
- 게이트는 진입이 아니라 **행동**에서 건다(2번째 생성 = 업로드 제출, 내보내기 = export 버튼).

- [ ] **Step 1: 온보딩 화면 작성**

디자인 레퍼런스: `scratchpad/free_trial_flow.html`의 `s-onboarding` 스크린. `DESIGN.md` 토큰(OKLCH hue 163 에메랄드, Pretendard, flat-by-default, 에메랄드 ≤10%)을 따른다. 기존 화면의 Tailwind 클래스 관례는 `web/src/app/deck/new/page.tsx`를 참고한다.

`web/src/app/onboarding/page.tsx`:

```tsx
'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function OnboardingPage() {
  const router = useRouter()
  const [leaving, setLeaving] = useState(false)

  async function finish(dest: string) {
    setLeaving(true)
    try {
      // 멱등 — 실패해도 진행을 막지 않는다(온보딩이 유저를 가두면 안 된다).
      await fetch('/api/auth/onboarded', { method: 'POST' })
    } catch {
      /* noop */
    }
    router.replace(dest)
  }

  return (
    <main className="onboarding">
      <div className="onboarding__card">
        <p className="onboarding__eyebrow">환영합니다</p>
        <h1 className="onboarding__title">논문 한 편이면,<br />카드뉴스 한 세트가 됩니다.</h1>
        <p className="onboarding__lede">
          PDF를 올리면 스토리·디자인·검증까지 한 번에 만들어 드려요.
          모든 수치는 원문과 대조해 <strong>✓ 확인</strong> 배지를 답니다.
        </p>

        <ol className="onboarding__steps">
          <li><span>1</span> 논문 PDF 업로드</li>
          <li><span>2</span> 카드뉴스 자동 저작 + 수치 검증</li>
          <li><span>3</span> 화면에서 확인하고 편집</li>
        </ol>

        <p className="onboarding__note">
          지금은 <strong>무료 체험 1덱</strong>이에요. 만들고 검증까지 전부 볼 수 있고,
          파일 내보내기는 업그레이드 후 이용할 수 있어요.
        </p>

        <div className="onboarding__actions">
          <button
            className="btn btn-primary"
            disabled={leaving}
            onClick={() => finish('/deck/new')}
          >
            첫 논문 올리기 →
          </button>
          <button
            className="btn btn-ghost"
            disabled={leaving}
            onClick={() => finish('/dashboard')}
          >
            나중에 할게요
          </button>
        </div>
      </div>
    </main>
  )
}
```

스타일은 `web/src/app/globals.css`에 추가한다. **전역 리셋 함정 주의**(`web/CLAUDE.md` Learned Mistakes 2026-07-03): 새 규칙은 반드시 `@layer` 안에 넣고, CSS 주석에 `*/`를 포함하는 문자열을 쓰지 않는다.

```css
@layer components {
  .onboarding {
    min-height: 100dvh;
    display: grid;
    place-items: center;
    padding: 40px 20px;
    background: var(--bg-subtle);
  }
  .onboarding__card {
    width: 100%;
    max-width: 560px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 40px 36px;
  }
  .onboarding__eyebrow {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0 0 12px;
  }
  .onboarding__title {
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1.28;
    margin: 0 0 16px;
  }
  .onboarding__lede {
    font-size: 15px;
    line-height: 1.65;
    color: var(--text-2);
    margin: 0 0 28px;
  }
  .onboarding__steps {
    list-style: none;
    margin: 0 0 28px;
    padding: 0;
    display: grid;
    gap: 12px;
  }
  .onboarding__steps li {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14.5px;
    font-weight: 600;
  }
  .onboarding__steps span {
    flex: 0 0 26px;
    height: 26px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-size: 12px;
    font-weight: 700;
    color: var(--accent);
    background: var(--accent-wash, var(--bg-subtle));
  }
  .onboarding__note {
    font-size: 13.5px;
    line-height: 1.6;
    color: var(--text-2);
    background: var(--bg-subtle);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    margin: 0 0 28px;
  }
  .onboarding__actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
}
```

`--accent-wash` 토큰이 `globals.css`에 없으면 폴백이 동작하므로 그대로 둔다. 기존 `.btn` / `.btn-primary` / `.btn-ghost` 클래스가 있는지 확인하고, 없으면 대시보드에서 쓰는 실제 버튼 클래스명으로 교체한다.

- [ ] **Step 2: `AuthGuard`가 온보딩으로 보내도록 수정**

`web/src/components/auth/AuthGuard.tsx`를 읽고, 현재 `/api/auth/me`를 fetch해서 401이면 `/login`으로 보내는 로직(`AuthGuard.tsx:14` 부근)에 온보딩 분기를 추가한다. 수정 방침:

```tsx
// 기존: 401이면 /login
// 추가: 200인데 onboarded === false이면 /onboarding (단, 이미 /onboarding이면 그대로 둔다 — 무한 리다이렉트 방지)
```

구체적으로 fetch 응답을 파싱해 아래 분기를 넣는다:

```tsx
const data = await res.json()
if (data?.onboarded === false && pathname !== '/onboarding') {
  router.replace('/onboarding')
  return
}
```

`pathname`은 `usePathname()`(`next/navigation`)으로 얻는다. 딥링크(예: `/deck/abc`)로 들어온 경우에도 온보딩이 한 번은 뜨지만, 온보딩의 "나중에 할게요"가 `/dashboard`로 보내므로 갇히지 않는다.

**주의:** `/onboarding` 페이지 자체가 `AuthGuard` 안에 있다면 위 `pathname` 가드가 반드시 필요하다. 레이아웃 구조를 먼저 확인할 것.

- [ ] **Step 3: 타입·빌드 확인**

```bash
cd web && npx tsc --noEmit
cd web && npm run build
```

기대: 에러 없음.

- [ ] **Step 4: 실브라우저 검증**

백엔드와 프론트를 띄운 뒤(`uvicorn` 재시작 필수 — `backend/CLAUDE.md` NEVER), 새 계정으로 가입해서 확인한다:

```bash
wmux browser open http://localhost:3000/signup
```

확인 항목:
1. 가입 직후 `/onboarding`이 뜬다
2. "첫 논문 올리기" → `/deck/new`로 간다
3. `/dashboard`로 직접 이동해도 온보딩이 **다시 뜨지 않는다**
4. 로그아웃 후 재로그인해도 온보딩이 뜨지 않는다

`wmux browser screenshot`이 타임아웃 나면 `wmux browser get-text`로 대체 확인한다.

- [ ] **Step 5: 커밋**

```bash
git add web/src/app/onboarding/ web/src/components/auth/AuthGuard.tsx web/src/app/globals.css
git commit -m "[FE] 첫 방문 온보딩 1회 + AuthGuard 진입 라우팅"
```

---

## Task 9: 대시보드 무료 미터 + 잠금 표시

**Files:**
- Modify: `web/src/app/dashboard/page.tsx` (미터 삽입 `page.tsx:227` 앞, 카드 액션 `page.tsx:341-375`, 빈/게이트 상태)

디자인 레퍼런스: `scratchpad/dashboard_free.html`. 미터는 덱 그리드 **위**에 놓고, 유료 유저에겐 `trialLabel()`이 `null`을 반환하므로 **렌더하지 않는다**.

- [ ] **Step 1: 플랜 상태 로드**

`web/src/app/dashboard/page.tsx`에 `/api/auth/me`를 부르는 state를 추가한다. 전역 컨텍스트는 만들지 않는다 — 이 레포는 필요한 컴포넌트가 각자 `/api/auth/me`를 부르는 기존 패턴을 쓴다(`AuthGuard.tsx:14`, `dashboard/layout.tsx:16`, `DeckAccountMenu.tsx:15`).

```tsx
import { trialLabel, type PlanState } from '@/lib/plan'

// 컴포넌트 안:
const [me, setMe] = useState<(PlanState & { canAuthor: boolean; canExport: boolean }) | null>(null)

useEffect(() => {
  fetch('/api/auth/me')
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => d && setMe(d))
    .catch(() => {})
}, [])
```

- [ ] **Step 2: 미터 렌더**

덱 그리드(`page.tsx:227` 부근의 `sorted.map(...)`을 감싸는 컨테이너) **바로 앞**에 삽입한다:

```tsx
{me && trialLabel(me) && (
  <section className="trial-meter">
    <div className="trial-meter__left">
      <span className="trial-meter__badge">무료 체험</span>
      <p className="trial-meter__usage">
        {me.freeDecksUsed}<span> / {me.freeDeckLimit} 덱 사용</span>
      </p>
      <div className="trial-meter__bar">
        <i style={{ width: `${Math.min(100, (me.freeDecksUsed / me.freeDeckLimit) * 100)}%` }} />
      </div>
    </div>
    <div className="trial-meter__mid">
      <p className="trial-meter__t">
        {me.canAuthor ? '카드뉴스 1덱을 무료로 만들어 보세요.' : '만들고 검증까지 무료로 다 봤어요.'}
      </p>
      <p className="trial-meter__d">
        <strong>내보내기</strong>와 <strong>다음 카드뉴스</strong>는 업그레이드 후 이용할 수 있어요.
        만든 덱은 그대로 보관돼요.
      </p>
    </div>
    <a className="btn btn-primary" href="/upgrade">업그레이드 →</a>
  </section>
)}
```

스타일은 `scratchpad/dashboard_free.html:47-63`의 `.meter*` 규칙을 `globals.css`의 `@layer components`로 옮기되, 하드코딩된 OKLCH 값 대신 **기존 토큰**(`var(--surface)`, `var(--border)`, `var(--text-2)` 등)으로 바꾼다. `web/CLAUDE.md` §6: `@theme`에 hex/oklch 직접 금지, 이식 전 토큰 매핑.

| scratchpad 하드코딩 | web 토큰 |
|---|---|
| `--canvas` | `var(--surface)` |
| `--canvas-warm` / `--canvas-subtle` | `var(--bg-subtle)` |
| `--border` | `var(--border)` |
| `--ink-1` / `--ink-2` / `--ink-3` | `var(--text-1)` / `var(--text-2)` / `var(--text-3)` |
| `--emerald` / `--cta-grad` | `var(--accent)` |
| `--amber*` | 기존 warn 토큰이 있으면 그것, 없으면 `var(--accent)` 계열로 통일 |

- [ ] **Step 3: 덱 카드 잠금 배지 + 게이트된 새 덱**

`ProjectCard`의 액션 영역(`page.tsx:341-375`)에서 다운로드/내보내기 링크에 잠금을 표시한다. 무료 유저(`me?.canExport === false`)일 때 버튼 라벨을 `🔒 내보내기`로 바꾸고 클릭 시 `/upgrade`로 보낸다. **버튼을 숨기지 않는다** — 벽이 보여야 전환이 일어난다.

빈 상태가 아니면서 `me?.canAuthor === false`일 때, 그리드 마지막에 게이트 카드를 추가한다(레퍼런스 `scratchpad/dashboard_free.html:173-178`):

```tsx
{me && !me.canAuthor && (
  <a className="new-deck-card new-deck-card--locked" href="/upgrade">
    <span className="new-deck-card__lock">🔒</span>
    <strong>다음 카드뉴스</strong>
    <span>무료 체험 1덱을 다 썼어요. 업그레이드하면 계속 만들 수 있어요.</span>
  </a>
)}
```

또한 헤더의 상시 CTA(`web/src/app/dashboard/layout.tsx:53-58`, `새 카드뉴스`)는 **그대로 둔다** — 클릭하면 `/deck/new`에서 업로드 제출 시 402가 나고 그때 페이월을 보여주는 게 이 설계의 원칙("게이트는 진입이 아니라 행동에서")이다.

- [ ] **Step 4: `/deck/new`에서 402 처리**

`web/src/app/deck/new/page.tsx:76-86`의 `submit()` catch 블록을 수정한다. 현재는 `setError(e.message)`만 한다:

```tsx
} catch (e) {
  const kind = planGateKind(e)
  if (kind === 'author') {
    router.push('/upgrade?from=author')
    return
  }
  setError((e as Error).message)
}
```

`planGateKind`를 `@/lib/plan`에서 import한다.

- [ ] **Step 5: 타입·빌드 확인**

```bash
cd web && npx tsc --noEmit && npm run build
```

- [ ] **Step 6: 실브라우저 검증**

무료 계정으로 확인한다:
1. 덱 0개 — 미터가 `0 / 1`을 보이고 게이트 카드는 **없다**
2. 덱 1개 만든 뒤 — 미터가 `1 / 1`, 덱 카드에 `🔒 내보내기`, 그리드에 게이트 카드
3. 게이트 상태에서 헤더 `새 카드뉴스` → `/deck/new` → 업로드 제출 → `/upgrade`로 이동
4. **유료 계정(`plan='lab'`)에선 미터가 아예 안 보인다**

유료 계정 전환은 SQL로 만든다:

```bash
sqlite3 polyinsight.db "UPDATE users SET plan='lab' WHERE email='<테스트계정>';"
```

- [ ] **Step 7: 커밋**

```bash
git add web/src/app/dashboard/page.tsx web/src/app/deck/new/page.tsx web/src/app/globals.css
git commit -m "[FE] 대시보드 무료 미터 + 덱 잠금 배지 + 생성 게이트 402→업그레이드"
```

---

## Task 10: Export 페이월 모달

**Files:**
- Modify: `web/src/components/deck/DeckExportModal.tsx`

현재 이 모달은 `exportDeck()` 실패를 통째로 삼키고 고정 문구만 보여준다(`DeckExportModal.tsx:33-35`). 402를 받으면 **페이월로 전환**해야 한다.

디자인 레퍼런스: `scratchpad/paywall_export.html`. 핵심 원칙 — **검증을 앞세우고**("✓ 원문 검증 완료"), BEFORE/AFTER로 "무료로 받은 것 / 업그레이드하면"을 나란히 놓고, **워터마크 타협을 제안하지 않는다**(순수잠금).

- [ ] **Step 1: 402 분기 추가**

`DeckExportModal.tsx`를 읽고, `exportDeck()` 호출부(`DeckExportModal.tsx:30`)의 catch를 수정한다:

```tsx
import { planGateKind } from '@/lib/plan'

// state 추가
const [paywalled, setPaywalled] = useState(false)

// catch 안:
} catch (e) {
  if (planGateKind(e) === 'export') {
    setPaywalled(true)
    return
  }
  setError('내보내기에 실패했습니다. 잠시 후 다시 시도해 주세요.')
}
```

- [ ] **Step 2: 페이월 렌더**

`paywalled === true`일 때 모달 본문을 아래로 교체한다:

```tsx
{paywalled ? (
  <div className="paywall">
    <p className="paywall__eyebrow">✓ 원문 검증 완료</p>
    <h2 className="paywall__title">이 카드뉴스, 내보낼 준비가 끝났어요</h2>

    <div className="paywall__split">
      <div className="paywall__col">
        <p className="paywall__colhead">무료로 받은 것</p>
        <ul>
          <li>✓ 카드뉴스 저작</li>
          <li>✓ 원문 수치 검증</li>
          <li>✓ 화면에서 보기 · 편집</li>
        </ul>
      </div>
      <div className="paywall__col paywall__col--accent">
        <p className="paywall__colhead">업그레이드하면</p>
        <ul>
          <li>1080×1350 PNG 파일</li>
          <li>덱 전체 ZIP 내보내기</li>
          <li>카드뉴스 계속 만들기</li>
        </ul>
      </div>
    </div>

    <div className="paywall__actions">
      <a className="btn btn-primary" href="/upgrade?from=export">업그레이드하고 내보내기</a>
      <button className="btn btn-ghost" onClick={onClose}>계속 둘러보기</button>
    </div>
  </div>
) : (
  /* 기존 모달 본문 그대로 */
)}
```

스타일은 `scratchpad/paywall_export.html`의 규칙을 Task 9와 같은 토큰 매핑표로 옮긴다.

**금지 사항:** 워터마크 버전 제공, 저해상도 "맛보기" 다운로드, 카운트다운 타이머, "지금만 할인" 문구. 순수잠금 + 다크패턴 배제가 결정 사항이다.

- [ ] **Step 3: 타입·빌드 확인**

```bash
cd web && npx tsc --noEmit && npm run build
```

- [ ] **Step 4: 실브라우저 검증**

무료 계정으로 덱을 하나 만든 뒤 `/deck/<jobId>`에서 "내보내기"를 누른다.

확인 항목:
1. 페이월이 뜬다(에러 문구가 아니라)
2. 뒤의 덱은 **여전히 보인다**(순수잠금 = 다 보이되 못 가져감)
3. "계속 둘러보기"로 닫으면 편집을 계속할 수 있다
4. 유료 계정에선 페이월 없이 실제 ZIP이 내려온다

- [ ] **Step 5: 커밋**

```bash
git add web/src/components/deck/DeckExportModal.tsx web/src/app/globals.css
git commit -m "[FE] export 페이월 — 402 시 검증 앞세운 벽(순수잠금, 워터마크 없음)"
```

---

## Task 11: `/upgrade` 안내 페이지 (가안)

**Files:**
- Create: `web/src/app/upgrade/page.tsx`

디자인 레퍼런스: `scratchpad/upgrade_page.html`.

**가격 숫자는 확정하지 않는다.** 금액 자리에 `$—`를 두고 `가안` 칩을 붙인다. 결제 버튼은 아직 체크아웃으로 연결되지 않으므로 "출시 알림 받기" 성격의 비활성 상태 또는 문의 링크로 둔다. 티어는 무료 / Pro(가장 인기 — 에메랄드 강조) / Lab(문의하기) 3개.

- [ ] **Step 1: 페이지 작성**

```tsx
'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

function UpgradeInner() {
  const from = useSearchParams().get('from')
  const headline =
    from === 'export'
      ? '내보내려면 업그레이드가 필요해요'
      : from === 'author'
        ? '무료 체험 1덱을 모두 사용했어요'
        : '계속 만들고, 파일로 내보내세요'

  return (
    <main className="upgrade">
      <header className="upgrade__head">
        <h1>{headline}</h1>
        <p>만든 카드뉴스는 그대로 보관돼요. 업그레이드하면 바로 이어서 쓸 수 있어요.</p>
      </header>

      <div className="upgrade__banner">
        가격은 <strong>확정 전</strong>이에요. 덱 생성 원가를 먼저 낮춘 뒤 공정하게 정할게요.
      </div>

      <div className="upgrade__tiers">
        <section className="tier">
          <h2>무료</h2>
          <p className="tier__price">₩0</p>
          <ul>
            <li>카드뉴스 1덱 (평생)</li>
            <li>원문 수치 검증</li>
            <li>화면에서 보기 · 편집</li>
            <li className="tier__off">파일 내보내기</li>
          </ul>
          <button className="btn" disabled>현재 플랜</button>
        </section>

        <section className="tier tier--featured">
          <span className="tier__flag">가장 인기</span>
          <h2>Pro</h2>
          <p className="tier__price">
            $—<span className="tier__chip">가안</span>
          </p>
          <ul>
            <li>매달 카드뉴스 여러 덱</li>
            <li>1080×1350 PNG · ZIP 내보내기</li>
            <li>원문 수치 검증</li>
            <li>편집 · 이미지 삽입</li>
          </ul>
          <button className="btn btn-primary" disabled>준비 중</button>
        </section>

        <section className="tier">
          <h2>Lab</h2>
          <p className="tier__price">문의</p>
          <ul>
            <li>연구실 · 팀 단위</li>
            <li>사용량 협의</li>
            <li>온보딩 지원</li>
          </ul>
          <a className="btn" href="mailto:dbstpgns789@hanyang.ac.kr?subject=PolyInsight%20Lab%20문의">
            문의하기
          </a>
        </section>
      </div>

      <p className="upgrade__foot">
        결제는 Creem을 통해 처리될 예정이에요 (부가세 포함, USD).
      </p>
    </main>
  )
}

export default function UpgradePage() {
  return (
    <Suspense fallback={null}>
      <UpgradeInner />
    </Suspense>
  )
}
```

`useSearchParams`는 Next.js App Router에서 `Suspense` 경계를 요구하므로 위 구조를 유지한다.

스타일은 `scratchpad/upgrade_page.html`에서 Task 9의 토큰 매핑표로 옮긴다. `tier--featured`에만 에메랄드를 쓴다(에메랄드 ≤10% 규칙).

- [ ] **Step 2: 타입·빌드 확인**

```bash
cd web && npx tsc --noEmit && npm run build
```

- [ ] **Step 3: 실브라우저 검증**

```bash
wmux browser open http://localhost:3000/upgrade?from=export
```

확인 항목:
1. `?from=export` / `?from=author` / 파라미터 없음 — 헤드라인 3종이 각각 바뀐다
2. 가안 배너와 `가안` 칩이 보인다
3. 좁은 화면에서 티어 3개가 세로로 쌓이고 **가로 스크롤이 생기지 않는다**

- [ ] **Step 4: 커밋**

```bash
git add web/src/app/upgrade/ web/src/app/globals.css
git commit -m "[FE] /upgrade 안내 페이지 — 3티어 가안(결제 연동 전)"
```

---

## Task 12: 퍼널 이벤트 — 벽 히트 기록 + 판독 스크립트

> **왜 이 태스크가 있나 (2026-07-20 추가).** 이 플랜을 끝내면 벽은 서지만 **읽을 수가 없다.**
> 무료체험의 목적은 매출이 아니라 **두 숫자**를 얻는 것이다:
> - **뷰어→벽 비율 = 제품 지표** — 덱을 다 보고도 내보내려 하지 않으면 그 덱은 발행급이 아니다. 우리가 한 번도 가져본 적 없는 정직한 품질 판정이다(현재 발행 save 0).
> - **벽→결제 비율 = 가격 지표** — 결제 붙은 뒤에 의미가 생긴다.
>
> 그리고 BM 로드맵상 **T1(결제 켜기) 트리거가 "벽 히트 30~50명"**이라, 이 숫자를 못 세면 다음 단계로 갈 판단 근거가 없다.

**이미 있는 것 (새로 만들지 말 것):** `events` 테이블(`backend/core/db.py:144`)과 `db.log_event()`(`db.py:967`)가 이미 있고, `signup`·`login`·`deck_upload`·`deck_edit`·`deck_export` 등 10종이 이미 기록되고 있다. **빠진 것은 딱 하나 — 402로 막힌 순간(벽 히트)이 아무데도 안 남는다.** `deck_export`는 성공했을 때만 기록된다.

**Files:**
- Modify: `backend/core/plans.py` (예외 클래스로 승격)
- Modify: `backend/main.py` (402 단일 핸들러)
- Create: `backend/scripts/funnel_report.py`
- Test: `backend/tests/test_free_trial.py` (append)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
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
    assert json.loads(evts[0]["payload"])["kind"] == "export"


@pytest.mark.asyncio
async def test_author_gate_hit_is_logged(client):
    uid = await _mk_user("gatelog2@test")
    await _db.consume_free_deck(uid, 1)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.post("/api/deck/upload", files={"file": _fake_pdf()})
    assert r.status_code == 402

    evts = [e for e in await _db.list_events(limit=50) if e["event_type"] == "plan_gate_hit"]
    assert json.loads(evts[0]["payload"])["kind"] == "author"


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
```

파일 상단 import에 `import json`을 추가한다.

- [ ] **Step 2: `plans.py`의 402를 예외 클래스로 승격**

Task 2에서 만든 `require_can_author`/`require_can_export`가 던지는 `HTTPException`을 전용 클래스로 바꾼다. **이유: 이벤트 훅을 한 곳에만 두기 위해서다.** 각 라우터에서 `log_event`를 직접 부르면 게이트를 새로 추가하는 사람이 반드시 잊는다(`_log_done`을 단일 훅으로 둔 Task 4와 같은 원칙).

```python
class PlanGateError(HTTPException):
    """플랜 벽. user_id를 실어 보내 예외 핸들러가 이벤트를 남긴다.

    request.state에 유저를 심지 않기 때문에 예외가 직접 들고 간다.
    """

    def __init__(self, gate_kind: str, code: str, message: str, user_id: int | None = None):
        super().__init__(status_code=402, detail={"code": code, "message": message})
        self.gate_kind = gate_kind
        self.user_id = user_id


def author_gate_error(user: dict | None = None) -> PlanGateError:
    return PlanGateError(
        gate_kind="author",
        code="ERR-PLAN-AUTHOR",
        message="무료 체험 1덱을 모두 사용했어요. 업그레이드하면 계속 만들 수 있어요.",
        user_id=(user or {}).get("id"),
    )


def export_gate_error(user: dict | None = None) -> PlanGateError:
    return PlanGateError(
        gate_kind="export",
        code="ERR-PLAN-EXPORT",
        message="내보내기는 업그레이드 후 이용할 수 있어요. 만든 카드뉴스는 그대로 보관돼요.",
        user_id=(user or {}).get("id"),
    )


def require_can_author(user: dict) -> None:
    if not can_author(user):
        raise author_gate_error(user)


def require_can_export(user: dict) -> None:
    if not can_export(user):
        raise export_gate_error(user)
```

Task 3의 `raise plans.author_gate_error()` 호출부에 `user`를 넘기도록 고친다 — `raise plans.author_gate_error(user)`. (안 넘기면 레이스에서 진 요청의 벽 히트가 익명으로 남는다.)

- [ ] **Step 3: `main.py`에 402 단일 핸들러**

```python
from fastapi import Request
from fastapi.exception_handlers import http_exception_handler

from .core.plans import PlanGateError


@app.exception_handler(PlanGateError)
async def _plan_gate_hit(request: Request, exc: PlanGateError):
    """벽 히트 계측 — 게이트가 몇 개로 늘어나든 기록은 여기 한 곳."""
    try:
        await db.log_event(
            "plan_gate_hit",
            user_id=exc.user_id,
            payload={"kind": exc.gate_kind, "path": request.url.path},
        )
    except Exception:
        pass  # 계측 실패가 응답을 막으면 안 된다(제품 > 측정)
    return await http_exception_handler(request, exc)
```

`main.py`의 기존 import 스타일(`from .core import db` 등)을 확인해 맞춘다. **`HTTPException` 전체에 핸들러를 걸지 말 것** — 다른 모든 에러 응답까지 가로챈다.

- [ ] **Step 4: 판독 스크립트**

`backend/scripts/funnel_report.py` — T1 트리거 판정용. 무료체험 퍼널을 한 화면에 찍는다.

```python
"""무료체험 퍼널 판독 — 벽 히트가 T1(결제 켜기) 트리거에 도달했는지 본다.

실행: python -m backend.scripts.funnel_report
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter

from backend.core import db

T1_TRIGGER = 30  # 벽 히트 고유 유저 — 이 밑에선 전환율이 통계가 아니라 노이즈다


async def main() -> None:
    evts = await db.list_events(limit=100000)
    by_type: dict[str, set[int]] = {}
    for e in evts:
        by_type.setdefault(e["event_type"], set()).add(e["user_id"])

    gate_kinds: Counter[str] = Counter()
    gate_users: set[int] = set()
    for e in evts:
        if e["event_type"] == "plan_gate_hit":
            gate_kinds[json.loads(e["payload"] or "{}").get("kind", "?")] += 1
            gate_users.add(e["user_id"])

    jobs = await db.list_all_jobs()
    done = [j for j in jobs if j["status"] == "DONE"]

    def n(t: str) -> int:
        return len(by_type.get(t, ()))

    print("── 무료체험 퍼널 (고유 유저 기준) ─────────────────")
    print(f"  가입              {n('signup'):>5}")
    print(f"  논문 업로드        {n('deck_upload'):>5}")
    print(f"  덱 완성           {len({j['user_id'] for j in done}):>5}   (덱 {len(done)}건)")
    print(f"  편집              {n('deck_edit'):>5}")
    print(f"  ★벽 히트          {len(gate_users):>5}   (export {gate_kinds['export']} / author {gate_kinds['author']}회)")
    print(f"  내보내기 성공      {n('deck_export'):>5}")
    print()
    denom = len({j["user_id"] for j in done})
    if denom:
        print(f"  덱 완성 → 벽 히트   {len(gate_users) / denom:.0%}   ← ★제품 지표(발행 의사)")
    print(f"  T1 트리거({T1_TRIGGER}명)   {'도달 ✅' if len(gate_users) >= T1_TRIGGER else f'미달 ({len(gate_users)}/{T1_TRIGGER})'}")


if __name__ == "__main__":
    asyncio.run(main())
```

**주의:** `db.list_all_jobs()`의 실제 이름·시그니처를 `backend/core/db.py`에서 확인하고 맞춘다(없으면 `list_jobs` 등 기존 함수를 쓰거나 raw SELECT로 대체). 없는 함수를 새로 만들지는 말 것.

**분모에 대한 정직한 한계:** "덱 완성"을 뷰어 도달의 대리 지표로 쓴다. 생성이 끝났는데 `/deck/[id]`를 한 번도 안 연 유저는 사실상 없지만(생성 중에 그 화면에서 기다린다), 엄밀히는 근사다. 별도 `deck_view` 이벤트는 폴링 노이즈가 커서 넣지 않는다.

- [ ] **Step 5: 테스트 통과 + 전체 회귀**

```bash
pytest backend/tests/test_free_trial.py -v
pytest backend/tests/
```

- [ ] **Step 6: 스크립트 실물 확인**

```bash
python -m backend.scripts.funnel_report
```

기대: 크래시 없이 표가 찍힌다(전부 0이어도 정상 — 아직 유저가 없다).

- [ ] **Step 7: 커밋**

```bash
git add backend/core/plans.py backend/main.py backend/scripts/funnel_report.py backend/tests/test_free_trial.py
git commit -m "[BE] 벽 히트 계측 — PlanGateError 단일 핸들러 + 퍼널 판독 스크립트"
```

---

## Task 13: 무료 유저 인라인 카드 축소 서빙 (원본 해상도 유출 차단)

> **왜 이 태스크가 있나 (2026-07-20 추가).** 최초 플랜은 이 구멍을 "렌더 파이프라인을 건드려야 한다"는 이유로 스코프 밖에 뒀는데, **재검토 결과 그럴 필요가 없었다.** 서빙 레이어에서 리사이즈하면 되고 Pillow는 이미 쓰는 의존성이다(`backend/agents/deck/layout_audit.py:23`).
>
> 지금 상태로는 무료 유저가 뷰어 이미지 URL을 직접 열어 **유료 산출물과 동일한 1080×1350 PNG**를 우클릭 저장할 수 있다 — export 벽 전체가 우회된다.

**설계 원칙: 게이트(402)가 아니라 해상도 차등이다.** 이 두 경로에 402를 걸면 무료 유저 뷰어가 빈 화면이 되고 아하가 죽는다. 보이는 것은 **전부 그대로 보이되**, 가져가는 파일만 화면용 크기다.

**Files:**
- Create: `backend/core/images.py`
- Modify: `backend/routers/export.py` (`get_card_image`), `backend/routers/deck.py` (`get_deck_card`)
- Test: `backend/tests/test_free_trial.py` (append)

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# ── 인라인 해상도 차등 ─────────────────────────────────────────────────────
from PIL import Image


def _png_size(raw: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(raw)).size


async def _seed_card(job_id: str, uid: int) -> tuple[int, int]:
    """1080×1350 카드 1장을 심고 원본 크기를 돌려준다."""
    buf = io.BytesIO()
    Image.new("RGB", (1080, 1350), (20, 120, 90)).save(buf, format="PNG")
    await _db.create_job(job_id, "p.pdf", user_id=uid)
    await _db.save_card_images(job_id, {1: buf.getvalue()})
    return (1080, 1350)


@pytest.mark.asyncio
async def test_free_user_gets_downscaled_inline_card(client):
    """★무료 유저는 화면용 축소본을 받는다 — 원본이 나가면 export 벽이 무의미해진다."""
    uid = await _mk_user("smallpng@test")
    await _seed_card("job-small", uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get("/api/cards/job-small/image/1")
    assert r.status_code == 200
    w, h = _png_size(r.content)
    assert (w, h) < (1080, 1350)
    assert w >= 400          # 화면에서 읽을 수는 있어야 한다(아하 보호)


@pytest.mark.asyncio
async def test_paid_user_gets_original_inline_card(client):
    uid = await _mk_user("bigpng@test")
    await _db.set_plan(uid, "pro")
    await _seed_card("job-big", uid)
    _as_user(dict(await _db.get_user_by_id(uid)))

    r = await client.get("/api/cards/job-big/image/1")
    assert _png_size(r.content) == (1080, 1350)


@pytest.mark.asyncio
async def test_render_service_user_gets_original(client):
    """★렌더 서비스 유저가 축소본을 받으면 산출물 품질이 통째로 망가진다."""
    uid = await _mk_user("svc@test")
    await _seed_card("job-svc", uid)
    _as_user({"id": uid, "email": "__render__", "role": "service"})

    r = await client.get("/api/cards/job-svc/image/1")
    assert _png_size(r.content) == (1080, 1350)
```

**주의:** `db.save_card_images`의 실제 이름·시그니처를 `backend/core/db.py`에서 확인해 맞춘다.

- [ ] **Step 2: `backend/core/images.py` 작성**

```python
"""서빙 레이어 이미지 변환.

무료 유저에게 인라인 카드를 축소해서 준다 — "다 보이되 못 가져간다"(순수잠금)의
'못 가져간다'를 실제로 성립시키는 조각. 게이트(402)가 아니라 해상도 차등이다.
"""
from __future__ import annotations

import io

from PIL import Image

PREVIEW_SCALE = 0.5  # 1080×1350 → 540×675. 화면에선 충분, 인스타 게시(1080)엔 부족


def downscale_png(raw: bytes, scale: float = PREVIEW_SCALE) -> bytes:
    """PNG를 비율 축소. 실패하면 원본을 그대로 돌려준다(뷰어가 깨지면 아하가 죽는다)."""
    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
        out = io.BytesIO()
        img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS).save(
            out, format="PNG", optimize=True
        )
        return out.getvalue()
    except Exception:
        return raw
```

- [ ] **Step 3: 두 경로에 배선**

`backend/routers/export.py`의 `get_card_image`(`export.py:39`) — 반환 직전에 삽입:

```python
    # 무료 유저에게는 화면용 축소본. can_export가 True면(유료·서비스 롤) 원본 그대로.
    if not plans.can_export(user):
        png = images_util.downscale_png(png)
```

`backend/routers/deck.py`의 `get_deck_card`(`deck.py:251`) — 자가치유(`_heal_card_images`) **뒤**, 반환 직전에 같은 2줄을 넣는다. (자가치유는 원본을 저장해야 하므로 순서를 지킬 것 — 축소본을 DB에 저장하면 유료 전환 후에도 영구히 저해상도가 된다.)

import는 각 파일 상단에 `from ..core import images as images_util`.

**여기에 `plans.require_can_export(user)`(402)를 넣지 말 것** — 무료 유저 뷰어가 빈 화면이 되고 아하가 죽는다. 판정은 `can_export`(bool)로만 쓴다.

- [ ] **Step 4: 테스트 통과 + 전체 회귀**

```bash
pytest backend/tests/test_free_trial.py -v
pytest backend/tests/
```

전체 스위트에서 카드 이미지 크기를 단언하는 기존 테스트가 깨지면, 그 테스트의 오버라이드 유저에 `"plan": "lab"`을 추가해 고친다(축소 로직을 약화시키지 말 것).

- [ ] **Step 5: 실브라우저 확인**

무료 계정 뷰어에서:
1. 카드가 **또렷하게 보인다**(축소본이어도 화면에선 읽힌다 — 아하 보호)
2. 이미지 URL 직접 열기 → 저장한 파일이 540×675다
3. 유료 계정에선 같은 URL이 1080×1350을 준다

- [ ] **Step 6: 커밋**

```bash
git add backend/core/images.py backend/routers/export.py backend/routers/deck.py backend/tests/test_free_trial.py
git commit -m "[BE] 무료 인라인 카드 축소 서빙 — 원본 해상도 유출 차단(게이트 아닌 해상도 차등)"
```

**성능 메모:** 뷰어가 카드 7장을 부르면 리사이즈가 7회 돈다(장당 ~10–30ms). 지금 규모에선 무시 가능. 느려지면 축소본을 `card_images`와 별도 키로 캐시하는 것이 다음 수순이다(이번 스코프 아님).

---

## 완료 검증 (전 태스크 후)

- [ ] **백엔드 전체 스위트**

```bash
pytest backend/tests/
```

기대: 전부 green. 무료체험 테스트 23개 포함.

- [ ] **프론트 전체**

```bash
cd web && npm test && npx tsc --noEmit && npm run build
```

- [ ] **E2E 시나리오 (실브라우저, 신규 계정)**

`uvicorn`을 재시작한 뒤 새 계정으로 아래를 순서대로 통과시킨다:

1. `/signup` 가입 → **온보딩이 뜬다**
2. "첫 논문 올리기" → `/deck/new` → PDF 업로드 → 생성 진행 → `/deck/<id>`에서 카드와 **✓ 검증 배지가 보인다** (아하)
3. "내보내기" 클릭 → **페이월**이 뜨고, 뒤의 덱은 여전히 보인다
4. `/dashboard` → 미터 `1 / 1`, 덱 카드 `🔒 내보내기`, 게이트 카드 존재
5. 헤더 `새 카드뉴스` → 업로드 제출 → `/upgrade?from=author`
6. 로그아웃 → 재로그인 → **온보딩이 다시 뜨지 않는다**
7. SQL로 `plan='pro'` 전환 → 미터 사라짐, export가 실제 ZIP을 내려준다

- [ ] **환불 경로 실증**

무료 계정에서 텍스트가 거의 없는 PDF(스캔본 등)를 올려 파이프라인을 `ERROR`로 끝낸 뒤, `free_decks_used`가 0으로 돌아왔는지 확인한다:

```bash
sqlite3 polyinsight.db "SELECT email, plan, free_decks_used FROM users WHERE email='<테스트계정>';"
```

- [ ] **알려진 구멍 재확인 후 보고**

무료 계정으로 로그인한 상태에서 `http://localhost:3000/api/cards/<jobId>/image/1`을 브라우저로 직접 연다. **원본 해상도 PNG가 그대로 보이면 정상**(이 플랜은 이 구멍을 막지 않는다). 완료 보고에 이 사실을 명시한다.

- [ ] **메모리 갱신**

`~/.claude/projects/.../memory/project_free_trial_model.md`에 구현 완료 사실, 실제 파일 경로, 남은 구멍(inline 원본 해상도), 다음 단계(Creem 연동·원가 실측 후 가격 확정)를 반영한다.
