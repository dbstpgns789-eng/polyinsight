# AI 도우미 계약 (서브프로젝트 ②) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자연어/원클릭 AI 편집을 **미커밋 propose → 확인 → commit** 2단계로 만들고, 편집 대상을 요소 단위로 앵커(`data-eid`)하며, AI 편집을 스냅샷으로 되돌릴 수 있게 하는 **계약(백엔드+iframe+프론트 배관)** 을 완성한다.

**Architecture:** 선택 시 iframe editorAgent가 요소에 불투명 난수 `data-eid`를 스탬프하고 `SELECTED` 페이로드에 `{eid, cardIndex, quotedText}`를 실어 보낸다. 프론트는 **캔버스 라이브 `serialize()` html**과 `target`을 새 `POST /deck/{id}/nlpatch/propose`(미저장·미렌더)로 보낸다. 응답 `{html, verify}`은 미커밋 상태로 유지되고, `data-eid`로 before/after 텍스트를 프론트에서 추출해 미리보기한다. **[✓ 적용]** 시에만 기존 `PATCH /deck/{id}`(commit=저장+재검증+PNG 재렌더)로 반영하고, commit 직전 html을 부모(React) 스냅샷 스택에 push해 **AI 되돌리기**를 제공한다.

**Tech Stack:** FastAPI(Python) + pydantic / Next.js(React 19) + TypeScript / iframe editorAgent(주입 문자열, ES5) / pytest(backend) · vitest(node 순수모듈) · 라이브 브라우저 E2E.

> **스펙:** `docs/superpowers/specs/2026-07-08-deck-editor-redesign-design.md` §4.2·§5·§9·§11. 이 서브프로젝트 = 스펙 §11 "② AI 도우미 계약".

---

## 테스트 인프라 현실 (스펙 §10 가정 검증 결과 — 반드시 숙지)

`web/vitest.config.mts`: `environment: 'node'`, `include: ['src/**/*.test.ts']`. **jsdom·testing-library 없음.** 기존 테스트(`focal.test.ts` 등)는 전부 **순수 로직 `.ts`**. 따라서:

- **백엔드 계약** → `pytest backend/tests/` (DEV_MOCK_LLM + render mock). ✅ 유닛 테스트
- **순수 프론트 모듈**(`deckDiff.ts`) → vitest node. ✅ 유닛 테스트
- **iframe editorAgent**(주입 문자열, 브라우저 전용) + **React 컴포넌트/페이지 배선** → node 유닛 테스트 불가. **라이브 브라우저 E2E**로 검증(프로젝트 기존 관행 — `project_phase3_deck_editor` 메모). 이 계획은 jsdom을 도입하지 않는다(스코프 밖).

이 분리는 각 태스크의 "검증" 단계에 반영돼 있다. iframe/컴포넌트 태스크는 유닛 테스트를 **날조하지 않고** 라이브 E2E(Task 9)로 증명한다.

---

## 파일 구조 (생성/수정 대상)

| 파일 | 책임 | 태스크 |
|---|---|---|
| `docs/contracts/07_api_data_model.md` | nlpatch propose + target 계약 문서화(docs-first) | 1 |
| `backend/agents/deck/edit_prompts.py` | EDIT_SYSTEM `data-eid` 보존 규칙 + target 앵커 블록 | 2 |
| `backend/agents/deck/nl_patch.py` | `apply_nl_patch`에 `target` 파라미터 | 2 |
| `backend/agents/deck/pipeline.py` | `compute_verify`(검증만, 저장·렌더 없음) 공개 | 3 |
| `backend/routers/deck.py` | `POST /deck/{id}/nlpatch/propose` + 요청 모델 | 3 |
| `backend/tests/test_edit_prompts.py` (신규) | build_user_prompt target 유닛 테스트 | 2 |
| `backend/tests/test_api.py` | propose 라우트 테스트 | 3 |
| `web/src/components/deck/editorAgent.ts` | 선택 시 `data-eid` 스탬프 + SELECTED 확장 | 4 |
| `web/src/components/deck/DeckEditor.tsx` | `SelectedInfo`에 eid/cardIndex/quotedText | 5 |
| `web/src/lib/api.ts` | `nlProposeDeck` 클라이언트 | 5 |
| `web/src/lib/deckDiff.ts` (신규) | `extractEidText` 순수 함수(before/after) | 6 |
| `web/src/lib/deckDiff.test.ts` (신규) | 위 유닛 테스트 | 6 |
| `web/src/components/deck/DeckAIAssistant.tsx` (신규) | AI 도우미 패널(제안·미리보기·적용/다른안/취소·되돌리기) | 7 |
| `web/src/app/deck/[jobId]/page.tsx` | propose/commit/스냅샷 되돌리기 오케스트레이션 배선 | 8 |

**계약 불변(건드리지 않음):** `serialize()`가 `data-pi-*`만 제거하므로 `data-eid`는 생존 — editorAgent serialize 로직 무수정. 기존 `POST /deck/{id}/nlpatch`(즉시저장) 라우트는 **남겨둔다**(테스트 그린 유지, 프론트만 propose+commit로 전환). `DeckNLBar.tsx`는 사용처만 제거(파일 삭제는 ① 정리로 유보).

---

## Task 1: docs-first — nlpatch propose + target 계약 문서화

**Files:**
- Modify: `docs/contracts/07_api_data_model.md` (§1-7 덱 API 섹션 끝, 현재 line 384 `---` 앞)

스펙 §5 "docs/contracts/07 갱신 선행(docs-first)". 코드 전에 계약을 문서화한다. 현재 07 문서엔 `nlpatch` 자체가 미기재이므로 **기존 nlpatch(commit 경로)와 신규 propose를 함께** 추가한다.

- [ ] **Step 1: 덱 API 섹션 끝(line 384 `---` 직전)에 다음을 삽입**

```markdown
#### `POST /api/deck/:jobId/nlpatch/propose` — AI 편집 제안 (미커밋)

자연어/원클릭 지시로 덱 HTML을 **최소 변경 수정한 결과를 미리보기용으로 반환**한다. **저장하지 않고 PNG도 렌더하지 않는다**(유료 LLM 1콜). 사용자가 확인 후 `PATCH /api/deck/:jobId`(commit)로만 반영된다.

**Request** — `application/json`
```json
{
  "instruction": "한 줄로 짧게",
  "html": "<!DOCTYPE html>…",
  "target": { "eid": "eab12cd3", "cardIndex": 2, "quotedText": "현재 요소 텍스트" }
}
```
- `html`: **캔버스 라이브 `serialize()` 결과**(DB의 `deck.html`이 아님). 선택 시 스탬프된 `data-eid`가 이 html에 존재해야 하고, 미저장 직접편집도 여기에 보존된다.
- `target`(선택): 편집 대상 요소 앵커. `eid`는 iframe이 선택 시 부여한 불투명 난수. 있으면 프롬프트가 "이 요소만" 수정하도록 앵커하고, LLM은 `data-eid`를 원형 보존한다.

**Response** `200 OK`
```json
{ "html": "<!DOCTYPE html>…(수정본)", "verify": { "verified": 12, "unverified": 1, "claims": [ … ] } }
```
- `verify`: 수정본을 원문(`paper_text`)과 대조한 결과. 원문 없으면 `{verified:0, unverified:0, claims:[], skipped:true}`.
- **DB·PNG 불변**(저장/렌더는 commit 전용).

**에러**: 잡/덱 없음 404(ERR-JOB-001) · 수정 결과가 카드 구조 이탈(`data-screen-label` 소실) 422(ERR-EDIT-001, 원본 보존).

#### `PATCH /api/deck/:jobId` (commit — 기재 보강)

직접조작 저장과 **AI 제안 적용(commit)** 공용. 요청 `{ "html": "…" }` 저장 → 재검증 + PNG 재렌더. AI 되돌리기는 클라이언트가 commit 직전 html을 스냅샷해 두었다가 이 엔드포인트로 재저장한다(서버는 무상태).

#### `<element data-eid>` — 편집 앵커 규약

iframe editorAgent가 요소 선택 시 부여하는 **불투명 난수 id**(예: `data-eid="eab12cd3"`). 위치·서수 기반이 아니라 요소에 고정된다(MOVE/DELETE/INSERT로 서수가 밀려도 충돌 없음). `data-pi-*`가 아니므로 `serialize()`에서 생존하며 propose·commit·DB까지 보존된다. LLM 편집 시 원형 유지가 강제된다(EDIT_SYSTEM 규칙).
```

- [ ] **Step 2: 커밋**

```bash
git add docs/contracts/07_api_data_model.md
git commit -m "[DOCS] nlpatch propose(미커밋) + target/data-eid 계약 문서화 (docs-first, 스펙 ②)"
```

---

## Task 2: 편집 프롬프트 target 앵커 + apply_nl_patch target 파라미터

**Files:**
- Modify: `backend/agents/deck/edit_prompts.py:9-51`
- Modify: `backend/agents/deck/nl_patch.py:22-47`
- Test: `backend/tests/test_edit_prompts.py` (신규)

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_edit_prompts.py`

```python
# -*- coding: utf-8 -*-
"""편집 프롬프트 target 앵커 유닛 테스트 (순수 함수, LLM 없음)."""
from backend.agents.deck.edit_prompts import build_user_prompt, EDIT_SYSTEM


def test_build_user_prompt_includes_target_block():
    p = build_user_prompt(
        "<html>x</html>", "짧게", "원문 텍스트", html_cap=1000,
        target={"eid": "e9", "quotedText": "긴 제목 텍스트"},
    )
    assert 'data-eid="e9"' in p
    assert "긴 제목 텍스트" in p
    assert "편집 대상 요소" in p


def test_build_user_prompt_no_target_omits_block():
    p = build_user_prompt("<html>x</html>", "짧게", None, html_cap=1000)
    assert "편집 대상 요소" not in p


def test_build_user_prompt_target_without_eid_omits_block():
    p = build_user_prompt("<html>x</html>", "짧게", None, html_cap=1000,
                          target={"eid": None, "quotedText": "x"})
    assert "편집 대상 요소" not in p


def test_edit_system_has_eid_preservation_rule():
    assert "data-eid" in EDIT_SYSTEM
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest backend/tests/test_edit_prompts.py -v`
Expected: FAIL — `build_user_prompt() got an unexpected keyword argument 'target'` (및 EDIT_SYSTEM에 data-eid 없음)

- [ ] **Step 3: `edit_prompts.py` 수정** — EDIT_SYSTEM 출력 계약에 규칙 1줄 추가, EDIT_USER에 target 슬롯, build_user_prompt에 target 파라미터

`EDIT_SYSTEM`의 `[출력 계약 — 엄수 …]` 블록 마지막 줄(현재 line 23 `- 코드펜스(...) 전문만 출력한다(부분 출력 금지).`) **뒤에** 다음 줄을 추가:

```
- **data-eid 보존**: `data-eid` 속성이 붙은 요소는 그 속성을 **원형 그대로 유지**한다(편집 후에도 동일한 data-eid). 제거·변경·재부여 금지.
```

`EDIT_USER`(line 30-41)를 다음으로 교체:

```python
EDIT_USER = """## 원문 (유일한 사실 소스 — 수치 판단 기준)
{paper_text}

## 현재 덱 HTML (이 문서를 보존하며 최소 수정)
{html}
{target_block}
---
## 사용자 지시
{instruction}

---
위 지시대로 현재 덱을 최소 변경으로 수정한 **HTML 전문**만 출력하라(코드펜스·설명 없이)."""

_TARGET_TMPL = """
---
## 편집 대상 요소 (이 요소에만 지시 적용 — data-eid로 식별)
- data-eid="{eid}" — 이 속성을 **원형 그대로 유지**한다(제거·변경 금지).
- 현재 텍스트: {quoted}
다른 요소·카드·색·레이아웃은 그대로 둔다."""
```

`build_user_prompt`(line 46-51)를 다음으로 교체:

```python
def build_user_prompt(
    html: str, instruction: str, paper_text: str | None, *,
    html_cap: int, target: dict | None = None,
) -> str:
    target_block = ""
    if target and target.get("eid"):
        target_block = _TARGET_TMPL.format(
            eid=target["eid"],
            quoted=(target.get("quotedText") or "")[:500],
        )
    return EDIT_USER.format(
        paper_text=(paper_text or _NO_PAPER)[:html_cap],
        html=html[:html_cap],
        instruction=instruction.strip(),
        target_block=target_block,
    )
```

- [ ] **Step 4: `nl_patch.py`의 `apply_nl_patch`에 target 파라미터 배선**

`apply_nl_patch` 시그니처(line 22)를 교체:

```python
async def apply_nl_patch(
    html: str, instruction: str, paper_text: str | None, target: dict | None = None,
) -> str:
```

`build_user_prompt` 호출(line 34)을 교체:

```python
    user = P.build_user_prompt(html, instruction, paper_text, html_cap=_MAX_INPUT_CHARS, target=target)
```

(DEV_MOCK_LLM 마커 경로·나머지는 무변.)

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest backend/tests/test_edit_prompts.py -v`
Expected: PASS (4개)

- [ ] **Step 6: 회귀 — 기존 nlpatch 테스트 그린 확인**

Run: `pytest backend/tests/test_api.py -k nlpatch -v`
Expected: PASS (`test_nlpatch_mock_applies_and_rerenders`, `test_nlpatch_404_when_no_deck`, `test_nlpatch_rejects_broken_contract` — target 기본값 None이라 기존 호출 무영향)

- [ ] **Step 7: 커밋**

```bash
git add backend/agents/deck/edit_prompts.py backend/agents/deck/nl_patch.py backend/tests/test_edit_prompts.py
git commit -m "[BE] 편집 프롬프트 target 앵커 + data-eid 보존 규칙 (스펙 ②)"
```

---

## Task 3: propose 엔드포인트 (미저장·미렌더)

**Files:**
- Modify: `backend/agents/deck/pipeline.py:42` (뒤에 `compute_verify` 추가)
- Modify: `backend/routers/deck.py:13-14, 107-135`
- Test: `backend/tests/test_api.py` (propose 테스트 추가)

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_api.py`의 `test_nlpatch_rejects_broken_contract`(line 568 끝) **뒤에** 추가

```python
@pytest.mark.asyncio
async def test_nlpatch_propose_returns_html_verify_without_persist(client, monkeypatch):
    """propose는 수정본 html+verify를 반환하되 DB 저장·PNG 렌더를 하지 않는다."""
    monkeypatch.setattr(settings, "DEV_MOCK_LLM", True)
    render_mock = AsyncMock(return_value=([b"\x89PNG"], []))
    monkeypatch.setattr("backend.agents.deck.pipeline.render_deck", render_mock)
    await _db.create_job("jprop", "p.pdf", user_id=1)
    await _db.save_authored_deck("jprop", _DECK_HTML, json.dumps({"verified": 1, "unverified": 0}),
                                 1, paper_text="The model scored 28.4 BLEU.")
    live_html = _DECK_HTML.replace("BLEU 28.4", 'BLEU 28.4 <span data-eid="e1">최고</span>')
    resp = await client.post(
        "/api/deck/jprop/nlpatch/propose",
        json={"instruction": "한 줄로", "html": live_html,
              "target": {"eid": "e1", "cardIndex": 0, "quotedText": "최고"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "html" in body and "verify" in body
    assert "data-screen-label" in body["html"]     # 계약 보존
    assert "nlpatch-mock" in body["html"]           # apply_nl_patch mock 경로 실행
    assert "verified" in body["verify"]
    render_mock.assert_not_called()                 # PNG 렌더 안 함
    deck = await _db.get_authored_deck("jprop")
    assert deck["html"] == _DECK_HTML               # DB 원본 불변(저장 안 함)


@pytest.mark.asyncio
async def test_nlpatch_propose_404_when_no_deck(client):
    resp = await client.post("/api/deck/nope/nlpatch/propose",
                             json={"instruction": "x", "html": "<html></html>"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nlpatch_propose_422_on_broken_contract(client, monkeypatch):
    """수정 결과가 카드 구조를 벗어나면 422(원본 보존, 저장 안 함)."""
    monkeypatch.setattr(
        "backend.routers.deck.apply_nl_patch",
        AsyncMock(return_value="<html><body>카드 라벨 없는 깨진 출력</body></html>"),
    )
    await _db.create_job("jpbad", "p.pdf", user_id=1)
    await _db.save_authored_deck("jpbad", _DECK_HTML, json.dumps({"verified": 1}), 1, paper_text="x")
    resp = await client.post("/api/deck/jpbad/nlpatch/propose",
                             json={"instruction": "전부 지워", "html": _DECK_HTML})
    assert resp.status_code == 422
    deck = await _db.get_authored_deck("jpbad")
    assert deck["html"] == _DECK_HTML
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest backend/tests/test_api.py -k propose -v`
Expected: FAIL — 404 (route `/nlpatch/propose` 미존재)

- [ ] **Step 3: `pipeline.py`에 `compute_verify` 추가** — `_verify_to_json`(line 31-42) **뒤에**

```python
def compute_verify(html: str, paper_text: str | None) -> dict:
    """검증만 수행(저장·렌더 없음) — nlpatch propose 미커밋 미리보기용."""
    _, payload = _verify_to_json(html, paper_text)
    return payload
```

- [ ] **Step 4: `deck.py` import 보강** — line 14를 교체

```python
from ..agents.deck.pipeline import compute_verify, persist_edited_deck, run_authoring_pipeline
```

- [ ] **Step 5: `deck.py`에 요청 모델 + propose 라우트 추가** — 기존 `nlpatch_deck`(line 135 `return result` 끝) **뒤에**

```python
class DeckNLTarget(BaseModel):
    eid: str | None = None
    cardIndex: int | None = None
    quotedText: str | None = Field(default=None, max_length=4000)


class DeckNLPropose(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)
    html: str = Field(min_length=1, max_length=2_000_000)
    target: DeckNLTarget | None = None


@router.post("/deck/{job_id}/nlpatch/propose")
async def nlpatch_propose(job_id: str, body: DeckNLPropose, user: dict = Depends(get_current_user)):
    """AI 편집 제안 — 미저장·미렌더. 라이브 캔버스 html + target으로 최소 변경 수정본을
    만들어 verify와 함께 반환한다. 실제 반영은 PATCH /deck/{id}(commit)에서만."""
    await require_owned_job(job_id, user)
    deck = await db.get_authored_deck(job_id)
    if deck is None or not deck.get("html"):
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})

    new_html = await apply_nl_patch(
        body.html, body.instruction, deck.get("paper_text"),
        target=body.target.model_dump() if body.target else None,
    )
    if "data-screen-label" not in new_html:
        raise HTTPException(
            422,
            detail={"code": "ERR-EDIT-001",
                    "message": "수정 결과가 덱 구조를 벗어나 제안하지 않았습니다. 원본은 그대로입니다."},
        )

    verify = compute_verify(new_html, deck.get("paper_text"))
    await db.log_event("deck_edit", user_id=user["id"], job_id=job_id, payload={"kind": "nl-propose"})
    return {"html": new_html, "verify": verify}
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `pytest backend/tests/test_api.py -k propose -v`
Expected: PASS (3개)

- [ ] **Step 7: 백엔드 전체 회귀**

Run: `pytest backend/tests/`
Expected: 전부 PASS (기존 스위트 + 신규 propose/prompt)

- [ ] **Step 8: 커밋**

```bash
git add backend/routers/deck.py backend/agents/deck/pipeline.py backend/tests/test_api.py
git commit -m "[BE] nlpatch propose 엔드포인트(미저장·미렌더) + compute_verify (스펙 ②)"
```

---

## Task 4: editorAgent — 선택 시 data-eid 스탬프 + SELECTED 확장

**Files:**
- Modify: `web/src/components/deck/editorAgent.ts` (AGENT_BODY 문자열 내부)

> ⚠️ AGENT_BODY는 iframe에 주입되는 **ES5 문자열**. 백틱·`${` 금지, `var`/`function` 유지. node 유닛 테스트 불가 → Task 9 라이브 E2E로 검증.

- [ ] **Step 1: eid 스탬프 헬퍼 추가** — `styleSnapshot`(line 68-74) **뒤에** 삽입

```javascript
  // 선택 요소에 불투명 난수 data-eid 스탬프(1회, 위치·서수 무관). data-pi-*가 아니라 serialize 생존.
  // setAttribute는 'input' 이벤트를 안 내므로 dirty·undo에 영향 없음(메타 부여이지 콘텐츠 편집 아님).
  function ensureEid(el) {
    if (!el.getAttribute('data-eid')) {
      el.setAttribute('data-eid', 'e' + Math.random().toString(36).slice(2, 10));
    }
    return el.getAttribute('data-eid');
  }
```

- [ ] **Step 2: `emitSelected`(line 185-200)에 eid·cardIndex·quotedText 추가** — `emitSelected` 함수를 교체

```javascript
  function emitSelected() {
    var p = primary(); if (!p) return;
    var n = selection.length;
    var rect = (n > 1) ? groupNatRect() : natRectOf(p);
    var single = (n === 1);
    post('SELECTED', {
      tag: n > 1 ? ('(다중 ' + n + ')') : p.tagName.toLowerCase(),
      count: n,
      editable: single && isTextLeaf(p),
      absolute: isAbsolute(p),
      styles: styleSnapshot(p),
      text: single ? (p.textContent || '').slice(0, 80) : '',
      eid: single ? ensureEid(p) : '',
      cardIndex: single ? cardIndexOf(p) : -1,
      quotedText: single ? (p.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 2000) : '',
      rect: rect,
      mixed: n > 1 && !sameSize(),
      canDistribute: n >= 3
    });
  }
```

> 주의: `cardIndexOf`는 이미 정의돼 있음(line 577). `\\s` 는 문자열 리터럴 안이므로 이스케이프(`\\s` → 주입 후 `\s`).

- [ ] **Step 3: 라이브 스모크(수동, iframe 로직 확인)** — 프론트 dev 서버에서 편집 모드 진입 → 텍스트 선택 → 브라우저 콘솔에서 부모가 받은 `SELECTED` 메시지에 `eid`(비어있지 않은 `e…`), `cardIndex`(≥0), `quotedText`(요소 전체 텍스트)가 실리는지 확인. (정식 E2E는 Task 9. 여기선 필드 존재만.)

검증 방법: `web/src/components/deck/DeckEditor.tsx`의 `onMsg` `SELECTED` 케이스에 임시 `console.log(d)`를 넣거나, Task 5 이후 React DevTools로 `selected` state 확인. 스탬프가 dirty를 켜지 않는지도 확인(선택만으로 "저장" 버튼 활성화 금지).

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/deck/editorAgent.ts
git commit -m "[WEB] editorAgent 선택 시 data-eid 스탬프 + SELECTED에 eid/cardIndex/quotedText (스펙 ②)"
```

---

## Task 5: SelectedInfo 타입 확장 + propose 클라이언트

**Files:**
- Modify: `web/src/components/deck/DeckEditor.tsx:14-24`
- Modify: `web/src/lib/api.ts` (nlPatchDeck line 63-65 부근)

- [ ] **Step 1: `DeckEditor.tsx` `SelectedInfo` 확장** — interface(line 14-24)를 교체

```typescript
export interface SelectedInfo {
  tag: string
  editable: boolean
  absolute: boolean
  styles: { color: string; fontSize: string; textAlign: string; fontWeight: string; background: string }
  text: string
  eid?: string                // 선택 요소 앵커(단일 선택 시). 다중=''
  cardIndex?: number          // 선택 요소가 속한 카드 index(단일). 다중=-1
  quotedText?: string         // 요소 전체 텍스트(AI 앵커용, ≤2000자)
  count?: number              // 선택 요소 수(다중선택). 미존재/1=단일
  rect?: ElementRect | null   // 자연 카드좌표(단일=요소, 다중=집합 바운딩박스)
  mixed?: boolean             // 다중선택에서 W/H 혼합 여부
  canDistribute?: boolean     // count>=3
}
```

> SELECTED 페이로드는 `onSelected?.(d as unknown as SelectedInfo)`(DeckEditor.tsx line 110)로 그대로 흐르므로 핸들 메서드 변경 불필요 — 추가 필드는 자동 통과.

- [ ] **Step 2: `api.ts`에 `nlProposeDeck` 추가** — `nlPatchDeck`(line 63-65) **뒤에**

```typescript
export interface NLTarget { eid?: string; cardIndex?: number; quotedText?: string }

// AI 편집 제안 (미커밋, 유료 LLM 1콜). html=캔버스 라이브 serialize 결과. 응답 {html, verify}.
export const nlProposeDeck = (
  jobId: string, instruction: string, html: string, target?: NLTarget,
) => api.post(`/deck/${jobId}/nlpatch/propose`, { instruction, html, target }, { timeout: 180_000 })
```

- [ ] **Step 3: 타입체크 통과 확인**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음 (신규 필드·함수 정합)

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/deck/DeckEditor.tsx web/src/lib/api.ts
git commit -m "[WEB] SelectedInfo eid/cardIndex/quotedText + nlProposeDeck 클라이언트 (스펙 ②)"
```

---

## Task 6: deckDiff — before/after 텍스트 추출 (순수 모듈, 유닛 테스트)

**Files:**
- Create: `web/src/lib/deckDiff.ts`
- Test: `web/src/lib/deckDiff.test.ts`

before/after 미리보기는 백엔드에 HTML 파서가 없어(fidelity=regex only) **프론트에서 target 요소의 텍스트를 추출**한다(스펙 §4.2·§9). before는 선택 시 캡처한 `quotedText`(무료), after는 propose 응답 html에서 같은 `data-eid` 요소 텍스트를 추출한다. 브라우저 DOM 비의존(node 테스트 가능).

- [ ] **Step 1: 실패 테스트 작성** — `web/src/lib/deckDiff.test.ts`

```typescript
import { describe, it, expect } from 'vitest'
import { extractEidText } from './deckDiff'

describe('extractEidText', () => {
  it('data-eid 요소의 텍스트를 태그 제거해 추출', () => {
    const html = '<div data-screen-label="01"><h1 data-eid="e1">제목 <b>강조</b></h1></div>'
    expect(extractEidText(html, 'e1')).toBe('제목 강조')
  })

  it('중첩된 동일 태그를 depth로 올바르게 닫음', () => {
    const html = '<section data-eid="ex"><div>안<div>쪽</div></div></section>'
    expect(extractEidText(html, 'ex')).toBe('안 쪽')
  })

  it('없는 eid는 null', () => {
    expect(extractEidText('<p data-eid="a">x</p>', 'nope')).toBeNull()
  })

  it('void 요소(img)는 빈 문자열', () => {
    expect(extractEidText('<img data-eid="im" src="x">', 'im')).toBe('')
  })

  it('정규식 특수문자가 든 eid도 안전', () => {
    expect(extractEidText('<p data-eid="a.b">x</p>', 'a.b')).toBe('x')
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd web && npx vitest run src/lib/deckDiff.test.ts`
Expected: FAIL — `Failed to resolve import './deckDiff'`

- [ ] **Step 3: `deckDiff.ts` 구현**

```typescript
// target 요소(data-eid)의 텍스트를 HTML 문자열에서 추출 — before/after 프리뷰용.
// 백엔드에 HTML 파서가 없고(fidelity=regex only), 브라우저 DOM에도 의존하지 않는다(node 유닛 테스트 가능).
// 최선노력 추출: 여는 태그 탐색 → 동일 태그명 depth 스캔으로 닫는 태그 찾기 → 내부 태그 제거·공백 정규화.

const VOID_TAGS = new Set([
  'img', 'br', 'hr', 'input', 'source', 'area', 'base', 'col', 'embed', 'link', 'meta', 'param', 'track', 'wbr',
])

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function extractEidText(html: string, eid: string): string | null {
  const open = new RegExp(`<([a-zA-Z][\\w-]*)\\b[^>]*\\bdata-eid="${escapeRe(eid)}"[^>]*>`, 'i')
  const m = open.exec(html)
  if (!m) return null
  const tag = m[1].toLowerCase()
  if (VOID_TAGS.has(tag)) return ''
  const bodyStart = m.index + m[0].length

  const scan = new RegExp(`<(/?)${escapeRe(tag)}\\b[^>]*>`, 'gi')
  scan.lastIndex = bodyStart
  let depth = 1
  let end = html.length
  let mm: RegExpExecArray | null
  while ((mm = scan.exec(html)) !== null) {
    if (mm[1] === '/') {
      if (--depth === 0) { end = mm.index; break }
    } else {
      depth++
    }
  }
  return html.slice(bodyStart, end).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd web && npx vitest run src/lib/deckDiff.test.ts`
Expected: PASS (5개)

- [ ] **Step 5: 커밋**

```bash
git add web/src/lib/deckDiff.ts web/src/lib/deckDiff.test.ts
git commit -m "[WEB] deckDiff.extractEidText — before/after 텍스트 추출(순수·테스트) (스펙 ②)"
```

---

## Task 7: DeckAIAssistant 컴포넌트 (제안·미리보기·적용/다른안/취소·되돌리기)

**Files:**
- Create: `web/src/components/deck/DeckAIAssistant.tsx`

프레젠테이션 + 지시 입력/원클릭. 상태(pending·busy·스냅샷)는 부모(page.tsx)가 소유하고 콜백으로 내려받는다. node 컴포넌트 테스트 인프라 없음 → Task 9 라이브 E2E로 검증.

- [ ] **Step 1: `DeckAIAssistant.tsx` 구현**

```tsx
'use client'

// AI 도우미 (스펙 §4.2) — 연구원용 주 편집 수단. 요소 선택 → 원클릭/자연어 → AI 제안(미커밋) →
// before/after 확인 → [✓ 적용]/[↻ 다른 안]/[✕]. 적용 후에만 저장·렌더. AI 되돌리기=부모 스냅샷.
// 제안(propose)·적용(commit)은 각각 유료 LLM/렌더이므로 명시적 클릭만(타이핑 자동호출 금지).

import { useState } from 'react'
import type { SelectedInfo } from './DeckEditor'

const TEXT_PRESETS = [
  { label: '한 줄로 짧게', instruction: '이 텍스트를 의미를 유지하며 한 줄로 짧게 줄여줘.' },
  { label: '더 쉬운 말로', instruction: '이 텍스트를 일반 독자가 이해하기 쉬운 말로 바꿔줘. 수치는 원문 근거 안에서만.' },
  { label: '더 크게', instruction: '이 텍스트 요소의 글자 크기를 눈에 띄게 키워줘(비율 유지).' },
]

interface Props {
  selected: SelectedInfo | null
  proposing: boolean          // propose 진행 중(유료)
  pending: boolean            // 미커밋 제안 대기 중
  committing: boolean         // 적용(저장+렌더) 진행 중
  beforeText: string | null
  afterText: string | null
  onPropose: (instruction: string) => void
  onCommit: () => void
  onDiscard: () => void
  canRevert: boolean
  reverting: boolean
  onRevert: () => void
}

export default function DeckAIAssistant({
  selected, proposing, pending, committing, beforeText, afterText,
  onPropose, onCommit, onDiscard, canRevert, reverting, onRevert,
}: Props) {
  const [text, setText] = useState('')
  const [last, setLast] = useState('')

  const busy = proposing || committing || reverting
  const hasTarget = !!selected?.eid

  const propose = (instruction: string) => {
    const t = instruction.trim()
    if (!t || busy) return
    setLast(t)
    onPropose(t)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-bold text-ink">✦ AI 도우미</span>
        {canRevert && (
          <button
            onClick={onRevert}
            disabled={busy}
            className="ml-auto text-[11px] font-semibold text-ink-2 border border-border rounded-md px-2 py-1 disabled:opacity-40"
          >
            {reverting ? '되돌리는 중…' : '↩ AI 편집 되돌리기'}
          </button>
        )}
      </div>

      {/* 맥락 */}
      <p className="text-[11.5px] text-ink-3 leading-snug">
        {hasTarget
          ? <>선택한 <b className="text-ink-2">{selected?.tag}</b> 요소를 고쳐요: “{(selected?.quotedText || '').slice(0, 40)}{(selected?.quotedText || '').length > 40 ? '…' : ''}”</>
          : '요소를 클릭해 고르면 그 부분만 정확히 고쳐요. 안 고르면 덱 전체에 적용됩니다.'}
      </p>

      {/* 미커밋 제안 미리보기 */}
      {pending ? (
        <div className="rounded-lg border border-forest-green/40 bg-forest-green-wash/40 p-3 flex flex-col gap-2">
          <span className="text-[11px] font-bold text-forest-green-deep">AI 제안 (아직 적용 안 됨)</span>
          {hasTarget && (beforeText !== null || afterText !== null) && (
            <div className="flex flex-col gap-1 text-[11.5px]">
              <span className="text-ink-3 line-through">{beforeText || '(빈 텍스트)'}</span>
              <span className="text-ink font-semibold">→ {afterText || '(빈 텍스트)'}</span>
            </div>
          )}
          {!hasTarget && <span className="text-[11px] text-ink-3">덱 전체에 반영됩니다. 적용하면 카드가 다시 그려져요.</span>}
          <div className="flex gap-2 mt-1">
            <button
              onClick={onCommit}
              disabled={committing}
              className="flex-1 h-8 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40"
            >
              {committing ? '적용 중…' : '✓ 적용'}
            </button>
            <button
              onClick={() => propose(last)}
              disabled={busy || !last}
              title="같은 지시로 다른 제안"
              className="h-8 px-3 rounded-lg border border-border text-ink-2 text-[12px] font-semibold disabled:opacity-40"
            >
              {proposing ? '…' : '↻ 다른 안'}
            </button>
            <button
              onClick={onDiscard}
              disabled={committing}
              className="h-8 px-3 rounded-lg border border-border text-ink-3 text-[12px] disabled:opacity-40"
            >✕</button>
          </div>
        </div>
      ) : (
        <>
          {/* 원클릭 프리셋(텍스트 선택 시) */}
          {selected?.editable && (
            <div className="flex flex-wrap gap-1.5">
              {TEXT_PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => propose(p.instruction)}
                  disabled={busy}
                  className="text-[11.5px] font-semibold text-forest-green-deep bg-forest-green-wash border border-forest-green/30 rounded-full px-2.5 py-1 disabled:opacity-40"
                >{p.label}</button>
              ))}
            </div>
          )}

          {/* 자유 지시 */}
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={hasTarget ? '예: "이 문장을 질문형으로 바꿔줘"' : '예: "표지 색을 더 차분하게"'}
            rows={2}
            disabled={busy}
            className="w-full rounded-lg border border-border bg-canvas-subtle p-2 text-[12px] text-ink-1 resize-none disabled:opacity-50"
          />
          <button
            onClick={() => { propose(text); setText('') }}
            disabled={busy || !text.trim()}
            className="h-8 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40"
          >
            {proposing ? 'AI가 제안 중…' : 'AI에게 맡기기'}
          </button>
          <p className="text-[10px] text-ink-3 leading-snug">
            AI가 먼저 제안을 보여줘요. 확인하고 <b>적용</b>을 눌러야 반영됩니다. 수치는 원문 근거 안에서만 바뀝니다.
          </p>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 타입체크 통과 확인**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음 (아직 page.tsx 미배선이므로 컴포넌트 단독 타입만 검증)

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/deck/DeckAIAssistant.tsx
git commit -m "[WEB] DeckAIAssistant — propose/commit 2단 UI + before/after + 되돌리기 (스펙 ②)"
```

---

## Task 8: page.tsx 배선 — propose/commit/스냅샷 되돌리기 오케스트레이션

**Files:**
- Modify: `web/src/app/deck/[jobId]/page.tsx:13-17, 111-121, 183-196, 359`

기존 `DeckNLBar`(즉시저장 handleNL)를 `DeckAIAssistant`(propose→commit)로 교체하고, 부모가 pending·스냅샷 상태를 소유한다. ①(탭 셸)은 아직 없으므로 **현 우측 사이드바 위치**에 배선한다.

- [ ] **Step 1: import 교체** — line 13-17

```typescript
import { getStatus, getDeck, patchDeck, nlProposeDeck, exportDeck, getDeckCardUrl, getExportDownloadUrl } from '@/lib/api'
import DeckEditor, { type DeckEditorHandle, type SelectedInfo, type HistoryState, type PageState } from '@/components/deck/DeckEditor'
import DeckElementPanel from '@/components/deck/DeckElementPanel'
import DeckMediaPanel from '@/components/deck/DeckMediaPanel'
import DeckAIAssistant from '@/components/deck/DeckAIAssistant'
import { extractEidText } from '@/lib/deckDiff'
```

> `nlPatchDeck` → `nlProposeDeck`로 교체(기존 즉시저장 클라이언트는 이 페이지에서 미사용). `DeckNLBar` import 제거.

- [ ] **Step 2: AI 상태 추가** — 기존 `nlBusy` state(line 118)를 다음으로 교체

```typescript
  const [proposing, setProposing] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [reverting, setReverting] = useState(false)
  const [pending, setPending] = useState<{ html: string; verify: VerifyData; afterText: string | null } | null>(null)
  const [snapshots, setSnapshots] = useState<string[]>([])
```

- [ ] **Step 3: handleNL(line 183-196)을 propose/commit/discard/revert 4핸들러로 교체**

```typescript
  const handlePropose = useCallback(async (instruction: string) => {
    if (!editorRef.current) return
    setProposing(true)
    try {
      const html = await editorRef.current.getHtml()   // 라이브 serialize(미저장 편집+eid 포함)
      const target = selected?.eid
        ? { eid: selected.eid, cardIndex: selected.cardIndex, quotedText: selected.quotedText }
        : undefined
      const r = await nlProposeDeck(jobId, instruction, html, target)
      const afterText = selected?.eid ? extractEidText(r.data.html, selected.eid) : null
      setPending({ html: r.data.html, verify: r.data.verify, afterText })
    } finally { setProposing(false) }
  }, [jobId, selected])

  const handleCommit = useCallback(async () => {
    if (!pending) return
    setCommitting(true)
    try {
      const snapshot = deck?.html
      const r = await patchDeck(jobId, pending.html)
      setDeck((prev) => prev ? {
        ...prev, html: pending.html, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      if (snapshot) setSnapshots((s) => [...s, snapshot])   // commit 직전 html 스냅샷
      setEditWarnings(r.data.warnings ?? [])
      setVer((x) => x + 1)
      setPending(null)
      setDirty(false)
    } finally { setCommitting(false) }
  }, [jobId, pending, deck])

  const handleDiscard = useCallback(() => setPending(null), [])

  const handleRevert = useCallback(async () => {
    const snapshot = snapshots[snapshots.length - 1]
    if (!snapshot) return
    setReverting(true)
    try {
      const r = await patchDeck(jobId, snapshot)
      setDeck((prev) => prev ? {
        ...prev, html: snapshot, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      setSnapshots((s) => s.slice(0, -1))
      setEditWarnings(r.data.warnings ?? [])
      setVer((x) => x + 1)
      setPending(null)
    } finally { setReverting(false) }
  }, [jobId, snapshots])
```

> ⚠️ `handleCommit`/`handleRevert`는 `deck.html`을 바꿔 iframe을 재마운트한다(editorAgent undo 스택 소실). 이것이 스냅샷 되돌리기를 별도로 두는 이유(스펙 §4.2). 상단바 undo/redo는 직접조작용(iframe), AI 되돌리기는 스냅샷용 — 별개.

- [ ] **Step 4: `toggleMode`에서 pending·스냅샷 정리** — `toggleMode`(line 198-202)를 교체

```typescript
  const toggleMode = useCallback(() => {
    setSelected(null)
    setEditWarnings([])
    setPending(null)
    setMode((m) => (m === 'edit' ? 'view' : 'edit'))
  }, [])
```

> 스냅샷 스택은 편집 세션 동안 유지(모드 전환에도 보존) — 뷰↔편집을 오가도 AI 되돌리기 이력이 살아있게. 다만 pending(미커밋)은 모드 전환 시 폐기.

- [ ] **Step 5: 우측 사이드바의 `DeckNLBar` 사용부(line 358-360)를 교체**

기존:
```tsx
            <div className="h-px bg-border my-6" />
            <DeckNLBar onSend={handleNL} busy={nlBusy} />
            <div className="h-px bg-border mt-6" />
```

교체:
```tsx
            <div className="h-px bg-border my-6" />
            <DeckAIAssistant
              selected={selected}
              proposing={proposing}
              pending={!!pending}
              committing={committing}
              beforeText={selected?.quotedText ?? null}
              afterText={pending?.afterText ?? null}
              onPropose={handlePropose}
              onCommit={handleCommit}
              onDiscard={handleDiscard}
              canRevert={snapshots.length > 0}
              reverting={reverting}
              onRevert={handleRevert}
            />
            <div className="h-px bg-border mt-6" />
```

- [ ] **Step 6: 타입체크 + 린트**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음. (`handleNL`·`nlBusy`·`DeckNLBar`·`nlPatchDeck` 잔존 참조가 있으면 제거 — 내 변경이 만든 orphan만.)

Run: `cd web && npm run lint`
Expected: 신규 파일 관련 에러 없음

- [ ] **Step 7: 커밋**

```bash
git add web/src/app/deck/[jobId]/page.tsx
git commit -m "[WEB] deck 페이지 AI propose/commit/스냅샷 되돌리기 배선(DeckNLBar→DeckAIAssistant) (스펙 ②)"
```

---

## Task 9: 라이브 E2E 검증 (플러밍 무료 + 실편집 유료-사전허락)

**Files:** (없음 — 실행/검증)

iframe·컴포넌트·페이지 배선은 node 유닛 불가 → 실브라우저로 계약 전체를 증명한다. **2단계**: (a) DEV_MOCK_LLM 플러밍(무료), (b) 실 LLM 편집(유료 — 사용자 사전허락 필수, 메모리 `feedback_ask_before_paid`).

- [ ] **Step 1: 서버 기동 확인**

- 백엔드: `127.0.0.1:8000` (기존 detached). 코드 변경 반영 위해 **uvicorn 재시작**(backend/CLAUDE.md §7 — 코드 변경 시 필수).
- 프론트: `localhost:3000`. deck 화면 WorkerError 이력 → 필요 시 `web/.next` 삭제 후 재컴파일(web/CLAUDE.md Learned Mistakes).

- [ ] **Step 2: (a) 무료 플러밍 E2E — `DEV_MOCK_LLM=true`**

백엔드 env `DEV_MOCK_LLM=true`로 재기동 후 브라우저에서:
1. 로그인 → 완성된 덱 `/deck/{id}` 열기 → **편집** 진입.
2. 카드의 제목 텍스트 **클릭 선택** → 우측 AI 도우미에 선택 맥락(`tag`·따옴표 텍스트)이 뜨는지, 원클릭 프리셋(한 줄로/쉬운 말로/더 크게)이 보이는지.
3. **"한 줄로 짧게"** 클릭 → "AI가 제안 중…" → **미커밋 제안 카드**(초록 테두리) 등장. mock은 마커 주입이라 afterText가 before와 같을 수 있음(플러밍 확인이 목적).
4. **[✕]** → 제안 폐기(pending 사라짐). 다시 프리셋 → **[✓ 적용]** → "적용 중…" → PNG 재렌더(카드 이미지 갱신, ver 증가). 저장 버튼 상태·검증 패널 수치 갱신 확인.
5. **[↩ AI 편집 되돌리기]** 등장 → 클릭 → "되돌리는 중…" → 이전 상태 복원(PNG·검증 원복). 스택 비면 버튼 사라짐.

**통과 기준(무료):** propose가 pending을 만들고 **DB·PNG를 안 바꾼다**(적용 전 새로고침 시 원본 유지) · 적용 시에만 저장/렌더 · 되돌리기가 스냅샷으로 원복 · 선택만으로 "저장"이 활성화되지 않음(eid 스탬프가 dirty 안 켬).

무저장 확인 콕 집기: 3에서 제안 대기 상태로 **브라우저 새로고침** → 원본 그대로(제안 미반영) 확인.

- [ ] **Step 3: (b) 실 LLM 편집 E2E — 유료, 사용자 사전허락 후에만**

> ⛔ 실행 전 사용자에게 비용 발생을 알리고 허락받는다(propose 1콜 + commit 렌더). 허락 없이 실행 금지.

`DEV_MOCK_LLM=false`(Opus 4.8)로 재기동 후:
1. 제목 선택 → "한 줄로 짧게" → **실제로 짧아진 제목**이 before/after에 `원문 line-through → 새 문장`으로 표시(afterText가 실제 변경 반영, `data-eid` 보존 덕에 매칭).
2. [✓ 적용] → 카드 PNG에 반영. 검증 패널이 수치 재대조 결과로 갱신.
3. 수치 왜곡 없음 확인(원문에 없는 숫자 안 생김 — 충실성).

**통과 기준(유료):** target 앵커가 정확히 그 요소만 바꾼다 · `data-eid` 보존으로 afterText 매칭 성공 · before/after가 의미 있는 diff를 보여준다.

- [ ] **Step 4: 회귀 스위트 최종 확인**

```bash
pytest backend/tests/
cd web && npx vitest run && npx tsc --noEmit
```
Expected: 백엔드 전체 PASS · vitest PASS · 타입 클린.

- [ ] **Step 5: 결과 기록(커밋 불요, 보고)**

E2E 결과(무료 통과 여부, 유료 실행 여부·결과)를 사용자에게 보고. 유료 미허락 시 (a)만으로 계약 플러밍 확정하고 (b)는 대기로 남긴다.

---

## Self-Review (스펙 §4.2·§5·§9 커버리지)

| 스펙 요구 | 태스크 |
|---|---|
| propose/commit 2단 (미저장→[적용]에서만 저장·렌더) | 3(propose) · 8(commit=patchDeck) |
| 요소 target eid (불투명 난수·서수 무관) | 4(ensureEid Math.random) |
| SELECTED에 `{eid, cardIndex, quotedText}` | 4 |
| propose 입력 = 라이브 serialize html (미저장편집·eid 보존) | 8(getHtml→propose) |
| target을 프롬프트에 "이 요소만" 앵커 | 2 |
| EDIT_SYSTEM `data-eid` 원형 보존 규칙 | 2 |
| before/after = 프론트 DOM 텍스트 비교(백엔드 파서 없음) | 6(extractEidText) · 8(before=quotedText) |
| 스냅샷 되돌리기(부모 push, patchDeck 재저장, "되돌리는 중…") | 8(snapshots·handleRevert) |
| 상단바 undo/redo(iframe)와 AI 되돌리기(스냅샷) 분리 | 8(Step 3 주석·별도 버튼) |
| propose 엔드포인트 형태 + docs/07 선행 | 1(docs) · 3(route) |
| 1차 제안 세트(한 줄로/쉬운 말로/더 크게) | 7(TEXT_PRESETS) |
| 취소 [✕] = 서버 무변·pending 폐기 | 7·8(handleDiscard) |

**Placeholder scan:** 모든 코드 스텝에 실제 코드 포함 — TODO/TBD 없음. ✅
**타입 일관성:** `nlProposeDeck(jobId, instruction, html, target)` · `NLTarget{eid,cardIndex,quotedText}` · `SelectedInfo.eid/cardIndex/quotedText` · `pending{html,verify,afterText}` · `extractEidText(html, eid)` — 태스크 간 시그니처 정합 확인. ✅
**스코프:** ② 계약 단일 수직 슬라이스(백엔드+iframe+프론트 배관). ①(탭 셸·뷰)·③(인스펙터)·④(자동저장 분리)는 별도 계획. ✅

---

## 실행 방식 선택

계획은 `docs/superpowers/plans/2026-07-08-deck-ai-assistant-contract.md`에 저장됨. 두 실행 옵션:

1. **Subagent-Driven (권장)** — 태스크마다 새 서브에이전트 + 2단 리뷰, 태스크 사이 검토, 빠른 반복.
2. **Inline Execution** — 이 세션에서 executing-plans로 체크포인트 배치 실행.

> 비용 주의: Task 9 Step 3(실 LLM E2E)은 유료 — 사용자 사전허락 후에만.
