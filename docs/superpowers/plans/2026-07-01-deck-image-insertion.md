# 덱 에디터 이미지 삽입 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 저작 덱 HTML에 사용자/스톡 `<img>`를 삽입하고, 삽입→저장(PATCH)→재검증(V)→재렌더 PNG→export까지 라운드트립으로 보존한다.

**Architecture:** 바이트는 `deck_assets`(BLOB)에 저장하고 저장 HTML엔 짧은 URL만 실린다. 렌더 순간에만 `deck_renderer`가 URL을 DB 바이트→data URI로 인라인해 Playwright가 쿠키·네트워크 없이 self-contained HTML을 캡처한다. 이미지 메타(asset-id/source-type/credit)는 별도 스키마가 아니라 `<img data-*>` 속성에 실려 직렬화·DB·V까지 공짜로 보존된다. 형태(프리셋)는 삽입 시점 인라인 스타일일 뿐이며 삽입 후 기존 도구(SET_RECT/이동/정렬/리사이즈)로 완전 자유 배치된다.

**Tech Stack:** 백엔드 FastAPI + aiosqlite + Playwright(async), 프론트 Next.js 15 + iframe editorAgent(ES5 문자열 주입) + axios. 테스트 = `pytest backend/tests/`(백엔드) + `tools/deck_editor_e2e/deck_harness.py`(경량 브라우저 하네스).

**출처 스펙:** `docs/superpowers/specs/2026-07-01-deck-image-insertion-design.md` (설계 승인 2026-07-01).

---

## 서브슬라이스 개요 (스펙 §10)

| 슬라이스 | 목표 | 닫는 리스크 |
|---|---|---|
| **S0** | 라운드트립 골격 — URL참조 자산 1건을 렌더시 인라인해 픽셀 증명 | auth공백·baseURL공백·직렬화생존·페인트순서·decode대기·2MB한도 (6대) |
| **S1** | 업로드 저장소 — ① 소유진실 배관(드롭존→멀티파트→deck_assets) | 실 업로드 URL로 S0 경로 구동 |
| **S2** | 스톡 배경 — 다운로드-저장 프록시 + background 프리셋(z-index 3층) + 스크림 넛지 | CDN 화이트리스트·핫링크 회피 |
| **S3** | 검증 정직화 — `upload-data` 제3분류(2경로 스키마) + 중립 배지 | verified와 섞이지 않는 provenance |
| **S4** | 마감 — SELECTED isImage 분기·export 인라인본·TTL 정합·docs 동기화 | — |

> **이 플랜은 S0을 완전한 TDD 단계로 확정한다.** S1~S4는 착수 슬라이스 진입 시 대상 파일을 재독하고 실행에서 배운 에러를 반영해 각 슬라이스 시작 시 동일한 granularity로 확장한다(backend memory: 방어 선코딩 금지 — 실호출에서 배운다). 각 슬라이스의 파일·엔드포인트·계약·테스트 불변식은 아래에 확정되어 있으므로 확장은 "코드 채우기"이지 "설계"가 아니다.

---

## File Structure

### S0가 생성/수정하는 파일

- **Modify** `backend/agents/deck/deck_renderer.py` — `render_deck(html, job_id=None)` 시그니처 확장 + `_inline_deck_assets(html, job_id)` 전처리 + `document.images decode` 대기.
- **Create** `backend/core/db.py`에 `deck_assets` 최소 테이블 + `save_deck_asset` / `get_deck_asset` — (전체 저장소는 S1에서 확장; S0은 인라인 소스로만 필요).
- **Modify** `backend/agents/deck/pipeline.py` — `persist_edited_deck`·`_execute`가 `render_deck(html, job_id)`로 호출.
- **Modify** `web/src/components/deck/editorAgent.ts` — `INSERT_IMAGE` 케이스(element 프리셋, undo 포함).
- **Modify** `web/src/components/deck/DeckEditor.tsx` — `insertImage` 핸들 + 인터페이스.
- **Test** `backend/tests/test_deck_pipeline.py` — 픽셀 diff 라운드트립(#1) + 인라인 단위(#2 서버측).
- **Test** `tools/deck_editor_e2e/deck_harness.py` — INSERT_IMAGE 브라우저 검증(직렬화 생존 #2·undo #3·activeCard #4).

### 경계 원칙 (스펙 §2, 구현 내내 준수)

- **에이전트가 형태를 소유** — 프리셋 위치·크기·z-index는 editorAgent가 계산. DeckEditor는 명령 전달만.
- **HTML이 단일 진실** — 메타는 `<img data-*>`. `CardSlot` 같은 필드스키마 신설 금지.
- **`data-pi-artifact` 부착 금지** — serialize가 제거. 메타는 `data-asset-id`/`data-source-type`/`data-provider`/`data-credit`/`data-credit-url`.
- **저장 HTML엔 base64 인라인 금지** — URL 참조. 인라인은 렌더 순간에만.
- **삽입은 `cardEls()[activeCard]` 한정** — 숨은 카드 금지.

---

## S0 — 라운드트립 골격

> S0 통과 = 라운드트립 6대 리스크가 실증적으로 닫힘. `deck_assets`에 자산 1건을 심고, 저장 HTML엔 `/api/deck/:job/assets/:id` URL만 두고, 렌더 직전 인라인해 PNG에 픽셀이 존재함을 증명한다.

### Task 0: 브랜치/환경 확인

**Files:** (없음 — 상태 점검만)

- [ ] **Step 1: 브랜치·테스트 그린 확인**

Run:
```bash
cd "C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight"
git branch --show-current
pytest backend/tests/test_deck_pipeline.py -q
```
Expected: 브랜치 `feat/v3-authoring-pipeline`, 기존 덱 테스트 PASS(베이스라인 그린).

---

### Task 1: `deck_assets` 최소 저장소 (인라인 소스)

**Files:**
- Modify: `backend/core/db.py:114-129` (migrate — authored_deck 블록 뒤에 테이블 추가), 파일 끝(save/get 함수)
- Modify: `backend/core/db.py:315-324` (delete_job — 연관 삭제에 deck_assets 추가)
- Test: `backend/tests/test_deck_pipeline.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_deck_pipeline.py` 끝에 추가:
```python
async def test_deck_asset_roundtrip():
    """자산 바이트 저장→조회 라운드트립 + delete_job 정리."""
    jid = "test-asset-rt"
    await db.delete_job(jid)
    await db.create_job(jid, title="a.pdf")
    try:
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        await db.save_deck_asset(jid, "asset-1", png, "image/png",
                                 source_type="upload-owned")
        got = await db.get_deck_asset(jid, "asset-1")
        assert got is not None
        assert got["bytes"] == png
        assert got["mime"] == "image/png"
        assert got["source_type"] == "upload-owned"
        await db.delete_job(jid)
        assert await db.get_deck_asset(jid, "asset-1") is None
    finally:
        await db.delete_job(jid)
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_deck_pipeline.py::test_deck_asset_roundtrip -q`
Expected: FAIL — `AttributeError: module 'backend.core.db' has no attribute 'save_deck_asset'`

- [ ] **Step 3: 마이그레이션 테이블 추가**

`backend/core/db.py` migrate() 안, `authored_deck` CREATE 블록 바로 뒤(닫는 `"""` 이전)에 삽입:
```sql
            -- 덱 이미지 삽입(스펙 2026-07-01): 바이트 원장. 저장 HTML엔 URL만, 렌더시 인라인.
            CREATE TABLE IF NOT EXISTS deck_assets (
                asset_id TEXT,
                job_id TEXT REFERENCES jobs(job_id),
                bytes BLOB,
                mime TEXT,
                source_type TEXT,
                source_url TEXT,
                provider TEXT,
                credit TEXT,
                credit_url TEXT,
                created_at TEXT,
                expires_at TEXT,
                PRIMARY KEY (job_id, asset_id)
            );
```

- [ ] **Step 4: save/get 함수 추가**

`backend/core/db.py`의 `get_authored_deck` 함수 뒤(줄 301 근처)에 삽입:
```python
# ── 덱 이미지 자산 (스펙 2026-07-01) ─────────────────────────────────────────

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
    ttl_hours: int = 24 * 30,  # 덱 수명 정합(스펙 §4.4). 재편집까지 생존.
) -> None:
    now = _utc_now_iso()
    expires_at = (_utc_now() + timedelta(hours=ttl_hours)).isoformat()
    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(
            """
            INSERT INTO deck_assets (
                asset_id, job_id, bytes, mime, source_type, source_url,
                provider, credit, credit_url, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, asset_id) DO UPDATE SET
                bytes = excluded.bytes, mime = excluded.mime,
                source_type = excluded.source_type, source_url = excluded.source_url,
                provider = excluded.provider, credit = excluded.credit,
                credit_url = excluded.credit_url, expires_at = excluded.expires_at
            """,
            (asset_id, job_id, data, mime, source_type, source_url,
             provider, credit, credit_url, now, expires_at),
        )
        await conn.commit()


async def get_deck_asset(job_id: str, asset_id: str) -> dict | None:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT asset_id, bytes, mime, source_type, source_url, provider, "
            "credit, credit_url FROM deck_assets "
            "WHERE job_id = ? AND asset_id = ? AND expires_at > ?",
            (job_id, asset_id, now),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_deck_assets(job_id: str) -> list[dict]:
    now = _utc_now_iso()
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT asset_id, mime, source_type FROM deck_assets "
            "WHERE job_id = ? AND expires_at > ?",
            (job_id, now),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]
```

- [ ] **Step 5: delete_job 정리 추가**

`backend/core/db.py` `delete_job` 안, `DELETE FROM card_images` 줄 뒤에 추가:
```python
        await conn.execute("DELETE FROM deck_assets WHERE job_id = ?", (job_id,))
```

- [ ] **Step 6: 통과 확인**

Run: `pytest backend/tests/test_deck_pipeline.py::test_deck_asset_roundtrip -q`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/core/db.py backend/tests/test_deck_pipeline.py
git commit -m "[BE] 덱 이미지 자산 저장소(deck_assets) — 바이트 원장 (S0)"
```

---

### Task 2: 렌더시 자산 URL→data URI 인라인 + decode 대기

**Files:**
- Modify: `backend/agents/deck/deck_renderer.py` (전체 — 인라인 전처리 + 시그니처)
- Modify: `backend/agents/deck/pipeline.py:63` 및 `:179` (render_deck 호출에 job_id 전달)
- Test: `backend/tests/test_deck_pipeline.py`

- [ ] **Step 1: 실패 테스트 작성 (인라인 단위)**

`backend/tests/test_deck_pipeline.py` 끝에 추가:
```python
async def test_inline_deck_assets_replaces_url():
    """저장 HTML의 자산 URL이 렌더 전처리에서 data URI로 치환된다(auth/base 공백 회피)."""
    from backend.agents.deck.deck_renderer import _inline_deck_assets
    jid = "test-inline"
    await db.delete_job(jid)
    await db.create_job(jid, title="i.pdf")
    try:
        png = b"\x89PNG\r\n\x1a\n" + b"\x01" * 64
        await db.save_deck_asset(jid, "aid9", png, "image/png")
        html = f'<img src="/api/deck/{jid}/assets/aid9">'
        out = await _inline_deck_assets(html, jid)
        assert "/api/deck/" not in out          # URL이 사라짐
        assert "data:image/png;base64," in out  # data URI로 치환
    finally:
        await db.delete_job(jid)
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_deck_pipeline.py::test_inline_deck_assets_replaces_url -q`
Expected: FAIL — `ImportError: cannot import name '_inline_deck_assets'`

- [ ] **Step 3: 인라인 전처리 구현**

`backend/agents/deck/deck_renderer.py` 상단 import에 추가:
```python
import base64
import re
```
그리고 `from ...core import db`를 import 블록에 추가(현재 없음):
```python
from ...core import db
```
`_CARD_H = 1350` 아래에 추가:
```python
# 저장 HTML의 자산 URL 패턴. 렌더 직전 DB 바이트→data URI로 인라인(스펙 §4.2).
_ASSET_URL_RE = re.compile(r'/api/deck/([\w-]+)/assets/([\w-]+)')


async def _inline_deck_assets(html: str, job_id: str | None) -> str:
    """set_content 전, 자산 URL을 DB 바이트→data URI로 치환.
    Playwright는 쿠키·base URL이 없어 authed 자산 URL을 못 불러온다(조용한 빈칸 렌더).
    인라인으로 self-contained HTML을 확보해 미리보기와 export PNG가 같은 픽셀로 수렴."""
    if not job_id or "/api/deck/" not in html:
        return html
    seen: dict[str, str] = {}
    for m in _ASSET_URL_RE.finditer(html):
        aid = m.group(2)
        if aid in seen:
            continue
        asset = await db.get_deck_asset(job_id, aid)
        if not asset or asset.get("bytes") is None:
            seen[aid] = ""   # 만료/부재 → 치환 안 함(§7: 플레이스홀더로 렌더 계속)
            continue
        b64 = base64.b64encode(asset["bytes"]).decode("ascii")
        seen[aid] = f'data:{asset["mime"] or "image/png"};base64,{b64}'

    def _repl(mm: "re.Match[str]") -> str:
        aid = mm.group(2)
        uri = seen.get(aid, "")
        return uri or mm.group(0)

    return _ASSET_URL_RE.sub(_repl, html)
```

- [ ] **Step 4: render_deck 시그니처·호출부 갱신 + decode 대기**

`_render_async` 함수 시그니처와 set_content 부분을 수정. `render_deck`은 job_id를 받아 인라인 후 렌더한다.

`_render_sync`와 `_render_async` 시그니처에 `html`은 이미 인라인된 것으로 취급(인라인은 async라 `render_deck`에서 수행). `render_deck` 함수를 다음으로 교체:
```python
async def render_deck(
    html: str, scale: int = 2, timeout_s: float = 30.0, job_id: str | None = None
) -> tuple[list[bytes], list[str]]:
    """저작 HTML → [PNG bytes], [warnings]. 각 [data-screen-label] 카드 1장씩(×scale 레티나).
    job_id가 있으면 렌더 전 자산 URL을 data URI로 인라인(스펙 §4.2)."""
    html = await _inline_deck_assets(html, job_id)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_deck_pool, _render_sync, html, scale, timeout_s)
```

`_render_async` 안, `page.evaluate("document.fonts && document.fonts.ready")` 블록 바로 뒤(줄 44 근처)에 decode 대기 추가:
```python
            # 안전망: 이미지 decode 완료 대기(networkidle이 디코드를 보장 안 함 → 부분 캡처 방지)
            try:
                await page.evaluate(
                    "() => Promise.all(Array.from(document.images)"
                    ".map(i => (i.decode ? i.decode().catch(() => {}) : null)))"
                )
            except Exception:
                pass
```

- [ ] **Step 5: pipeline 호출부에 job_id 전달**

`backend/agents/deck/pipeline.py` 두 곳 수정:

`persist_edited_deck` 안 (줄 63):
```python
    images, render_warns = await render_deck(html, job_id=job_id)
```
`_execute` 안 (줄 179):
```python
    images, render_warns = await render_deck(html, job_id=job_id)
```

- [ ] **Step 6: 인라인 단위 테스트 통과 확인**

Run: `pytest backend/tests/test_deck_pipeline.py::test_inline_deck_assets_replaces_url -q`
Expected: PASS

- [ ] **Step 7: 기존 렌더 테스트 회귀 확인 (job_id 없을 때 무해)**

Run: `pytest backend/tests/test_deck_pipeline.py::test_render_deck_produces_pngs -q`
Expected: PASS (job_id 기본 None → 인라인 스킵, 기존 동작 보존)

- [ ] **Step 8: 커밋**

```bash
git add backend/agents/deck/deck_renderer.py backend/agents/deck/pipeline.py backend/tests/test_deck_pipeline.py
git commit -m "[S7] 렌더시 자산 URL→data URI 인라인 + decode 대기 (S0)"
```

---

### Task 3: 라운드트립 픽셀 증명 (불변식 #1)

**Files:**
- Test: `backend/tests/test_deck_pipeline.py`

이 테스트가 S0의 심장 — 저장 HTML(URL참조) → persist_edited_deck → 재렌더 PNG가 순수 배경과 픽셀이 다름을 증명(인라인 경로 전체 관통).

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_deck_pipeline.py` 끝에 추가:
```python
async def test_inserted_image_survives_to_rendered_png():
    """자산 URL을 담은 카드 HTML → persist → 재렌더 PNG가 순수 배경 렌더와 다름.
    (인라인 경로가 실제로 픽셀을 그림 = auth/base/2MB/직렬화 리스크 실증 폐쇄)"""
    jid = "test-rt-pixel"
    await db.delete_job(jid)
    await db.create_job(jid, title="rt.pdf")
    try:
        # 눈에 띄는 단색 이미지(빨강 400x300 근사) — 실제 유효 PNG 필요.
        from PIL import Image
        import io as _io
        buf = _io.BytesIO()
        Image.new("RGB", (400, 300), (220, 40, 40)).save(buf, format="PNG")
        red_png = buf.getvalue()
        await db.save_deck_asset(jid, "redA", red_png, "image/png")

        base_html = (
            '<!DOCTYPE html><html><head><meta charset=utf-8></head><body>'
            '<div data-screen-label="01" style="width:1080px;height:1350px;'
            'position:relative;background:#0A0E1A;box-sizing:border-box"></div>'
            '</body></html>'
        )
        img_html = base_html.replace(
            '</div>',
            f'<img src="/api/deck/{jid}/assets/redA" data-asset-id="redA" '
            f'data-source-type="upload-owned" '
            f'style="position:absolute;left:340px;top:525px;width:400px;height:300px;'
            f'object-fit:cover"></div>',
        )
        # 기존 authored_deck 필요(persist가 조회) — paper_text 없이 저장.
        await db.save_authored_deck(jid, base_html, json.dumps({"verified": 0}), 1)

        # 베이스라인(이미지 없음) 렌더
        base_imgs, _ = await deck_renderer.render_deck(base_html, scale=1, job_id=jid)
        # 삽입본 저장 + 재렌더
        result = await persist_edited_deck(jid, img_html)
        got = await db.get_card_images(jid)
        assert len(got) >= 1
        assert base_imgs and got[1] != base_imgs[0]     # 픽셀이 달라짐
        # 저장 HTML은 URL 참조 유지(2MB 한도 — base64 저장 금지)
        deck = await db.get_authored_deck(jid)
        assert "/api/deck/" in deck["html"]
        assert "data:image/png;base64," not in deck["html"]
        assert 'data-asset-id="redA"' in deck["html"]   # 메타 직렬화 생존
    finally:
        await db.delete_job(jid)
```

- [ ] **Step 2: 실패/통과 실행**

Run: `pytest backend/tests/test_deck_pipeline.py::test_inserted_image_survives_to_rendered_png -q`
Expected: PASS (Task 1·2가 이미 배관을 깔았으므로 이 테스트는 통합 증명). 만약 `PIL` 미설치면 `pip install pillow` 후 재실행 — Playwright 스택에 이미 포함일 가능성 높음. 실패 시 원인(인라인 누락/렌더 0장)을 raw 로그로 확인 후 수정.

- [ ] **Step 3: 커밋**

```bash
git add backend/tests/test_deck_pipeline.py
git commit -m "[S7] 라운드트립 픽셀 증명 — 자산 URL→인라인→PNG (S0 불변식#1)"
```

---

### Task 4: editorAgent `INSERT_IMAGE` (element 프리셋 + undo)

**Files:**
- Modify: `web/src/components/deck/editorAgent.ts:652` (DELETE_ELEMENT 케이스 앞/뒤에 INSERT_IMAGE 추가)
- Modify: `web/src/components/deck/DeckEditor.tsx:32-45` (인터페이스) 및 `:78-95` (핸들)

- [ ] **Step 1: editorAgent INSERT_IMAGE 케이스 추가**

`web/src/components/deck/editorAgent.ts`의 `window.addEventListener('message', ...)` switch 안, `case 'DELETE_ELEMENT':` 바로 앞에 삽입:
```javascript
      case 'INSERT_IMAGE': {
        var cards = cardEls();
        var card = cards[activeCard];   // 삽입 대상 = 현재 보이는 카드만(숨은 카드 금지)
        if (!card) break;
        if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
        var img = document.createElement('img');
        img.src = d.url;
        // 메타는 data-* 로(serialize가 data-pi-* 만 제거 → 이건 생존). data-pi-artifact 절대 금지.
        img.setAttribute('data-asset-id', d.assetId || '');
        img.setAttribute('data-source-type', d.sourceType || 'upload-owned');
        if (d.provider) img.setAttribute('data-provider', d.provider);
        if (d.credit) img.setAttribute('data-credit', d.credit);
        if (d.creditUrl) img.setAttribute('data-credit-url', d.creditUrl);
        // element 프리셋: absolute + 명시 px(height:auto 금지 — setRect/resize의 offsetWidth 로직이 px 요구).
        var IW = 400, IH = 300;
        img.style.position = 'absolute';
        img.style.width = IW + 'px';
        img.style.height = IH + 'px';
        img.style.left = ((CARD_W - IW) / 2) + 'px';
        img.style.top = ((CARD_H - IH) / 2) + 'px';
        img.style.objectFit = 'cover';
        // undo 보편성(3e 불변식): 삽입도 되돌리기 가능. run=append, undo=remove.
        pushCmd({
          run: function () { card.appendChild(img); },
          undo: function () { if (img.parentNode) img.parentNode.removeChild(img); }
        });
        card.appendChild(img);
        select(img);
        afterMutate();
        break;
      }
```

- [ ] **Step 2: DeckEditor 인터페이스 + 핸들 추가**

`web/src/components/deck/DeckEditor.tsx`의 `DeckEditorHandle` 인터페이스에 추가(줄 44 `setPage` 뒤):
```typescript
  insertImage: (p: {
    url: string; assetId?: string; sourceType?: string
    provider?: string; credit?: string; creditUrl?: string
  }) => void
```
`useImperativeHandle` 반환 객체에 추가(줄 94 `setPage` 뒤):
```typescript
    insertImage: (p) => send('INSERT_IMAGE', p),
```

- [ ] **Step 3: 프론트 타입체크**

Run:
```bash
cd web && npx tsc --noEmit
```
Expected: 에러 없음(인터페이스·핸들 정합).

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/deck/editorAgent.ts web/src/components/deck/DeckEditor.tsx
git commit -m "[WEB] editorAgent INSERT_IMAGE(element 프리셋+undo) + DeckEditor 핸들 (S0)"
```

---

### Task 5: 브라우저 하네스 — 직렬화 생존·undo·activeCard (불변식 #2·#3·#4)

**Files:**
- Modify: `tools/deck_editor_e2e/deck_harness.py` (INSERT_IMAGE 테스트 함수 추가 + main에 연결)

- [ ] **Step 1: 하네스 테스트 함수 추가**

`tools/deck_editor_e2e/deck_harness.py`의 `test_baseline()` 함수 뒤에 추가:
```python
def test_insert_image():
    """INSERT_IMAGE: activeCard 삽입 + 직렬화 생존(data-asset-id 유지, data-pi 0) + undo/redo."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser, page = make_page(pw)   # SET_MODE edit(=paged), activeCard=0
        results = []

        def check(name, cond):
            results.append((name, bool(cond)))

        # 카드2(index1)로 페이지 이동 후 삽입 → 카드2에만 들어가야 함
        goto_card(page, 1)
        clear_msgs(page)
        host(page, "INSERT_IMAGE", url="data:image/gif;base64,R0lGODlhAQABAAAAACwAAAAAAQABAAA=",
             assetId="A1", sourceType="upload-owned")
        page.wait_for_timeout(150)

        counts = page.evaluate("""() => {
          const cards = document.querySelectorAll('[data-screen-label]');
          return [cards[0].querySelectorAll('img').length, cards[1].querySelectorAll('img').length];
        }""")
        check("삽입: activeCard(카드2)에 img 1개", counts[1] == 1)
        check("삽입: 다른 카드(카드1)엔 0개", counts[0] == 0)

        sel = last(page, "SELECTED")
        check("삽입 후 img 선택", sel is not None and sel.get("tag") == "img")

        # 직렬화 생존
        html = get_html(page)
        check("serialize: data-asset-id 생존", 'data-asset-id="A1"' in html)
        check("serialize: data-source-type 생존", 'data-source-type="upload-owned"' in html)
        check("serialize: data-pi 아티팩트 0", "data-pi-" not in html)
        check("serialize: img 1개", html.count("<img") == 1)

        # undo → img 제거, redo → 복원
        host(page, "UNDO"); page.wait_for_timeout(120)
        after_undo = page.evaluate("() => document.querySelectorAll('img').length")
        check("undo→img 제거", after_undo == 0)
        host(page, "REDO"); page.wait_for_timeout(120)
        after_redo = page.evaluate("() => document.querySelectorAll('img').length")
        check("redo→img 복원", after_redo == 1)

        browser.close()

        print("\n=== INSERT_IMAGE (S0) ===")
        ok = True
        for name, passed in results:
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
            ok = ok and passed
        return ok
```

- [ ] **Step 2: main에 연결**

`deck_harness.py` 파일 맨 아래 `if __name__ == "__main__":` 블록에서 `test_baseline()` 호출 뒤에 `test_insert_image()`도 실행하도록 추가(기존 실행 구조에 맞춰 append). 기존 구조가 `test_baseline()` 단일 호출이면:
```python
if __name__ == "__main__":
    ok1 = test_baseline()
    ok2 = test_insert_image()
    sys.exit(0 if (ok1 and ok2) else 1)
```
(기존 main이 이미 여러 테스트를 리스트로 돌리면 그 리스트에 `test_insert_image` 추가.)

- [ ] **Step 3: 하네스 실행**

Run:
```bash
python tools/deck_editor_e2e/deck_harness.py
```
Expected: INSERT_IMAGE 섹션 전 체크 PASS + 기존 베이스라인 PASS 유지.

- [ ] **Step 4: 커밋**

```bash
git add tools/deck_editor_e2e/deck_harness.py
git commit -m "[WEB] 하네스 INSERT_IMAGE 검증 — 직렬화생존·undo·activeCard (S0 불변식#2·3·4)"
```

---

### Task 6: S0 통합 확인 + 임시 삽입 버튼(연기 결정)

**Files:** (없음 — S0 종료 게이트)

- [ ] **Step 1: 백엔드 전 스위트 그린**

Run: `pytest backend/tests/`
Expected: 전 통과(신규 4개 포함, 기존 회귀 없음).

- [ ] **Step 2: 하네스 전 통과**

Run: `python tools/deck_editor_e2e/deck_harness.py`
Expected: 전 체크 PASS.

- [ ] **Step 3: S0 완료 판정 기록**

S0 = 6대 리스크(auth공백·baseURL공백·직렬화생존·페인트순서·decode대기·2MB한도)가 테스트로 닫힘.
UI 진입점(패널 버튼)은 **S1에서** 실 업로드와 함께 붙인다(S0은 배관 증명이 목적, 임시 버튼 불필요).
메모리 `project_deck_image_insertion.md` 갱신: "S0 완료, 다음 S1".

---

## S1 — 업로드 저장소 (① 소유진실 배관) — 착수 시 확장

> S0 배관 위에 실제 업로드 소스를 붙인다. 저위험 증분.

**확정 파일·계약:**
- Modify `backend/routers/deck.py` — `POST /api/deck/{job_id}/assets`(multipart `file`, `source_type` Form) → `save_deck_asset` → `{assetId, url}`. `GET /api/deck/{job_id}/assets/{asset_id}` → `Response(bytes, media_type=mime)`. mime 화이트리스트(`image/png|jpeg|webp|gif`), 최대 크기(예 8MB), SVG는 거부 또는 스크립트 제거(§7).
- Modify `web/src/lib/api.ts` — `uploadDeckAsset(jobId, file, sourceType)`(multipart) + `getDeckAssetUrl(jobId, assetId)`.
- Create `web/src/components/deck/DeckMediaPanel.tsx` — 업로드 드롭존(구 `RightPanel.tsx`는 **UI 마크업만** 참고, onImageUpdate 슬롯배관 이식 금지). `onInsert(url, preset, sourceType, meta)`.
- Modify `web/src/app/deck/[jobId]/page.tsx` — 편집 aside에 `DeckMediaPanel` 마운트, `onInsert` → `editorRef.current?.insertImage(...)`.

**불변식/테스트:**
- `POST assets` → deck_assets 저장 → `GET assets/:id`가 바이트·mime 반환(`test_api.py` 또는 `test_deck_pipeline.py`).
- 크기/mime 초과 → 4xx(막지 않고 패널 인라인 에러).
- 업로드 URL로 삽입 → S0 픽셀 라운드트립 재현(실 업로드 경로 E2E).
- 스톡 키 없음과 무관하게 업로드 경로 독립 동작(§7).

**docs 선행:** `docs/contracts/07_api_data_model.md`에 3 엔드포인트 + `deck_assets` + `<img data-*>` 규약 추가(헌법 §4 docs→code).

---

## S2 — 스톡 배경 (다운로드-저장) — 착수 시 확장

**확정 파일·계약:**
- Modify `backend/routers/deck.py` — `POST /api/deck/{job_id}/assets/from-stock {url, credit, provider, credit_url}` → **라우터 async httpx**로 CDN fetch(렌더 스레드풀 충돌 회피) → **CDN 호스트 화이트리스트**(Pexels/Unsplash 도메인, SSRF 방지) → `save_deck_asset(kind=stock, source_url, credit...)` → `{assetId, url}`.
- Modify `web/src/components/deck/DeckMediaPanel.tsx` — 스톡 검색(`searchStockImages`/`/api/images/search` 재사용, `RightPanel` 검색 UI 참고) + 프리셋 토글("배경으로"/"요소로").
- Modify `web/src/components/deck/editorAgent.ts` — `INSERT_IMAGE`에 `preset:'background'` 분기: `position:absolute; inset:0; object-fit:cover; z-index:-2`. **스크림 넛지**: 삽입 후 img가 텍스트리프 형제를 덮으면 `SCRIM_SUGGEST` post. `APPLY_SCRIM` 명령 = wrapper div로 img 감싸고 그라디언트 형제(z-index img 위·텍스트 아래) 삽입.

**불변식/테스트:**
- background 프리셋 z-index 3층 페인트 순서(텍스트가 이미지 위) — 하네스 실브라우저.
- from-stock 화이트리스트 밖 호스트 → 거부. 다운로드 실패 → 삽입 취소(부분 상태 금지, §7).
- 스크림-이미지 wrapper 단위 이동/삭제(고아 스크림 방지).

**docs 선행:** `18_card_design_system.md`에 프리셋("배경으로"/"요소로")과 구 `image_mode`(신 덱 미적용) 관계 명시.

---

## S3 — 검증 정직화 (② 천장 오버라이드 + 데이터도표) — 착수 시 확장

**확정 파일·계약:**
- Modify `backend/core/fidelity.py` `verify_deck` — `data-source-type="upload-data"` `<img>`(및 사용자 캡션 서브트리) 내 수치를 **제3 버킷**(verified도 unverified도 아님)으로. NumberClaim에 `status`/`provenance` 필드 추가.
- Modify `backend/agents/deck/pipeline.py` — **직렬화 2곳 동시 수정**: `_verify_to_json`(편집 재검증)과 `_execute` 인라인(최초 생성). 스키마에 `userProvided:int` + claim별 `status`(한쪽만 고치면 편집 후 라벨 소실).
- Modify `web/src/components/deck/DeckMediaPanel.tsx` — "데이터 도표" 체크박스 → 삽입 시 `data-source-type="upload-data"`.
- Modify `web/src/app/deck/[jobId]/page.tsx` — `VerifyClaim`/`VerifyData`에 상태/카운트. aside에 **중립톤 배지**(amber=AI added와 시각 구분, verified와 절대 안 섞음 — NEVER label verified unless proven).

**불변식/테스트:**
- `upload-data` 마킹 캡션 수치 → 제3분류. 마커 없는 캡션 → 기존 대조(`test_verify_deck_classifies_provenance` 확장).
- 직렬화 2경로 스키마 동일성 — 편집 후 라벨 소실 없음.

**docs 선행:** `07_api_data_model.md`에 verify 스키마 `status`/`userProvided` 추가.

---

## S4 — 마감 — 착수 시 확장

**확정 작업:**
- Modify `web/src/app/deck/[jobId]/page.tsx` / `DeckElementPanel.tsx` — `SELECTED`에 `isImage` 분기(이미지 선택 시 스크림/데이터도표 컨트롤 표면).
- export ZIP — 원본 assets/ 폴더 동봉(소유진실 재사용, 스펙 §9 결정). `backend/routers/deck.py` `export_deck`에 `list_deck_assets` 루프.
- TTL 정합 확인(deck_assets = 덱 수명, `save_deck_asset` ttl_hours 이미 720h). 만료 감지 시 프론트 "이미지 재업로드 필요" 표시.
- docs 최종 동기화(`07`, `18`, 선택 `12`) + 메모리 갱신.

---

## Self-Review (스펙 대조)

- **§3.1 삽입 두 소스**: 스톡=S2, 업로드=S1. ✅
- **§3.2 에이전트 삽입**: activeCard 한정·data-* 메타·undo·프리셋 = Task 4 + S2 background. ✅
- **§3.3 저장→재검증→재렌더**: persist_edited_deck 기존 경로 재사용 + Task 2 인라인. ✅
- **§4 저장 설계**: deck_assets(Task 1) + URL참조+렌더시인라인(Task 2·3). ✅
- **§5 프리셋**: element=Task 4, background=S2. ✅
- **§6 충실성 정직화**: S3(2경로 스키마 + 중립 배지). ✅ (§6.1 코드 무변경 — 방어 선작성 안 함)
- **§7 degrade**: mime/크기=S1, from-stock 실패=S2, 인라인 실패 플레이스홀더=Task 2 `_repl`. ✅
- **§8 테스트**: #1 Task 3, #2·3·4 Task 5, #5·6 S3, #7·8·9 S2/S1. ✅
- **§9 docs 선행**: 각 슬라이스에 docs 선행 명시. ✅
- **§10 순서**: S0 완전, S1~S4 확정 계약. ✅
- **열린 질문**: 덱 토큰 변수명(`--set-radius`) → S2 background border-radius 시 저작 덱 HTML 실측(Task에 없음 — element 프리셋은 radius 미적용이라 S0 무관). ⚠️ S2 착수 시 확인.

**Type 일관성:** `save_deck_asset`/`get_deck_asset`(Task1) → `_inline_deck_assets`가 `asset["bytes"]`/`asset["mime"]` 사용(Task2) 정합. `render_deck(html, scale, timeout_s, job_id)` 시그니처 → pipeline 두 호출부 정합(Task2 Step5). `insertImage({url, assetId, sourceType, provider, credit, creditUrl})` 핸들 → editorAgent `d.url/d.assetId/...` 정합(Task4).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-01-deck-image-insertion.md`.**

S0을 즉시 시작한다(사용자 지시). 슬라이스 내 각 Task는 TDD(실패 테스트→최소 구현→통과→커밋).
