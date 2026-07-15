# 팩트 패널 — 수치 클릭 → 카드 점프+하이라이트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 팩트 패널의 '확인 필요' 수치를 클릭하면 그 수치가 쓰인 카드로 이동해 해당 텍스트에 마커를 씌운다. 내부 용어(FIDELITY·해자, CLAIM LEDGER)를 사용자 언어로 바꾼다.

**Architecture:** 백엔드 `verify_deck()`을 카드 단위(`data-screen-label`)로 분할해 각 claim에 `card` 인덱스를 붙인다(이미 `derived_claims()`가 쓰는 분할을 재사용). 프론트는 원장 행을 버튼으로 만들고, 클릭 시 편집 모드로 그 카드에 진입한 뒤 editorAgent의 새 `HIGHLIGHT` 명령으로 텍스트 위에 **오버레이 마커**를 그린다(DOM 삽입 금지 — 자동저장 오염 방지).

**Tech Stack:** Python/pytest (backend), React 19 + TypeScript + vitest (web), iframe postMessage editorAgent

**스펙:** `docs/superpowers/specs/2026-07-14-fact-panel-jump-to-claim-design.md`

---

## 파일 구조

| 파일 | 역할 | 변경 |
|---|---|---|
| `backend/core/fidelity.py` | 수치 추출·검증 | `NumberClaim.card` 추가, `verify_deck` 카드 분할, `derived_claims`에 `card` 기록 |
| `backend/agents/deck/pipeline.py:37-53` | verify payload 조립 | claims dict에 `card` 포함 |
| `backend/tests/test_fidelity_card_index.py` | 신규 테스트 | 카드 인덱스 부여 검증 |
| `web/src/lib/verifyStatus.ts` | verify 타입·판독 | `card?: number \| null` 추가, `reviewQueue()` 추가 |
| `web/src/lib/verifyStatus.test.ts` | 기존 테스트 | `reviewQueue` 케이스 추가 |
| `web/src/components/deck/editorAgent.ts` | iframe 에이전트 | `HIGHLIGHT`/`CLEAR_HIGHLIGHT` 명령 + 마커 오버레이 풀 |
| `web/src/components/deck/DeckEditor.tsx` | 에이전트 래퍼 | `highlight(value)` / `clearHighlight()` 핸들 |
| `web/src/components/deck/DeckFactPanel.tsx` | 팩트 패널 | 행=버튼(onJump), 문구 교체 |
| `web/src/components/deck/DeckFactJumpBar.tsx` | 신규 | 편집 캔버스 상단 문맥 바(다음 항목/닫기) |
| `web/src/app/deck/[jobId]/page.tsx` | 배선 | onJump → enterEditAt + highlight, 문맥 바 상태 |

---

## Task 1: 백엔드 — claim에 카드 인덱스 부여

**Files:**
- Modify: `backend/core/fidelity.py:26-30` (NumberClaim), `93-109` (verify_deck), `202-227` (derived_claims)
- Test: `backend/tests/test_fidelity_card_index.py` (신규)

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_fidelity_card_index.py`:

```python
# -*- coding: utf-8 -*-
"""claim에 카드 위치(card 인덱스)가 붙는가 — 팩트 패널 '클릭→그 카드로 점프'의 전제."""
from backend.core.fidelity import derived_claims, verify_deck

DECK = """
<div data-screen-label="01" style="width:1080px">
  <h1>표면 전위는 49.3 mV 였다</h1>
</div>
<div data-screen-label="02" style="width:1080px">
  <p>인장강도가 142에서 238 MPa로, 약 1.7배 늘었다</p>
</div>
"""
PAPER = "surface potential 49.3 mV ... tensile strength 142 to 238 MPa (1.7-fold)"


def test_claim_carries_card_index():
    claims = verify_deck(DECK, PAPER)
    by_value = {c.value: c.card for c in claims}
    assert by_value["49.3 mV"] == 0
    assert by_value["238 MPa"] == 1


def test_duplicate_value_keeps_first_card_and_no_extra_claims():
    # 같은 수치가 두 카드에 나와도 claim은 한 번만(전역 dedup 유지) — 원장 카운트 회귀 방지
    deck = DECK + '<div data-screen-label="03"><p>다시 49.3 mV</p></div>'
    claims = verify_deck(deck, PAPER)
    hits = [c for c in claims if c.value == "49.3 mV"]
    assert len(hits) == 1
    assert hits[0].card == 0          # 첫 등장 카드


def test_derived_claim_carries_card_index():
    derived = derived_claims(DECK, PAPER)
    fold = [d for d in derived if d["kind"] == "fold"]
    assert fold and fold[0]["card"] == 1


def test_html_without_card_markers_yields_card_none():
    # 카드 분할 마커가 없는 HTML(구 저작물/조각) — 죽지 않고 card=None
    claims = verify_deck("<p>49.3 mV</p>", PAPER)
    assert claims and claims[0].card is None
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_fidelity_card_index.py -v`
Expected: FAIL — `AttributeError: 'NumberClaim' object has no attribute 'card'`

- [ ] **Step 3: 구현**

`backend/core/fidelity.py` — `NumberClaim`에 필드 추가:

```python
@dataclass
class NumberClaim:
    value: str          # 카드에 쓰인 정량 수치 토큰 (예: "28.4", "19.36 ± 0.96 %", "+49.3 mV")
    context: str        # 그 수치 주변 콘텐츠 한 토막 (사용자 판단용, 단어 경계로 정리)
    verified: bool      # 원문에 존재?
    card: int | None = None   # 이 수치가 처음 등장한 카드 인덱스(0-기반). 분할 마커 없으면 None
```

`verify_deck`을 카드 단위 루프로 교체 (기존 함수 본문 전체 대체):

```python
def verify_deck(html: str, paper_text: str) -> list[NumberClaim]:
    """덱 HTML의 정량 수치를 원문과 대조해 NumberClaim 리스트 반환.

    카드(data-screen-label) 단위로 순회해 각 claim에 첫 등장 카드 인덱스를 붙인다 —
    팩트 패널이 '이 수치가 쓰인 카드'로 사용자를 데려갈 수 있게 하는 좌표다.
    dedup은 덱 전역(seen)으로 유지한다 — 원장 카운트를 바꾸지 않는다(위치만 덧붙이는 작업).
    """
    paper_flat = _flat(paper_text)
    seen: set[str] = set()
    claims: list[NumberClaim] = []

    for card_idx, content in _card_contents(html):
        for m in _NUM.finditer(content):
            tok = m.group().strip()
            if not _is_meaningful(tok) or tok in seen:
                continue
            seen.add(tok)
            # 주 수치 코어(첫 숫자 런, 콤마 제거)로 원문 대조 — 단위 표기 차이에 견고
            cm = _CORE.search(tok)
            core = cm.group().replace(",", "") if cm else ""
            verified = bool(core) and (core in paper_text or core in paper_flat)
            claims.append(NumberClaim(
                value=tok,
                context=_clean_context(content, m.start(), m.end()),
                verified=verified,
                card=card_idx,
            ))
    return claims
```

`_card_contents` 헬퍼를 `_content_text` 아래에 추가 (V1·V2가 함께 쓰는 유일한 분할 지점):

```python
def _card_contents(html: str) -> list[tuple[int | None, str]]:
    """덱 HTML → [(카드 인덱스, 그 카드의 콘텐츠 텍스트)].

    분할 마커(data-screen-label)가 없으면 [(None, 전체 텍스트)] — 구 저작물/조각에서도 죽지 않는다.
    """
    chunks = [c for c in _CARD_SPLIT.split(html) if "data-screen-label" in c]
    if not chunks:
        return [(None, _content_text(html))]
    return [(i, _content_text(c)) for i, c in enumerate(chunks)]
```

`_CARD_SPLIT`은 파일 아래쪽(112행 근처)에 정의돼 있다 — **`_content_text` 위쪽(모듈 상단 정규식 블록, `_CORE` 정의 다음 줄)으로 옮겨** `_card_contents`가 참조할 수 있게 한다. 정의만 이동하고 패턴은 그대로다:

```python
_CARD_SPLIT = re.compile(r'(?=<div[^>]+data-screen-label=)', re.I)
```

`derived_claims`를 `_card_contents`를 쓰도록 교체 (기존 루프 헤더만 바뀐다):

```python
def derived_claims(html: str, paper_text: str) -> list[dict]:
    """카드별 파생수치(N% 증가·N배)를 같은 카드 수치쌍과 검산.

    반환: [{value, kind, suspect, unresolved, verified, context, card}]
    suspect=True → 사용자에게 '계산 불일치' 표면화(막지 않음, 헌법 3조).
    """
    results: list[dict] = []
    for card_idx, content in _card_contents(html):
        if card_idx is None:
            continue                       # 카드 경계가 없으면 '같은 카드 수치쌍' 검산이 성립 안 함
        nums = _card_numbers(content)
        for pat, kind in ((_PCT_CHANGE, "pct_change"), (_FOLD, "fold"), (_PCT_POINT, "pct_point")):
            for m in pat.finditer(content):
                claimed = float(m.group(1).replace(",", ""))
                suspect, unresolved = _check_pairs(nums, claimed, kind)
                core = m.group(1).replace(",", "")
                results.append({
                    "value": m.group().strip(),
                    "kind": kind,
                    "suspect": suspect,
                    "unresolved": unresolved,
                    "verified": core in _flat(paper_text),
                    "context": _clean_context(content, m.start(), m.end()),
                    "card": card_idx,
                })
    return results
```

- [ ] **Step 4: 테스트 통과 확인 + 회귀 확인**

Run: `pytest backend/tests/test_fidelity_card_index.py backend/tests/test_fidelity_derived.py -v`
Expected: 전부 PASS. `test_fidelity_derived.py`가 깨지면 dedup/카운트가 변한 것 — 되돌아가 원인을 잡는다.

Run: `pytest backend/tests/ -q`
Expected: 기존 전체 스위트 그대로 green.

- [ ] **Step 5: 커밋**

```bash
git add backend/core/fidelity.py backend/tests/test_fidelity_card_index.py
git commit -m "[BE] fidelity: claim에 카드 인덱스 부여 — 팩트 패널이 수치의 위치를 알게 한다"
```

---

## Task 2: 백엔드 — verify payload에 card 실어보내기

**Files:**
- Modify: `backend/agents/deck/pipeline.py:37-53`
- Test: `backend/tests/test_fidelity_card_index.py` (Task 1 파일에 추가)

- [ ] **Step 1: 실패하는 테스트 추가**

`backend/tests/test_fidelity_card_index.py` 하단에 추가:

```python
def test_compute_verify_payload_includes_card():
    from backend.agents.deck.pipeline import compute_verify
    payload = compute_verify(DECK, PAPER)
    cards = {c["value"]: c["card"] for c in payload["claims"]}
    assert cards["49.3 mV"] == 0
    assert cards["238 MPa"] == 1
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_fidelity_card_index.py::test_compute_verify_payload_includes_card -v`
Expected: FAIL — `KeyError: 'card'`

- [ ] **Step 3: 구현**

`backend/agents/deck/pipeline.py`의 `_verify_to_json` 안 claims 직렬화 한 줄을 교체:

```python
        "claims": [
            {"value": c.value, "context": c.context, "verified": c.verified, "card": c.card}
            for c in claims
        ],
```

- [ ] **Step 4: 통과 확인**

Run: `pytest backend/tests/test_fidelity_card_index.py -v && pytest backend/tests/ -q`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/agents/deck/pipeline.py backend/tests/test_fidelity_card_index.py
git commit -m "[BE] verify payload에 card 인덱스 포함"
```

---

## Task 3: 프론트 타입 + 확인필요 큐

**Files:**
- Modify: `web/src/lib/verifyStatus.ts`
- Test: `web/src/lib/verifyStatus.test.ts`

`reviewQueue()`는 패널과 문맥 바가 **같은 순서**를 보게 하는 단일 진실이다(둘이 각자 정렬하면 '다음 항목'이 엉킨다).

- [ ] **Step 1: 실패하는 테스트 추가**

`web/src/lib/verifyStatus.test.ts` 하단에 추가:

```typescript
import { reviewQueue } from './verifyStatus'

describe('reviewQueue', () => {
  const verify = {
    verified: 1,
    unverified: 1,
    claims: [
      { value: '49.3 mV', context: 'a', verified: true, card: 0 },
      { value: '999 nm', context: 'b', verified: false, card: 2 },
    ],
    derived: [
      { value: '170% 증가', kind: 'pct_change', suspect: true, unresolved: false, verified: true, context: 'c', card: 1 },
      { value: '2배', kind: 'fold', suspect: false, unresolved: false, verified: true, context: 'd', card: 1 },
    ],
  }

  it('산수 불일치를 먼저, 그 다음 원문 미확인을 담는다', () => {
    const q = reviewQueue(verify)
    expect(q.map((i) => i.value)).toEqual(['170% 증가', '999 nm'])
    expect(q.map((i) => i.card)).toEqual([1, 2])
    expect(q[0].reason).toBe('mismatch')
    expect(q[1].reason).toBe('missing')
  })

  it('검증된 수치와 정합한 파생수치는 담지 않는다', () => {
    expect(reviewQueue(verify).some((i) => i.value === '2배')).toBe(false)
  })

  it('verify가 없으면 빈 큐', () => {
    expect(reviewQueue(null)).toEqual([])
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npx vitest run src/lib/verifyStatus.test.ts`
Expected: FAIL — `reviewQueue is not a function`

- [ ] **Step 3: 구현**

`web/src/lib/verifyStatus.ts` — 타입에 `card` 추가하고 `reviewQueue` 신설:

```typescript
export interface DerivedClaim {
  value: string
  kind: string
  suspect: boolean
  unresolved: boolean
  verified: boolean
  context: string
  card?: number | null   // 구 덱엔 없음 — 없으면 점프 불가(클릭 비활성)
}

export interface VerifyClaim {
  value: string
  context: string
  verified: boolean
  card?: number | null   // 구 덱엔 없음
}

/** 사용자가 훑어야 할 항목(확인 필요) — 패널·문맥 바가 공유하는 단일 순서. */
export interface ReviewItem {
  value: string
  context: string
  card: number | null
  reason: 'mismatch' | 'missing'   // 계산이 안 맞음 / 원문에 없음
}

export function reviewQueue(verify: VerifyData | null | undefined): ReviewItem[] {
  const mismatch: ReviewItem[] = suspectClaims(verify).map((d) => ({
    value: d.value, context: d.context, card: d.card ?? null, reason: 'mismatch' as const,
  }))
  const missing: ReviewItem[] = (verify?.claims ?? [])
    .filter((c) => !c.verified)
    .map((c) => ({ value: c.value, context: c.context, card: c.card ?? null, reason: 'missing' as const }))
  return [...mismatch, ...missing]
}
```

(`VerifyData`·`suspectClaims`·`isAllClear`는 그대로 둔다.)

- [ ] **Step 4: 통과 확인**

Run: `cd web && npx vitest run src/lib/verifyStatus.test.ts`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add web/src/lib/verifyStatus.ts web/src/lib/verifyStatus.test.ts
git commit -m "[FE] verify 타입에 card 추가 + reviewQueue(확인필요 단일 순서)"
```

---

## Task 4: editorAgent — HIGHLIGHT 마커 (DOM 삽입 없음)

**Files:**
- Modify: `web/src/components/deck/editorAgent.ts` (전역 변수 19행 근처, 오버레이 블록 104-122행, `positionOverlay` 145행, `setPage` 737행, 메시지 스위치 763행)

**왜 오버레이인가:** `<mark>`를 넣으면 DOM이 바뀌어 문서가 dirty가 되고, 자동저장이 마커를 원본 HTML에 저장한다. 오버레이 div는 `data-pi-artifact`라 `serialize()`가 제거하고, `DIRTY`는 `onInput`에서만 발신되므로 저장 경로를 건드리지 않는다.

- [ ] **Step 1: 마커 풀 전역 변수 추가**

`editorAgent.ts` 19행 `var overlayPool = [];` 다음 줄에:

```javascript
  var markPool = [];       // 팩트 점프 하이라이트(수치 위 마커) — 선택 오버레이와 별도 풀
  var markRects = [];      // 현재 마킹된 사각형(스크롤·리사이즈 시 재배치용)
```

- [ ] **Step 2: 마커 엘리먼트 팩토리 + 텍스트 탐색 + HIGHLIGHT 구현**

`editorAgent.ts`의 `placeBox` 함수(122행) 다음에 추가:

```javascript
  // ── 팩트 점프 하이라이트 ────────────────────────────────────────────────────
  // DOM에 <mark>를 넣지 않는다 — 삽입하면 문서가 dirty가 되어 자동저장이 원본을 오염시킨다.
  // Range 좌표만 읽어 오버레이 박스를 띄운다(data-pi-artifact → serialize에서 제거됨).
  function makeMarkEl() {
    var d = document.createElement('div');
    d.setAttribute('data-pi-mark', '1'); d.setAttribute('data-pi-artifact', '1');
    d.style.cssText = 'position:absolute;pointer-events:none;z-index:2147483644;border-radius:3px;'
      + 'background:rgba(250,204,21,.38);box-shadow:0 0 0 2px rgba(202,138,4,.55);display:none;';
    document.body.appendChild(d);
    return d;
  }

  function clearHighlight() {
    markRects = [];
    for (var i = 0; i < markPool.length; i++) markPool[i].style.display = 'none';
  }

  // 현재 카드 안에서 needle이 나오는 모든 위치의 사각형을 모은다.
  function findRects(needle) {
    var cs = cardEls();
    var card = cs[activeCard];
    if (!card || !needle) return [];
    var rects = [];
    var walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      var text = node.nodeValue || '';
      var from = 0;
      while (true) {
        var at = text.indexOf(needle, from);
        if (at < 0) break;
        var r = document.createRange();
        r.setStart(node, at); r.setEnd(node, at + needle.length);
        var list = r.getClientRects();
        for (var i = 0; i < list.length; i++) {
          var b = list[i];
          if (b.width > 0 && b.height > 0) {
            rects.push({ x: b.left + window.scrollX, y: b.top + window.scrollY, w: b.width, h: b.height });
          }
        }
        from = at + needle.length;
      }
    }
    return rects;
  }

  function positionMarks() {
    for (var i = 0; i < markPool.length; i++) markPool[i].style.display = 'none';
    while (markPool.length < markRects.length) markPool.push(makeMarkEl());
    for (var j = 0; j < markRects.length; j++) placeBox(markPool[j], markRects[j]);
  }

  function highlight(value) {
    clearHighlight();
    // 텍스트가 공백으로 갈라져 있을 수 있다("170% 증가" vs "170 % 증가") — 원문 → 공백제거 순으로 시도
    markRects = findRects(value);
    if (!markRects.length) markRects = findRects(value.replace(/\s+/g, ''));
    positionMarks();
    if (markRects.length) {
      var first = markRects[0];
      window.scrollTo({ top: Math.max(0, first.y - 120), behavior: 'smooth' });
    }
    post('HIGHLIGHTED', { value: value, found: markRects.length });
  }
```

- [ ] **Step 3: 재배치·소거 훅 연결**

`positionOverlay()` 함수(145행) 본문 **맨 끝**에 마커 재배치를 붙인다 (스크롤·줌·리사이즈에서 이미 호출되는 지점이다):

```javascript
    positionMarks();
```

`setPage(index)`(737행)에서 카드가 바뀌면 마커는 무효다 — `deselect();` 다음 줄에 추가:

```javascript
    clearHighlight();    // 다른 카드로 넘어가면 이전 카드의 마커는 무효
```

- [ ] **Step 4: 메시지 스위치에 명령 추가**

`editorAgent.ts` 메시지 스위치(763행 `switch (d.type) {`)의 `case 'SET_PAGE':` 다음 줄에:

```javascript
      case 'HIGHLIGHT': highlight(String(d.value || '')); break;
      case 'CLEAR_HIGHLIGHT': clearHighlight(); break;
```

- [ ] **Step 5: 하네스로 실제 동작 검증**

`tools/deck_editor_e2e/deck_harness.py`가 실 `AGENT_BODY`를 standalone HTML에 주입해 돌리는 하네스다(sandboxed iframe이라 playwright가 직접 못 들어간다). 이 하네스에 케이스를 추가한다 — 파일을 열어 기존 케이스 형식을 그대로 따르고, 다음을 확인하는 체크를 넣는다:

1. `SET_PAGE 1` → `HIGHLIGHT "238 MPa"` 전송 후 `data-pi-mark` 요소가 1개 이상 `display:block`이다.
2. 그 상태에서 `GET_HTML` → 반환된 HTML에 **`data-pi-mark`가 없다**(serialize가 제거 — 저장 오염 없음).
3. `HIGHLIGHT` 후 `DIRTY` 메시지가 오지 않았다(자동저장이 깨어나지 않는다).
4. `SET_PAGE 0` → 마커가 모두 `display:none`이다.

Run: `python tools/deck_editor_e2e/deck_harness.py`
Expected: 추가한 4개 체크 PASS (기존 체크도 전부 PASS 유지)

- [ ] **Step 6: 커밋**

```bash
git add web/src/components/deck/editorAgent.ts tools/deck_editor_e2e/deck_harness.py
git commit -m "[FE] editorAgent: HIGHLIGHT 오버레이 마커 — DOM 삽입 없이 수치 위치 표시"
```

---

## Task 5: DeckEditor 핸들 노출

**Files:**
- Modify: `web/src/components/deck/DeckEditor.tsx:40-53` (`DeckEditorHandle`), `121-138` (useImperativeHandle)

- [ ] **Step 1: 핸들 인터페이스에 추가**

`DeckEditorHandle`(40행)에 두 줄 추가:

```typescript
  highlight: (value: string) => void
  clearHighlight: () => void
```

- [ ] **Step 2: 구현 연결**

`useImperativeHandle`(121행) 안, `setPage: (index) => send('SET_PAGE', { index }),` 다음 줄에:

```typescript
    highlight: (value) => send('HIGHLIGHT', { value }),
    clearHighlight: () => send('CLEAR_HIGHLIGHT'),
```

- [ ] **Step 3: 타입 확인**

Run: `cd web && npx tsc --noEmit`
Expected: 새 에러 없음. (주의: `deck/[jobId]/page.tsx:371`의 `dirty` prop 관련 **기존 에러 1건**은 이 작업 전부터 있던 것 — 이 계획에서 고치지 않는다. 새로 생긴 에러만 본다.)

- [ ] **Step 4: 커밋**

```bash
git add web/src/components/deck/DeckEditor.tsx
git commit -m "[FE] DeckEditor: highlight/clearHighlight 핸들"
```

---

## Task 6: 팩트 패널 — 행을 버튼으로, 문구를 사용자 언어로

**Files:**
- Modify: `web/src/components/deck/DeckFactPanel.tsx` (전체)

- [ ] **Step 1: Props에 onJump 추가하고 행을 버튼으로 교체**

`DeckFactPanel.tsx`의 `Props`와 컴포넌트 시그니처:

```typescript
interface Props {
  verify: VerifyData | null | undefined
  canReverify: boolean
  onJump?: (item: { value: string; card: number }) => void
}

export default function DeckFactPanel({ verify, canReverify, onJump }: Props) {
```

- [ ] **Step 2: 헤더 라벨 삭제 + 원장 제목 교체**

27행 `<div className="font-mono text-[10px] ...">Fidelity · 해자</div>` — **줄 전체 삭제.**

73행 `Claim Ledger` → `수치 목록`:

```tsx
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3 group-hover:text-ink-2 transition-colors">수치 목록</span>
```

- [ ] **Step 3: 행 렌더러를 공용 컴포넌트로 뽑고 클릭 연결**

파일 하단(export default 함수 바깥)에 행 컴포넌트를 추가한다. 두 원장(suspect/claims)이 같은 클릭·비활성 규칙을 공유해야 하므로 한 곳에 둔다:

```tsx
function LedgerRow({
  value, context, card, badge, onJump,
}: {
  value: string
  context: string
  card: number | null
  badge: React.ReactNode
  onJump?: (item: { value: string; card: number }) => void
}) {
  const jumpable = card !== null && card !== undefined && !!onJump
  const body = (
    <>
      <span className="font-mono text-[12.5px] font-bold text-ink shrink-0 max-w-[128px] truncate" title={value}>{value}</span>
      <span className="flex-1 text-[11px] text-ink-2 leading-snug line-clamp-2">{context}</span>
      {badge}
    </>
  )
  if (!jumpable) {
    return (
      <li className="flex items-center gap-2.5 py-2.5 border-t border-deck-line-soft first:border-t-0"
        title="위치 정보가 없어요 — 다시 만들면 표시됩니다">
        {body}
      </li>
    )
  }
  return (
    <li className="border-t border-deck-line-soft first:border-t-0">
      <button
        type="button"
        onClick={() => onJump!({ value, card: card as number })}
        title={`카드 ${(card as number) + 1}에서 이 수치 보기`}
        className="flex w-full items-center gap-2.5 py-2.5 text-left rounded-lg hover:bg-bg-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-forest-green/40 transition-colors"
      >
        {body}
        <span className="shrink-0 text-[10px] font-mono text-ink-3">카드 {(card as number) + 1} ›</span>
      </button>
    </li>
  )
}
```

- [ ] **Step 4: 두 원장 루프를 LedgerRow로 교체**

`suspects.map` 블록(82-90행)을 교체:

```tsx
            {suspects.map((d, i) => (
              <LedgerRow
                key={`d${i}`}
                value={d.value}
                context={`카드 안 수치와 계산이 맞지 않아요 — ‘% 증가’와 ‘배’를 혼동했을 수 있어요. ${d.context.trim()}`}
                card={d.card ?? null}
                onJump={onJump}
                badge={<span className="shrink-0 text-[9.5px] font-bold px-1.5 py-1 rounded-md bg-risk-medium-faint text-risk-medium border border-risk-medium-border">계산이 안 맞아요</span>}
              />
            ))}
```

`shown.map` 블록(91-103행)을 교체:

```tsx
            {shown.map((c, i) => (
              <LedgerRow
                key={i}
                value={c.value}
                context={c.context.trim()}
                card={c.card ?? null}
                onJump={onJump}
                badge={c.verified ? (
                  <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold text-forest-green-deep bg-forest-green-wash border border-forest-green/25 rounded-md px-1.5 py-1">
                    <span className="w-[11px] h-[11px] rounded-full bg-forest-green text-canvas grid place-items-center text-[7px]" aria-hidden="true">✓</span>원문 확인
                  </span>
                ) : (
                  <span className="shrink-0 text-[9.5px] font-bold px-1.5 py-1 rounded-md bg-risk-medium-faint text-risk-medium border border-risk-medium-border">원문에 없음</span>
                )}
              />
            ))}
```

- [ ] **Step 5: 타입·기존 테스트 확인**

Run: `cd web && npx tsc --noEmit && npx vitest run`
Expected: 새 에러 없음, 기존 vitest 전부 PASS

- [ ] **Step 6: 커밋**

```bash
git add web/src/components/deck/DeckFactPanel.tsx
git commit -m "[FE] 팩트 패널: 수치 행=클릭 가능한 점프 버튼 + 내부용어 제거(해자/CLAIM LEDGER)"
```

---

## Task 7: 문맥 바 — 확인 필요를 순서대로 훑는다

**Files:**
- Create: `web/src/components/deck/DeckFactJumpBar.tsx`

편집 모드로 넘어가면 팩트 드로어가 닫혀 "무엇을 찾고 있었는지"를 잃는다. 이 바가 그 맥락을 들고 있다.

- [ ] **Step 1: 컴포넌트 작성**

`web/src/components/deck/DeckFactJumpBar.tsx`:

```tsx
'use client'

// 팩트 점프 문맥 바 — 편집 캔버스 상단. 확인 필요 항목을 순서대로 훑게 한다.
// (편집 모드에선 팩트 패널이 드로어라 닫힌다 → 무엇을 보고 있었는지 여기서 붙든다)
import type { ReviewItem } from '@/lib/verifyStatus'

interface Props {
  item: ReviewItem
  index: number          // 0-기반
  total: number
  found: boolean | null  // null=아직 응답 전, false=카드 안에서 못 찾음
  onNext: () => void
  onClose: () => void
}

export default function DeckFactJumpBar({ item, index, total, found, onNext, onClose }: Props) {
  const reason = item.reason === 'mismatch' ? '계산이 안 맞아요' : '원문에서 확인 안 됨'
  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 rounded-full border border-risk-medium-border bg-risk-medium-faint px-3.5 py-2 shadow-card backdrop-blur">
      <span className="font-mono text-[12px] font-bold text-ink">{item.value}</span>
      <span className="text-[11.5px] text-risk-medium">{reason}</span>
      {found === false && (
        <span className="text-[11px] text-ink-3">이 카드에서 찾지 못했어요 — 이미 고치셨을 수 있어요</span>
      )}
      <span className="font-mono text-[11px] text-ink-3 tabular-nums">{index + 1}/{total}</span>
      {total > 1 && (
        <button type="button" onClick={onNext}
          className="text-[11.5px] font-semibold text-forest-green-deep hover:underline">다음 항목 →</button>
      )}
      <button type="button" onClick={onClose} aria-label="닫기"
        className="w-6 h-6 rounded-full grid place-items-center text-ink-3 hover:text-ink hover:bg-surface transition-colors">✕</button>
    </div>
  )
}
```

- [ ] **Step 2: 타입 확인**

Run: `cd web && npx tsc --noEmit`
Expected: 새 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add web/src/components/deck/DeckFactJumpBar.tsx
git commit -m "[FE] 팩트 점프 문맥 바 컴포넌트"
```

---

## Task 8: 페이지 배선 — 클릭이 실제로 데려가게 한다

**Files:**
- Modify: `web/src/app/deck/[jobId]/page.tsx` (import, 상태, onJump 핸들러, DeckFactPanel 2곳, 편집 캔버스)

- [ ] **Step 1: import와 상태 추가**

import 블록에:

```tsx
import DeckFactJumpBar from '@/components/deck/DeckFactJumpBar'
import { reviewQueue, type ReviewItem, type VerifyData } from '@/lib/verifyStatus'
```

(기존 `import { type VerifyData } from '@/lib/verifyStatus'` 줄을 위 줄로 교체한다.)

상태 선언부(`const [showFact, setShowFact] = useState(...)` 근처)에 추가:

```tsx
  const [jump, setJump] = useState<{ item: ReviewItem; index: number } | null>(null)  // 팩트 점프 중인 항목
  const [jumpFound, setJumpFound] = useState<boolean | null>(null)                    // 카드 안에서 찾았나
```

- [ ] **Step 2: 점프 핸들러 추가**

`enterEditAt`(331행) 아래에 추가:

```tsx
  // 팩트 패널 수치 클릭 → 그 카드로 데려가 수치에 마커를 씌운다.
  // 뷰 모드면 편집 모드로 전환한다(뷰어는 PNG라 텍스트 좌표를 모른다).
  // 안전: toggleMode의 ver 상승은 pngStale 가드를 타므로, 보기만 하고 나오면 재렌더가 없다.
  const queue = useMemo(() => reviewQueue(deck.verify), [deck.verify])

  const jumpTo = useCallback((index: number) => {
    const item = queue[index]
    if (!item || item.card === null) return
    setJump({ item, index })
    setJumpFound(null)
    setShowFact(false)
    if (mode === 'view') {
      enterEditAt(item.card)                 // EDITOR_READY 후 initialPage로 그 카드에 진입
    } else {
      editorRef.current?.setPage(item.card)
    }
    // 카드 전환(페이징·폰트 프리즈) 후에 마킹해야 좌표가 맞는다
    window.setTimeout(() => editorRef.current?.highlight(item.value), 260)
  }, [queue, mode, enterEditAt])

  const handleJump = useCallback((it: { value: string; card: number }) => {
    const i = queue.findIndex((q) => q.value === it.value && q.card === it.card)
    jumpTo(i < 0 ? 0 : i)
  }, [queue, jumpTo])

  const closeJump = useCallback(() => {
    setJump(null)
    editorRef.current?.clearHighlight()
  }, [])
```

`useMemo`가 import에 없으면 `react` import에 추가한다.

- [ ] **Step 3: HIGHLIGHTED 응답 수신**

`DeckEditor`는 `onHighlighted` 콜백이 없다. `DeckEditor.tsx`의 Props에 추가하고(`onPage` 옆), 메시지 스위치(150행 근처)에 케이스를 넣는다:

`web/src/components/deck/DeckEditor.tsx` Props 인터페이스:

```typescript
  onHighlighted?: (info: { value: string; found: number }) => void
```

메시지 스위치의 `case 'PAGE':` 다음:

```typescript
        case 'HIGHLIGHTED': onHighlighted?.({ value: String(d.value), found: Number(d.found) || 0 }); break
```

`useEffect` 의존성 배열(186행)에 `onHighlighted`를 추가한다.

- [ ] **Step 4: 편집 캔버스에 문맥 바 + 콜백 연결**

`page.tsx`의 `<DeckEditor ... onPage={setPage} />`에 추가:

```tsx
                onHighlighted={(info) => setJumpFound(info.found > 0)}
```

같은 `<div className="relative h-full">` 안, 페이저 블록 앞에 문맥 바를 넣는다:

```tsx
              {jump && (
                <DeckFactJumpBar
                  item={jump.item}
                  index={jump.index}
                  total={queue.length}
                  found={jumpFound}
                  onNext={() => jumpTo((jump.index + 1) % queue.length)}
                  onClose={closeJump}
                />
              )}
```

- [ ] **Step 5: 두 DeckFactPanel에 onJump 연결**

뷰 모드 패널(499행)과 편집 드로어 패널(558행) **둘 다**:

```tsx
            <DeckFactPanel verify={v} canReverify={deck.canReverify !== false} onJump={handleJump} />
```

- [ ] **Step 6: 타입·테스트**

Run: `cd web && npx tsc --noEmit && npx vitest run`
Expected: 새 에러 없음, vitest 전부 PASS

- [ ] **Step 7: 커밋**

```bash
git add web/src/app/deck/\[jobId\]/page.tsx web/src/components/deck/DeckEditor.tsx
git commit -m "[FE] 팩트 수치 클릭 → 카드 점프+하이라이트 배선 + 문맥 바"
```

---

## Task 9: 실브라우저 검증 (완료 조건)

**Files:** 없음 (검증 전용)

테스트 그린은 "코드가 돈다"까지고, 이 기능의 완료는 **눈으로 마커를 본 것**이다.

- [ ] **Step 1: 백엔드·프론트 기동**

```bash
# 터미널 A
cd backend && ../.venv/Scripts/python -m uvicorn main:app --port 8000
# 터미널 B
cd web && npm run dev
```

- [ ] **Step 2: 확인 필요 수치가 있는 덱 준비**

기존 덱 중 `unverified > 0`인 것을 쓴다. 없으면:

```bash
python tools/deck_editor_e2e/seed_session.py
```

로 시드 세션을 만들고 `/deck/<jobId>`를 연다.

**주의:** 구 덱은 verify JSON에 `card`가 없어 클릭이 비활성이다(설계된 동작). 새로 만들거나 재저장(편집 후 자동저장 → 재검증)된 덱으로 확인한다.

- [ ] **Step 3: 눈으로 확인**

```bash
wmux browser open http://localhost:3000/deck/<jobId>
wmux browser snapshot
wmux browser click @<확인 필요 항목의 ref>
wmux browser screenshot
```

확인 항목:
1. 편집 모드로 전환되고 **그 수치가 있는 카드**가 떠 있다.
2. 그 수치 위에 **노란 마커**가 보인다.
3. 상단 문맥 바에 `값 — 원문에서 확인 안 됨 · 1/N · [다음 항목 →]`가 보인다.
4. `다음 항목`을 누르면 다음 수치의 카드로 넘어가고 마커가 옮겨간다.

- [ ] **Step 4: 저장 오염 없음 확인 (가장 중요)**

마커가 떠 있는 상태에서 아무것도 고치지 않고 뷰 모드로 돌아간다.

```bash
wmux browser eval "document.querySelector('[data-testid=save-status]')?.textContent"
```

확인 항목:
1. 자동저장이 **깨어나지 않는다**(저장 상태가 '저장 중'으로 바뀌지 않는다).
2. 뷰어 카드 PNG가 **다시 렌더되지 않는다**(`pngStale=false`라 `ver`가 그대로 — 셔머 스켈레톤이 뜨지 않는다).
3. 덱 HTML을 API로 받아 `data-pi-mark`가 **없다**:

```bash
curl -s localhost:8000/api/deck/<jobId> | grep -c "data-pi-mark"   # → 0
```

- [ ] **Step 5: 문구 확인**

```bash
wmux browser eval "document.body.innerText.match(/해자|FIDELITY|CLAIM LEDGER/gi)"
```
Expected: `null` (내부 용어가 화면에 없다)

- [ ] **Step 6: 스크린샷을 남기고 커밋**

검증 스크린샷은 커밋하지 않는다(레포 비대). 대신 실패한 게 있으면 그 자리에서 고치고 해당 Task로 되돌아간다.

---

## 마무리

- [ ] `pytest backend/tests/ -q` green
- [ ] `cd web && npx vitest run` green
- [ ] `cd web && npx tsc --noEmit` — 새 에러 없음 (기존 `dirty` prop 에러 1건은 별개)
- [ ] `python tools/deck_editor_e2e/deck_harness.py` green
- [ ] 실브라우저 4개 확인 항목 통과
