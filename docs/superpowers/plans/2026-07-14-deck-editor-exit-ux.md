# /deck 편집기 나가기 UX (A안) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 편집기에서 대시보드로 나가는 길을 **보이게** 하고, 자동저장으로 나가기를 **안전한 행동**으로 만든다.

**Architecture:** 자동저장 로직을 React와 무관한 순수 스케줄러(`src/lib/autosave.ts`)로 만들고 vitest 페이크 타이머로 테스트한다(이 레포엔 jsdom·testing-library가 없다 — 기존 테스트는 전부 `src/lib/*.test.ts` 순수 로직). 얇은 React 훅(`useAutosave`)이 그 코어를 감싸고, `DeckTopBar`는 상태를 props로만 받는다(상태를 만들지 않는다).

**Tech Stack:** Next.js 15 App Router · TypeScript · Tailwind · vitest(node 환경, jsdom 없음)

**스펙:** `docs/superpowers/specs/2026-07-14-deck-editor-exit-ux-design.md`

---

## 파일 구조

| 파일 | 책임 |
|---|---|
| `web/src/lib/autosave.ts` (신규) | 프레임워크 무관 자동저장 스케줄러. 디바운스·차단·재시도·플러시. **DOM·React를 모른다** |
| `web/src/lib/autosave.test.ts` (신규) | 위 코어의 vitest 테스트(페이크 타이머) |
| `web/src/lib/useAutosave.ts` (신규) | 코어를 감싸는 얇은 React 훅. `useEffect`로 생명주기만 배선 |
| `web/src/components/deck/DeckTopBar.tsx` (수정) | 나가기 버튼 승격 · 로고 제거 · 저장 상태 표시 · 수동 저장 버튼 제거 |
| `web/src/app/deck/[jobId]/page.tsx` (수정) | 훅 배선 · 자동저장은 선택 보존/ver 미상승 · 뷰어 전환 시 ver 1회 상승 |

---

## Task 1: 자동저장 코어 (순수 스케줄러)

**Files:**
- Create: `web/src/lib/autosave.ts`
- Test: `web/src/lib/autosave.test.ts`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`web/src/lib/autosave.test.ts`:

```ts
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { createAutosave } from './autosave'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('createAutosave', () => {
  it('편집 후 유휴 시간이 지나면 1회 저장한다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    expect(a.status()).toBe('dirty')
    expect(save).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(1)
    expect(a.status()).toBe('clean')
  })

  it('연속 편집은 디바운스된다 — 마지막 편집 기준 1회만', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(2000)
    a.markDirty()                       // 타이머 리셋
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).not.toHaveBeenCalled()  // 아직 3초 유휴가 안 됐다

    await vi.advanceTimersByTimeAsync(1000)
    expect(save).toHaveBeenCalledTimes(1)
  })

  it('차단 중(AI 제안 대기 등)에는 저장하지 않는다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    let blocked = true
    const a = createAutosave({ save, delayMs: 3000, isBlocked: () => blocked })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(10_000)
    expect(save).not.toHaveBeenCalled()
    expect(a.status()).toBe('dirty')     // dirty는 유지된다 — 편집이 사라지면 안 된다

    blocked = false
    a.markDirty()                        // 차단 해제 후 다음 편집에 다시 예약
    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(1)
  })

  it('저장 실패 시 1회 자동 재시도하고, 그래도 실패하면 error가 된다', async () => {
    const save = vi.fn().mockRejectedValue(new Error('offline'))
    const a = createAutosave({ save, delayMs: 3000, retryDelayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(3000)   // 자동 재시도 1회
    expect(save).toHaveBeenCalledTimes(2)
    expect(a.status()).toBe('error')
    expect(a.isDirty()).toBe(true)            // 편집은 아직 안 저장됐다
  })

  it('retry()는 error 상태에서 즉시 다시 저장한다', async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000, retryDelayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)   // 1차 실패
    await vi.advanceTimersByTimeAsync(3000)   // 재시도도 mockResolvedValue라 성공
    expect(a.status()).toBe('clean')

    save.mockRejectedValueOnce(new Error('offline'))
    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)
    await vi.advanceTimersByTimeAsync(3000)
    expect(a.status()).toBe('error')

    save.mockResolvedValue(undefined)
    await a.retry()
    expect(a.status()).toBe('clean')
  })

  it('flush()는 대기 중인 저장을 즉시 실행한다 (탭 이탈 대비)', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    await a.flush()
    expect(save).toHaveBeenCalledTimes(1)
    expect(a.status()).toBe('clean')
  })

  it('깨끗한 상태에서 flush()는 아무것도 하지 않는다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })
    await a.flush()
    expect(save).not.toHaveBeenCalled()
  })

  it('저장 중에 들어온 편집은 잃지 않는다 — 저장 후 다시 예약된다', async () => {
    let resolveSave: () => void = () => {}
    const save = vi.fn().mockImplementation(() => new Promise<void>((r) => { resolveSave = r }))
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)
    expect(a.status()).toBe('saving')

    a.markDirty()                 // 저장 중에 또 편집
    resolveSave()
    await vi.advanceTimersByTimeAsync(0)
    expect(a.status()).toBe('dirty')     // 저장 끝났지만 새 편집이 있으므로 dirty

    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(2)
    expect(a.status()).toBe('clean')
  })

  it('dispose()는 예약된 저장을 취소한다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })
    a.markDirty()
    a.dispose()
    await vi.advanceTimersByTimeAsync(10_000)
    expect(save).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `cd web && npx vitest run src/lib/autosave.test.ts`
Expected: FAIL — `Failed to resolve import "./autosave"`

- [ ] **Step 3: 최소 구현을 쓴다**

`web/src/lib/autosave.ts`:

```ts
// 자동저장 스케줄러 — React·DOM 무관(테스트 가능한 순수 코어).
//
// 왜 코어를 분리하나: 이 레포엔 jsdom·testing-library가 없다(기존 테스트는 전부 src/lib 순수 로직).
// 훅 안에 로직을 넣으면 테스트할 방법이 없다 — 디바운스·재시도·차단은 버그가 숨기 좋은 곳이라
// 반드시 테스트돼야 한다.

export type AutosaveStatus = 'clean' | 'dirty' | 'saving' | 'error'

export interface AutosaveOptions {
  save: () => Promise<void>
  delayMs?: number            // 편집 후 유휴 시간
  retryDelayMs?: number       // 실패 후 자동 재시도까지
  isBlocked?: () => boolean   // true면 저장하지 않는다(AI 제안 대기·드래그 중 등)
  onChange?: (status: AutosaveStatus) => void
}

export interface Autosave {
  markDirty: () => void
  flush: () => Promise<void>
  retry: () => Promise<void>
  status: () => AutosaveStatus
  isDirty: () => boolean
  dispose: () => void
}

export function createAutosave({
  save, delayMs = 3000, retryDelayMs = 3000, isBlocked, onChange,
}: AutosaveOptions): Autosave {
  let status: AutosaveStatus = 'clean'
  let dirty = false                 // 저장되지 않은 편집이 있나 (status와 별개 — saving 중에도 새 편집이 들어온다)
  let timer: ReturnType<typeof setTimeout> | null = null
  let retried = false               // 이번 실패 사이클에서 자동 재시도를 이미 썼나
  let disposed = false

  const set = (s: AutosaveStatus) => {
    if (status === s) return
    status = s
    onChange?.(s)
  }

  const clearTimer = () => {
    if (timer) { clearTimeout(timer); timer = null }
  }

  const schedule = (ms: number) => {
    clearTimer()
    timer = setTimeout(() => { timer = null; void run() }, ms)
  }

  const run = async (): Promise<void> => {
    if (disposed || !dirty) return
    if (status === 'saving') return
    if (isBlocked?.()) return              // 차단 중 — dirty는 유지한다(편집을 잃지 않는다)

    set('saving')
    const hadDirty = dirty
    dirty = false                          // 이 시점 이후의 편집은 '새 편집'이다
    try {
      await save()
      if (disposed) return
      retried = false
      set(dirty ? 'dirty' : 'clean')       // 저장 중 들어온 편집이 있으면 다시 dirty
      if (dirty) schedule(delayMs)
    } catch {
      if (disposed) return
      dirty = hadDirty                     // 실패 — 편집은 아직 안 저장됐다
      if (!retried) {
        retried = true
        set('dirty')
        schedule(retryDelayMs)             // 자동 재시도 1회
      } else {
        set('error')                       // 사용자 개입 필요
      }
    }
  }

  return {
    markDirty() {
      if (disposed) return
      dirty = true
      retried = false
      if (status !== 'saving') set('dirty')
      schedule(delayMs)
    },
    async flush() {
      clearTimer()
      await run()
    },
    async retry() {
      retried = false
      clearTimer()
      await run()
    },
    status: () => status,
    isDirty: () => dirty,
    dispose() {
      disposed = true
      clearTimer()
    },
  }
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `cd web && npx vitest run src/lib/autosave.test.ts`
Expected: PASS (9 tests)

- [ ] **Step 5: 커밋한다**

```bash
git add web/src/lib/autosave.ts web/src/lib/autosave.test.ts
git commit -m "[WEB] 자동저장 코어 — 디바운스·차단·재시도·플러시 (순수 스케줄러)"
```

---

## Task 2: React 훅 (얇은 래퍼)

**Files:**
- Create: `web/src/lib/useAutosave.ts`

- [ ] **Step 1: 훅을 쓴다**

로직은 Task 1의 코어에 있다. 훅은 **생명주기 배선만** 한다 — 테스트하지 않는다(jsdom 없음).
대신 코어가 테스트돼 있고, 훅은 20줄이라 눈으로 검증 가능하다.

`web/src/lib/useAutosave.ts`:

```ts
'use client'

// 자동저장 훅 — 로직은 createAutosave(순수 코어, 테스트됨)에 있고 여기선 생명주기만 배선한다.
import { useEffect, useRef, useState } from 'react'
import { createAutosave, type Autosave, type AutosaveStatus } from './autosave'

interface Params {
  save: () => Promise<void>
  enabled: boolean            // 편집 모드일 때만 true
  isBlocked: () => boolean    // AI 제안 대기·저장 중 등
  delayMs?: number
}

export function useAutosave({ save, enabled, isBlocked, delayMs = 3000 }: Params) {
  const [status, setStatus] = useState<AutosaveStatus>('clean')
  const ref = useRef<Autosave | null>(null)

  // 최신 콜백을 참조로 유지(코어를 재생성하지 않기 위해)
  const saveRef = useRef(save)
  const blockedRef = useRef(isBlocked)
  saveRef.current = save
  blockedRef.current = isBlocked

  useEffect(() => {
    if (!enabled) return
    const a = createAutosave({
      save: () => saveRef.current(),
      isBlocked: () => blockedRef.current(),
      delayMs,
      onChange: setStatus,
    })
    ref.current = a

    const onHide = () => { if (document.visibilityState === 'hidden') void a.flush() }
    document.addEventListener('visibilitychange', onHide)

    return () => {
      document.removeEventListener('visibilitychange', onHide)
      void a.flush()          // 편집 모드를 떠날 때 마지막 저장 시도
      a.dispose()
      ref.current = null
      setStatus('clean')
    }
  }, [enabled, delayMs])

  return {
    status,
    markDirty: () => ref.current?.markDirty(),
    flush: () => ref.current?.flush() ?? Promise.resolve(),
    retry: () => ref.current?.retry() ?? Promise.resolve(),
  }
}
```

- [ ] **Step 2: 타입 검사**

Run: `cd web && npx tsc --noEmit`
Expected: 에러 없음

- [ ] **Step 3: 커밋한다**

```bash
git add web/src/lib/useAutosave.ts
git commit -m "[WEB] useAutosave 훅 — 코어 배선 + visibilitychange 플러시"
```

---

## Task 3: 상단바 — 나가기 승격 · 저장 상태 · 로고 제거

**Files:**
- Modify: `web/src/components/deck/DeckTopBar.tsx`

- [ ] **Step 1: props를 새 계약으로 바꾼다**

`DeckTopBar.tsx`의 `interface Props`에서 아래를 **삭제**한다:
```ts
  dirty?: boolean
  saveLabel?: string
  savedAt?: string
  onSave?: () => void
  saveDisabled?: boolean
```
그리고 아래를 **추가**한다:
```ts
  saveStatus?: 'clean' | 'dirty' | 'saving' | 'error'   // 편집 모드에서만 의미 있음
  savedAt?: string          // 마지막 저장 시각 'hh:mm'
  onRetrySave?: () => void  // error 상태에서 재시도
```

- [ ] **Step 2: guardLeave를 error 전용으로 좁힌다**

기존:
```ts
  const guardLeave = (e: MouseEvent) => {
    if (editing && dirty && !window.confirm('저장하지 않은 편집이 있어요. 나가면 사라집니다. 나가시겠어요?')) e.preventDefault()
  }
```
교체:
```ts
  // 자동저장이 도는 한 나가기는 안전한 행동이다 — 저장이 **실패한** 상태에서만 막는다.
  const guardLeave = (e: MouseEvent) => {
    if (editing && saveStatus === 'error' &&
        !window.confirm('마지막 편집이 저장되지 않았어요. 나가면 사라집니다. 나가시겠어요?')) {
      e.preventDefault()
    }
  }
```

- [ ] **Step 3: 상단바 좌측을 교체한다 (로고 삭제 → 나가기 버튼 승격)**

기존 `{/* ① 정체성·탈출 … */}` 의 `<Link>`(로고)와 `<nav>` 블록 전체를 아래로 교체:

```tsx
      {/* ① 탈출 — 상단바 첫 요소, 버튼 형태(클릭 가능함이 형태로 보이게) */}
      <Link href="/dashboard" onClick={guardLeave}
        className="flex items-center gap-1.5 shrink-0 rounded-lg border border-border bg-surface px-3 py-1.5
                   text-[13px] font-bold text-ink hover:bg-bg-subtle transition-colors">
        <span aria-hidden="true" className="text-[15px] leading-none">←</span>대시보드
      </Link>

      {/* ② 위치 — 덱 제목 + 저장 상태 */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <span className="text-[13.5px] font-semibold text-ink truncate min-w-0" title={filename}>{filename}</span>
        {editing && <SaveState status={saveStatus} savedAt={savedAt} onRetry={onRetrySave} />}
      </div>
```

- [ ] **Step 4: SaveState 컴포넌트를 추가한다 (MoatRing 아래)**

```tsx
// 저장 상태 — "나가도 안전하다"를 형태로 증명한다(수동 저장 버튼을 대체)
function SaveState({ status, savedAt, onRetry }: {
  status?: 'clean' | 'dirty' | 'saving' | 'error'; savedAt?: string; onRetry?: () => void
}) {
  if (status === 'error') {
    return (
      <button onClick={onRetry}
        className="flex items-center gap-1.5 shrink-0 text-[12px] font-semibold text-risk-medium hover:underline">
        <span aria-hidden="true">⚠</span>저장 실패 — 다시 시도
      </button>
    )
  }
  if (status === 'saving') {
    return <span className="shrink-0 text-[12px] font-semibold text-ink-3">저장 중…</span>
  }
  if (status === 'dirty') {
    return <span className="shrink-0 text-[12px] font-semibold text-ink-3">변경사항 있음</span>
  }
  return (
    <span className="flex items-center gap-1.5 shrink-0 text-[12px] font-semibold text-forest-green-deep">
      <span className="w-1.5 h-1.5 rounded-full bg-forest-green" aria-hidden="true" />
      모든 변경 저장됨{savedAt ? ` · ${savedAt}` : ''}
    </span>
  )
}
```

- [ ] **Step 5: 편집 전용 블록에서 수동 저장 버튼을 제거한다**

`{editing && ( … )}` 안의 `<button onClick={onSave} …>{saveLabel}…</button>` 을 **삭제**한다.
undo/redo 버튼 두 개는 남긴다.

- [ ] **Step 6: 시그니처에서 삭제한 props를 구조분해에서도 뺀다**

```tsx
export default function DeckTopBar({
  filename, editing, verified, unverified, onBadgeClick, factOpen, factInline, onToggleMode, onExport,
  saveStatus, savedAt, onRetrySave,
  canUndo, canRedo, onUndo, onRedo,
}: Props) {
```

- [ ] **Step 7: 타입 검사 (page.tsx가 아직 옛 props를 넘기므로 여기서 에러가 나야 정상)**

Run: `cd web && npx tsc --noEmit`
Expected: `page.tsx`에서 `dirty`·`saveLabel`·`onSave`·`saveDisabled` 관련 에러. Task 4에서 고친다.

---

## Task 4: 페이지 배선 — 자동저장 · 선택 보존 · ver 억제

**Files:**
- Modify: `web/src/app/deck/[jobId]/page.tsx`

- [ ] **Step 1: `handleSave`를 자동/수동 두 경로로 분기한다**

기존 `handleSave`(선택을 풀고 ver를 올린다)를 아래로 교체:

```tsx
  // 저장 코어 — silent=true(자동저장)면 선택을 풀지 않고 PNG ver도 올리지 않는다.
  //   · 선택을 풀면 3초마다 사용자의 선택이 사라진다(편집 불가)
  //   · 편집 캔버스는 iframe이라 PNG가 필요 없다 — ver를 올리면 서버 렌더 7장이 헛돈다
  const saveCore = useCallback(async (silent: boolean) => {
    if (!editorRef.current) return
    setSaving(true)
    try {
      const html = await editorRef.current.getHtml()
      const r = await patchDeck(jobId, html)
      setDeck((prev) => prev ? {
        ...prev, html, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      setEditWarnings(r.data.warnings ?? [])
      setDirty(false)
      stampSaved()
      if (!silent) {
        setVer((x) => x + 1)      // 뷰어 PNG 갱신
        setSelected(null)
      } else {
        setPngStale(true)         // 뷰어 전환 시 한 번만 갱신하도록 표시
      }
    } finally { setSaving(false) }
  }, [jobId, stampSaved])

  const handleSave = useCallback(() => saveCore(false), [saveCore])
```

- [ ] **Step 2: `pngStale` 상태를 추가한다** (다른 state 선언 옆, `const [ver, setVer] = useState(0)` 아래)

```tsx
  const [pngStale, setPngStale] = useState(false)   // 자동저장으로 html은 바뀌었는데 PNG는 안 받은 상태
```

- [ ] **Step 3: 자동저장 훅을 배선한다** (`handleSave` 정의 아래)

```tsx
  // 자동저장 — 편집 모드에서만. AI 제안(pending) 대기 중엔 돌지 않는다(사용자가 결정 중이다).
  const autosave = useAutosave({
    enabled: mode === 'edit',
    save: () => saveCore(true),
    isBlocked: () => pending !== null || saving || proposing || committing || reverting,
  })
```

import 추가 (파일 상단 import 블록):
```tsx
import { useAutosave } from '@/lib/useAutosave'
```

- [ ] **Step 4: 편집이 일어날 때 `markDirty`를 부른다**

현재 `page.tsx:427`은 이렇다 — **`setPending(null)`을 반드시 보존해야 한다**
(사용자가 직접 편집하면 대기 중인 AI 제안은 폐기된다):

```tsx
                onDirty={() => { setDirty(true); setPending(null) }}
```

핸들러로 승격하고 `markDirty`를 더한다:

```tsx
  const handleDirty = useCallback(() => {
    setDirty(true)
    setPending(null)          // ★기존 동작 — 직접 편집은 대기 중 AI 제안을 폐기한다
    autosave.markDirty()
  }, [autosave])
```
그리고 호출부를 `onDirty={handleDirty}` 로 교체한다.

- [ ] **Step 5: 모드 전환 시 PNG를 한 번만 갱신한다**

`toggleMode`를 아래로 교체(편집 → 뷰어로 갈 때만 ver 상승):

```tsx
  const toggleMode = useCallback(async () => {
    if (mode === 'edit') {
      await autosave.flush()          // 나가기 전에 마지막 편집 저장
      if (pngStale) {
        setVer((x) => x + 1)          // 이때 딱 한 번 PNG를 새로 받는다
        setPngStale(false)
      }
      setSelected(null)
      setMode('view')
    } else {
      setMode('edit')
    }
  }, [mode, autosave, pngStale])
```

- [ ] **Step 6: DeckTopBar 호출부를 새 props로 바꾼다**

```tsx
      <DeckTopBar
        filename={deck.filename ?? '덱'}
        editing={editing}
        verified={v?.verified}
        unverified={v?.unverified}
        onBadgeClick={onBadgeClick}
        factOpen={showFact}
        factInline={!editing}
        onToggleMode={toggleMode}
        onExport={() => setShowExport(true)}
        canUndo={history.canUndo}
        canRedo={history.canRedo}
        onUndo={() => editorRef.current?.undo()}
        onRedo={() => editorRef.current?.redo()}
        saveStatus={autosave.status}
        savedAt={savedAt}
        onRetrySave={() => void autosave.retry()}
      />
```

그리고 더는 쓰지 않는 `saveLabel` 계산 줄을 **삭제**한다:
```tsx
  const saveLabel = saving ? '저장 중…' : dirty ? '저장' : '저장됨'   // ← 삭제
```

- [ ] **Step 7: 타입 검사 + 전체 테스트**

Run: `cd web && npx tsc --noEmit && npx vitest run`
Expected: tsc 에러 없음, vitest 전부 통과

- [ ] **Step 8: 커밋한다**

```bash
git add web/src/components/deck/DeckTopBar.tsx "web/src/app/deck/[jobId]/page.tsx"
git commit -m "[WEB] 편집기 나가기 UX — 대시보드 버튼 승격 + 자동저장(선택 보존·PNG 재렌더 억제)"
```

---

## Task 5: 실브라우저 검증 (완료 조건)

**Files:** 없음 (검증만)

- [ ] **Step 1: 서버를 띄운다**

```bash
# 터미널 1
cd backend && ../.venv/Scripts/python.exe -m uvicorn main:app --port 8000
# 터미널 2
cd web && npm run dev
```

- [ ] **Step 2: 편집기를 연다**

브라우저로 `http://localhost:3000/deck/094fe1e2-5bf9-4df2-93ef-b75d79f1af71` → 상단 `편집` 탭.

- [ ] **Step 3: 완료 조건을 하나씩 확인한다** (스펙 §7)

| # | 확인 | 기대 |
|---|---|---|
| 1 | 텍스트를 고치고 3초 기다린다 | `저장 중…` → `● 모든 변경 저장됨 · hh:mm` |
| 2 | 새로고침한다 | 편집이 남아 있다 |
| 3 | 요소를 선택하고 3초 기다린다 | **선택이 유지된다**(자동저장이 풀지 않는다) |
| 4 | AI에게 수정을 제안시키고(제안 카드가 뜬 채) 3초 기다린다 | **자동저장이 돌지 않는다**(상태가 `변경사항 있음`에 머문다) |
| 5 | `← 대시보드`를 누른다 | **다이얼로그 없이** 대시보드로 이동 |
| 6 | 개발자도구 Network를 Offline으로 두고 편집 → 6초 기다린다 | `⚠ 저장 실패 — 다시 시도` |
| 7 | 그 상태로 `← 대시보드` 클릭 | *"마지막 편집이 저장되지 않았어요"* 확인창이 뜬다 |
| 8 | 온라인 복구 후 `다시 시도` 클릭 | `● 모든 변경 저장됨` |

- [ ] **Step 4: 스크린샷으로 상단바를 남긴다**

```bash
node "C:\Users\User\Downloads\wmux-0.13.0-win-x64\resources\cli\wmux.js" browser open "http://localhost:3000/deck/094fe1e2-5bf9-4df2-93ef-b75d79f1af71"
node "C:\Users\User\Downloads\wmux-0.13.0-win-x64\resources\cli\wmux.js" browser screenshot
```
확인: 좌상단이 `[← 대시보드]` 버튼이고, 초록 강조는 `내보내기` 하나뿐이다.

- [ ] **Step 5: 커밋한다**

```bash
git add -A
git commit -m "[WEB] 나가기 UX 실브라우저 검증 — 완료조건 8/8"
```

---

## 스펙 대조 (self-review)

| 스펙 요구 | 태스크 |
|---|---|
| `← 대시보드` 버튼 승격·로고 제거 | Task 3 Step 3 |
| 저장 상태 상시 표시 | Task 3 Step 4 |
| 수동 저장 버튼 제거 | Task 3 Step 5 |
| 자동저장 3초 유휴 | Task 1 (코어) + Task 4 Step 3 |
| 차단 조건(pending·saving·조작 중) | Task 1 (`isBlocked`) + Task 4 Step 3 |
| 선택 보존 | Task 4 Step 1 (`silent`) |
| PNG 재렌더 억제 | Task 4 Step 1·5 (`pngStale`) |
| 실패 시 재시도 1회 → error | Task 1 (테스트 4·5) |
| 이탈 직전 플러시 | Task 2 (`visibilitychange`) + Task 4 Step 5 |
| clean 상태 다이얼로그 없음 / error만 경고 | Task 3 Step 2 |
| 완료 조건 8개 | Task 5 |
