# 앱 크롬 + 뷰 (서브프로젝트 ①) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `/deck/[jobId]`를 클로드디자인식 전문 에디터 크롬으로 재구성 — 상단바 + 중앙(뷰=빅카드+썸네일 / 편집=캔버스) + 우측 탭 셸[AI 도우미·직접 편집·팩트 체크] + 적응형 팩트 배지 + Export 모달.

**Architecture:** 순수 프론트(백엔드 무변). 기존 컴포넌트(`DeckEditor`·`DeckElementPanel`·`DeckMediaPanel`·`DeckAIAssistant`)는 그대로 재사용하고 그 위에 크롬 컴포넌트를 신설한 뒤 `page.tsx`를 재조립한다. 뷰/편집은 **같은 크롬 셸**(상단바+우측)을 공유하고 중앙만 다르다.

**Tech Stack:** Next.js(React 19)+TS+Tailwind v4. 테스트=vitest(node, 순수 로직만)+ 라이브 브라우저 E2E(wmux `browser eval`, 로그인은 signup 자동로그인 우회 가능). jsdom 미도입.

> **상위 스펙:** `docs/superpowers/specs/2026-07-08-deck-editor-redesign-design.md` §4.1·§4.4·§4.5·§4.6·§6. 뷰=A안(한 장씩+썸네일, 사용자 승인). 팔레트=forest-green(`--accent` oklch 52% 0.15 163). 다크는 auth/CTA 한정(제약 2) — 크롬은 라이트.

---

## 하드 제약 (globals.css 검증 완료)

- **토큰만**(hex 금지). forest-green: `forest-green`/`forest-green-deep`/`forest-green-wash`. 텍스트 `ink`/`ink-2`/`ink-3`. 보더 `border`/`border-subtle`. 배경 `canvas`/`canvas-subtle`/`surface`/`bg-subtle`. amber `risk-medium`/`risk-medium-faint`/`risk-medium-border`. 그림자 `shadow-card`/`shadow-modal`/`shadow-topbar`.
- **전역 리셋은 `@layer base`만**(무계층 `*` 금지 — 2026-07-03 여백 죽음 버그). CSS 주석에 `p-*`/`m-*` 문자열 금지.
- 카드 내부 색(`--set-*`/저작HTML)·`DeckEditor` iframe·`CardRenderer` 불변.
- Export = **modal(React Portal), 소프트 경고**(하드블록 금지, web/CLAUDE.md §7).
- 다크 사이드바/툴바 금지 — 상단바·우측 패널 **라이트**.

## 파일 구조

| 파일 | 책임 | 태스크 |
|---|---|---|
| `web/src/lib/factBadge.ts` (신규) | `factBadgeState(verify)` 순수 함수 | 1 |
| `web/src/lib/factBadge.test.ts` (신규) | 위 vitest | 1 |
| `web/src/components/deck/DeckTopBar.tsx` (신규) | 상단바(로고·파일명·undo/redo·저장상태·팩트배지·편집토글·내보내기) | 2 |
| `web/src/components/deck/DeckFactPanel.tsx` (신규) | 팩트 체크 패널(스탯+클레임, 배지 강등·출처 금지) | 3 |
| `web/src/components/deck/DeckViewer.tsx` (신규) | 뷰: 빅카드+좌우 네비+썸네일 스트립+"이 카드 편집" | 4 |
| `web/src/components/deck/DeckRightTabs.tsx` (신규) | 우측 탭 셸[AI 도우미·직접 편집·팩트 체크] | 5 |
| `web/src/components/deck/DeckExportModal.tsx` (신규) | v3 Export 모달(Portal·소프트경고·exportDeck) | 6 |
| `web/src/app/deck/[jobId]/page.tsx` (수정) | 크롬 재조립 + 배선 | 7 |
| — | 라이브 E2E + tsc/vitest | 8 |

기존 `page.tsx`의 `GenerationTheater`(진행)·ERROR 화면·모든 ② 핸들러(propose/commit/revert/snapshot)·`DeckEditor` 마운트·잠금 오버레이는 **보존**한다.

---

## Task 1: factBadge 순수 함수 (팩트 배지 상태)

**Files:** Create `web/src/lib/factBadge.ts`, `web/src/lib/factBadge.test.ts`

팩트 배지는 확인필요(unverified)=0이면 초록 `✓ 수치 N 확인`, ≥1이면 주황 `⚠ N개 확인 필요`. 재검증 불가(원문 없음)면 중립. 순수 함수로 뽑아 테스트한다.

- [ ] **Step 1: 실패 테스트** — `web/src/lib/factBadge.test.ts`
```typescript
import { describe, it, expect } from 'vitest'
import { factBadgeState } from './factBadge'

describe('factBadgeState', () => {
  it('확인필요 0 → 초록 확인 배지', () => {
    expect(factBadgeState({ verified: 36, unverified: 0, claims: [] }, true))
      .toEqual({ tone: 'ok', label: '수치 36 확인', icon: '✓' })
  })
  it('확인필요 ≥1 → 주황 확인필요 배지', () => {
    expect(factBadgeState({ verified: 30, unverified: 2, claims: [] }, true))
      .toEqual({ tone: 'warn', label: '2개 확인 필요', icon: '⚠' })
  })
  it('재검증 불가(canReverify=false) → 중립', () => {
    expect(factBadgeState({ verified: 0, unverified: 0, claims: [] }, false))
      .toEqual({ tone: 'muted', label: '재검증 안 됨', icon: '—' })
  })
  it('verify 없음 → 중립', () => {
    expect(factBadgeState(null, true)).toEqual({ tone: 'muted', label: '검증 없음', icon: '—' })
  })
})
```

- [ ] **Step 2: 실패 확인** — `cd web && npx vitest run src/lib/factBadge.test.ts` → FAIL(import 없음)

- [ ] **Step 3: 구현** — `web/src/lib/factBadge.ts`
```typescript
// 팩트 배지 상태 파생 — 뷰·편집 상단바 공통. 출처/정합 주장 금지(헌법: 코드가 증명 못 하는 것 표기 X).
export interface VerifyLike { verified: number; unverified: number; claims: unknown[] }
export type BadgeTone = 'ok' | 'warn' | 'muted'
export interface BadgeState { tone: BadgeTone; label: string; icon: string }

export function factBadgeState(verify: VerifyLike | null | undefined, canReverify: boolean): BadgeState {
  if (!verify) return { tone: 'muted', label: '검증 없음', icon: '—' }
  if (!canReverify) return { tone: 'muted', label: '재검증 안 됨', icon: '—' }
  if (verify.unverified >= 1) return { tone: 'warn', label: `${verify.unverified}개 확인 필요`, icon: '⚠' }
  return { tone: 'ok', label: `수치 ${verify.verified} 확인`, icon: '✓' }
}
```

- [ ] **Step 4: 통과 확인** — `cd web && npx vitest run src/lib/factBadge.test.ts` → 4 PASS

- [ ] **Step 5: 커밋**
```bash
git add web/src/lib/factBadge.ts web/src/lib/factBadge.test.ts
git commit -m "[WEB] factBadgeState 순수 함수 — 적응형 팩트 배지 상태(순수·테스트) (스펙 ①)"
```

---

## Task 2: DeckTopBar — 상단바

**Files:** Create `web/src/components/deck/DeckTopBar.tsx`

뷰·편집 공통 상단바. 라이트(다크 금지). 로고 락업 · 파일명(mono) · [편집시 undo/redo·저장상태] · 팩트 배지(클릭→팩트탭) · 편집토글 · 내보내기.

- [ ] **Step 1: 구현** — `web/src/components/deck/DeckTopBar.tsx`
```tsx
'use client'

// /deck 상단바 (스펙 §4.1) — 뷰·편집 공통. 라이트 크롬(다크 금지, 제약 2). 토큰만.
import type { BadgeState } from '@/lib/factBadge'

interface Props {
  filename: string
  editing: boolean
  badge: BadgeState
  onBadgeClick: () => void
  onToggleMode: () => void
  onExport: () => void
  // 편집 전용
  canUndo?: boolean
  canRedo?: boolean
  onUndo?: () => void
  onRedo?: () => void
  saveLabel?: string   // '저장됨' | '저장 중…' | '저장'
}

const TONE: Record<BadgeState['tone'], string> = {
  ok: 'bg-forest-green-wash text-forest-green-deep border-forest-green/30',
  warn: 'bg-risk-medium-faint text-risk-medium border-risk-medium-border',
  muted: 'bg-bg-subtle text-ink-3 border-border',
}

export default function DeckTopBar({
  filename, editing, badge, onBadgeClick, onToggleMode, onExport,
  canUndo, canRedo, onUndo, onRedo, saveLabel,
}: Props) {
  return (
    <header className="flex items-center gap-3 px-5 h-14 bg-surface border-b border-border shrink-0">
      {/* 로고 락업 */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-7 h-7 rounded-lg grid place-items-center text-canvas text-[13px] font-bold"
             style={{ background: 'linear-gradient(150deg, var(--accent-bright), var(--accent))' }}>P</div>
        <span className="text-[14px] font-bold text-ink hidden sm:inline">PolyInsight</span>
      </div>
      <span className="w-px h-5 bg-border shrink-0" aria-hidden="true" />
      <span className="text-[12px] font-mono text-ink-3 truncate flex-1 min-w-0">{filename}</span>

      {/* 편집: undo/redo + 저장상태 */}
      {editing && (
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={onUndo} disabled={!canUndo} title="실행 취소 (Ctrl+Z)"
            className="w-8 h-8 rounded-lg border border-border text-ink-2 disabled:opacity-30">↶</button>
          <button onClick={onRedo} disabled={!canRedo} title="다시 실행 (Ctrl+Shift+Z)"
            className="w-8 h-8 rounded-lg border border-border text-ink-2 disabled:opacity-30">↷</button>
          <span className="text-[12px] text-ink-3 ml-1 min-w-[52px] text-center">{saveLabel}</span>
        </div>
      )}

      {/* 팩트 배지 */}
      <button onClick={onBadgeClick}
        className={`flex items-center gap-1.5 text-[11.5px] font-semibold rounded-full border px-3 py-1.5 shrink-0 ${TONE[badge.tone]}`}>
        <span aria-hidden="true">{badge.icon}</span>{badge.label}
      </button>

      {/* 편집 토글 */}
      <button onClick={onToggleMode}
        className={`text-[12.5px] font-semibold px-3 py-1.5 rounded-lg border shrink-0 ${
          editing ? 'border-forest-green text-forest-green' : 'border-border text-ink-2'}`}>
        {editing ? '편집 종료' : '✎ 편집'}
      </button>

      {/* 내보내기 */}
      <button onClick={onExport}
        className="text-[12.5px] font-semibold px-4 py-1.5 rounded-lg bg-forest-green text-canvas shrink-0">
        내보내기
      </button>
    </header>
  )
}
```

- [ ] **Step 2: 타입체크** — `cd web && npx tsc --noEmit` → no errors

- [ ] **Step 3: 커밋**
```bash
git add web/src/components/deck/DeckTopBar.tsx
git commit -m "[WEB] DeckTopBar — 뷰·편집 공통 상단바(로고·파일명·undo/저장·팩트배지·내보내기) (스펙 ①)"
```

---

## Task 3: DeckFactPanel — 팩트 체크 패널

**Files:** Create `web/src/components/deck/DeckFactPanel.tsx`

현 `page.tsx` 우측 "충실성 검증" 섹션을 컴포넌트로 추출·개명("팩트 체크"). 스펙 §4.5: 카피 강등, **출처 위치·"정확히 일치" 금지**. verify 데이터={value,context,verified}뿐.

- [ ] **Step 1: 구현** — `web/src/components/deck/DeckFactPanel.tsx`
```tsx
'use client'

// 팩트 체크 패널 (스펙 §4.5) — "충실성 검증·해자" 폐기. 출처 위치·정합 주장 금지(헌법).
interface VerifyClaim { value: string; context: string; verified: boolean }
interface VerifyData { verified: number; unverified: number; claims: VerifyClaim[] }

interface Props {
  verify: VerifyData | null | undefined
  canReverify: boolean
}

export default function DeckFactPanel({ verify, canReverify }: Props) {
  const flagged = verify?.claims.filter((c) => !c.verified) ?? []
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-[14px] font-bold text-ink">팩트 체크</h3>
        <p className="text-[11.5px] text-ink-3 mt-1 leading-snug">
          {canReverify
            ? '원문에 없는 수치는 따로 표시해요. 최종 판단은 직접 하세요.'
            : '이 덱은 원문이 없어 편집 시 재검증되지 않습니다. 재생성하면 복원됩니다.'}
        </p>
      </div>

      <div className="flex gap-2.5">
        <div className="flex-1 rounded-xl border border-border p-3 text-center">
          <div className="text-[20px] font-extrabold text-forest-green">{verify?.verified ?? 0}</div>
          <div className="text-[10.5px] text-ink-3 mt-0.5">원문에서 찾음</div>
        </div>
        <div className="flex-1 rounded-xl border border-border p-3 text-center">
          <div className="text-[20px] font-extrabold text-risk-medium">{verify?.unverified ?? 0}</div>
          <div className="text-[10.5px] text-ink-3 mt-0.5">확인 필요</div>
        </div>
      </div>

      {flagged.length > 0 ? (
        <div className="flex flex-col gap-2">
          <p className="text-[11.5px] font-semibold text-ink-2">⚠️ 원문에 없는 수치 — AI가 더한 맥락/예시인지 확인하세요:</p>
          <ul className="flex flex-col gap-2">
            {flagged.map((c, i) => (
              <li key={i} className="rounded-lg border border-risk-medium-border bg-risk-medium-faint p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] font-bold text-ink">{c.value}</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-canvas text-risk-medium shrink-0">원문에 없음</span>
                </div>
                <p className="text-[10.5px] text-ink-3 mt-1 leading-snug">…{c.context}…</p>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-[12px] text-ink-3">모든 수치가 원문에서 추적됐습니다.</p>
      )}
    </div>
  )
}
```

- [ ] **Step 2: tsc** — `cd web && npx tsc --noEmit`
- [ ] **Step 3: 커밋**
```bash
git add web/src/components/deck/DeckFactPanel.tsx
git commit -m "[WEB] DeckFactPanel — 팩트 체크 패널(카피 강등·출처 금지) (스펙 ①)"
```

---

## Task 4: DeckViewer — 뷰(빅카드+썸네일 A안)

**Files:** Create `web/src/components/deck/DeckViewer.tsx`

스펙 §4.4: 큰 카드 1장 + 좌우 네비 + 썸네일 스트립(클릭 전환·키보드 ←/→) + "이 카드 편집"(그 index로 편집 진입). PNG는 `getDeckCardUrl(jobId, n, ver)`. 미완/실패 → "그리는 중…"/재시도(빈 화면 금지).

- [ ] **Step 1: 구현** — `web/src/components/deck/DeckViewer.tsx`
```tsx
'use client'

// 뷰 — 한 장씩 + 썸네일 스트립 (스펙 §4.4, A안). PNG 피드 대체.
import { useEffect, useState } from 'react'
import { getDeckCardUrl } from '@/lib/api'

interface Props {
  jobId: string
  cardCount: number
  ver: number
  onEditCard: (index: number) => void   // index 0-based
}

export default function DeckViewer({ jobId, cardCount, ver, onEditCard }: Props) {
  const [idx, setIdx] = useState(0)
  const n = Math.max(cardCount, 1)
  const clamp = (i: number) => Math.max(0, Math.min(i, n - 1))

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') setIdx((i) => clamp(i - 1))
      else if (e.key === 'ArrowRight') setIdx((i) => clamp(i + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [n])

  if (cardCount <= 0) {
    return <div className="grid place-items-center h-full text-[13px] text-ink-3">카드가 아직 없습니다.</div>
  }

  return (
    <div className="flex flex-col items-center gap-4 py-6 h-full overflow-y-auto">
      <div className="relative flex items-center gap-3">
        {n > 1 && (
          <button onClick={() => setIdx((i) => clamp(i - 1))} disabled={idx <= 0} aria-label="이전 카드"
            className="w-9 h-9 rounded-full bg-surface border border-border text-ink-2 shadow-card disabled:opacity-30 shrink-0">‹</button>
        )}
        <div className="relative w-[min(46vh,320px)]" style={{ aspectRatio: '1080 / 1350' }}>
          <CardImg jobId={jobId} num={idx + 1} ver={ver} />
          <button onClick={() => onEditCard(idx)}
            className="absolute left-1/2 -translate-x-1/2 bottom-3 bg-surface/95 text-forest-green-deep text-[12px] font-bold rounded-lg px-3.5 py-1.5 shadow-modal">
            ✎ 이 카드 편집
          </button>
        </div>
        {n > 1 && (
          <button onClick={() => setIdx((i) => clamp(i + 1))} disabled={idx >= n - 1} aria-label="다음 카드"
            className="w-9 h-9 rounded-full bg-surface border border-border text-ink-2 shadow-card disabled:opacity-30 shrink-0">›</button>
        )}
      </div>

      {n > 1 && (
        <div className="flex gap-1.5 flex-wrap justify-center max-w-[80%]">
          {Array.from({ length: n }, (_, i) => (
            <button key={i} onClick={() => setIdx(i)} aria-label={`카드 ${i + 1}`}
              className={`w-8 rounded-md overflow-hidden border ${i === idx ? 'border-forest-green ring-1 ring-forest-green' : 'border-border'}`}
              style={{ aspectRatio: '1080 / 1350' }}>
              <CardImg jobId={jobId} num={i + 1} ver={ver} thumb />
            </button>
          ))}
        </div>
      )}
      <span className="text-[12px] tabular-nums text-ink-3">{idx + 1} / {n}</span>
    </div>
  )
}

// PNG 로드 — 미완/실패 시 "그리는 중…"(빈 화면 금지, 스펙 §4.4 엣지)
function CardImg({ jobId, num, ver, thumb }: { jobId: string; num: number; ver: number; thumb?: boolean }) {
  const [err, setErr] = useState(false)
  if (err) {
    return (
      <div className="w-full h-full grid place-items-center bg-bg-subtle text-ink-3"
        style={{ fontSize: thumb ? 7 : 12 }}>그리는 중…</div>
    )
  }
  return (
    <img src={getDeckCardUrl(jobId, num, ver || undefined)} alt={`카드 ${num}`}
      className="w-full h-full object-cover rounded-[inherit]"
      style={thumb ? undefined : { borderRadius: 12, boxShadow: 'var(--shadow-modal)' }}
      onError={() => setErr(true)} />
  )
}
```

- [ ] **Step 2: tsc** — `cd web && npx tsc --noEmit`
- [ ] **Step 3: 커밋**
```bash
git add web/src/components/deck/DeckViewer.tsx
git commit -m "[WEB] DeckViewer — 빅카드+썸네일 스트립+이 카드 편집(A안) (스펙 ①)"
```

---

## Task 5: DeckRightTabs — 우측 탭 셸

**Files:** Create `web/src/components/deck/DeckRightTabs.tsx`

편집 모드 우측: [AI 도우미][직접 편집][팩트 체크] 탭. 기본=AI 도우미. 팩트 배지 클릭 시 팩트 탭으로 전환(제어 탭). 각 탭 내용은 부모가 children/props로 주입 — 셸은 탭 전환만 담당.

- [ ] **Step 1: 구현** — `web/src/components/deck/DeckRightTabs.tsx`
```tsx
'use client'

// 편집 우측 탭 셸 (스펙 §4.1). 기본=AI 도우미. 탭은 부모 제어(팩트 배지→팩트 탭 점프).
import type { ReactNode } from 'react'

export type DeckTab = 'ai' | 'inspector' | 'fact'

interface Props {
  active: DeckTab
  onTab: (t: DeckTab) => void
  ai: ReactNode
  inspector: ReactNode
  fact: ReactNode
}

const TABS: { key: DeckTab; label: string }[] = [
  { key: 'ai', label: '✦ AI 도우미' },
  { key: 'inspector', label: '직접 편집' },
  { key: 'fact', label: '팩트 체크' },
]

export default function DeckRightTabs({ active, onTab, ai, inspector, fact }: Props) {
  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-1 p-1.5 border-b border-border shrink-0">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => onTab(t.key)}
            className={`flex-1 text-[12px] font-semibold py-1.5 rounded-md ${
              active === t.key ? 'bg-forest-green-wash text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-5">
        {active === 'ai' && ai}
        {active === 'inspector' && inspector}
        {active === 'fact' && fact}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: tsc** — `cd web && npx tsc --noEmit`
- [ ] **Step 3: 커밋**
```bash
git add web/src/components/deck/DeckRightTabs.tsx
git commit -m "[WEB] DeckRightTabs — 우측 탭 셸(AI 도우미·직접 편집·팩트 체크) (스펙 ①)"
```

---

## Task 6: DeckExportModal — v3 Export 모달

**Files:** Create `web/src/components/deck/DeckExportModal.tsx`

스펙 §4.6: React Portal, **소프트 경고**(unverified≥1 경고 표시하되 내보내기 가능, 하드블록 금지). props 구동(legacy `ExportModal`의 uiStore/Card.fields 결합 제거). `exportDeck(jobId)`→`getExportDownloadUrl`.

- [ ] **Step 1: 구현** — `web/src/components/deck/DeckExportModal.tsx`
```tsx
'use client'

// v3 덱 Export 모달 (스펙 §4.6) — Portal, 소프트 경고(하드블록 금지, web/CLAUDE.md §7).
// legacy components/export/ExportModal(uiStore·Card.fields.risk_level 결합) 대체.
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { exportDeck, getExportDownloadUrl } from '@/lib/api'

interface Props {
  jobId: string
  filename: string
  cardCount: number
  unverified: number
  onClose: () => void
}

export default function DeckExportModal({ jobId, filename, cardCount, unverified, onClose }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleExport = async () => {
    setBusy(true); setError(null)
    try {
      const r = await exportDeck(jobId)
      window.location.href = getExportDownloadUrl(r.data.exportId)
      onClose()
    } catch {
      setError('내보내기에 실패했어요. 잠시 후 다시 시도해 주세요.'); setBusy(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-[400px] bg-surface rounded-2xl shadow-modal p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-[16px] font-bold text-ink">내보내기</h2>
        <p className="text-[12px] text-ink-3 mt-1 truncate">{filename}</p>

        <div className="mt-4 rounded-xl border border-border p-3 flex items-center justify-between">
          <span className="text-[12.5px] text-ink-2">카드 {cardCount}장 · PNG ZIP</span>
          <span className="text-[11px] text-ink-3">1080×1350</span>
        </div>

        {unverified >= 1 && (
          <div className="mt-3 rounded-xl border border-risk-medium-border bg-risk-medium-faint p-3">
            <p className="text-[11.5px] text-risk-medium font-semibold">⚠ 확인이 필요한 수치가 {unverified}개 있어요.</p>
            <p className="text-[11px] text-ink-3 mt-1 leading-snug">그래도 내보낼 수 있어요 — 최종 판단은 직접 하세요.</p>
          </div>
        )}

        {error && <p className="mt-3 text-[11.5px] text-risk-medium">{error}</p>}

        <div className="mt-5 flex gap-2">
          <button onClick={onClose} disabled={busy}
            className="flex-1 h-10 rounded-lg border border-border text-ink-2 text-[13px] font-semibold disabled:opacity-40">취소</button>
          <button onClick={handleExport} disabled={busy}
            className="flex-1 h-10 rounded-lg bg-forest-green text-canvas text-[13px] font-semibold disabled:opacity-40">
            {busy ? '내보내는 중…' : 'ZIP 내보내기'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
```

- [ ] **Step 2: tsc** — `cd web && npx tsc --noEmit`
- [ ] **Step 3: 커밋**
```bash
git add web/src/components/deck/DeckExportModal.tsx
git commit -m "[WEB] DeckExportModal — v3 Portal 소프트경고 내보내기(legacy 결합 제거) (스펙 ①)"
```

---

## Task 7: page.tsx 재조립

**Files:** Modify `web/src/app/deck/[jobId]/page.tsx`

크롬을 조립: 상단 `DeckTopBar` + 중앙(뷰=`DeckViewer` / 편집=기존 캔버스+잠금오버레이) + 우측(뷰=`DeckFactPanel` / 편집=`DeckRightTabs`) + `DeckExportModal`. **모든 ② 상태·핸들러·GenerationTheater·ERROR 화면 보존.** 인라인 상단 툴바(현 285-331)는 `DeckTopBar`로 대체.

- [ ] **Step 1: import 추가** (기존 import 블록에)
```typescript
import DeckTopBar from '@/components/deck/DeckTopBar'
import DeckViewer from '@/components/deck/DeckViewer'
import DeckRightTabs, { type DeckTab } from '@/components/deck/DeckRightTabs'
import DeckFactPanel from '@/components/deck/DeckFactPanel'
import DeckExportModal from '@/components/deck/DeckExportModal'
import { factBadgeState } from '@/lib/factBadge'
```

- [ ] **Step 2: 새 상태 추가** (다른 useState 옆)
```typescript
  const [rightTab, setRightTab] = useState<DeckTab>('ai')
  const [showExport, setShowExport] = useState(false)
```

- [ ] **Step 3: 뷰→편집 진입 헬퍼** (핸들러 옆). "이 카드 편집" = 그 index로 편집 진입.
```typescript
  const enterEditAt = useCallback((index: number) => {
    setMode('edit')
    // 마운트 후 해당 카드로 이동(EDITOR_READY 뒤 setPage 반영 위해 다음 틱)
    setTimeout(() => editorRef.current?.setPage(index), 0)
  }, [])
```

- [ ] **Step 4: 배지 클릭 = 편집 시 팩트 탭, 뷰 시 무동작(패널 이미 노출)**
```typescript
  const onBadgeClick = useCallback(() => { if (mode === 'edit') setRightTab('fact') }, [mode])
```

- [ ] **Step 5: DONE 렌더 블록(현 281-400의 `return (...)`)을 아래로 교체.**
   기존 `handleExport`(직접 내보내기)는 유지하되 상단바 내보내기는 모달을 연다. `handleExport`가 다른 곳에서 안 쓰이면 제거(orphan). `GenerationTheater`/ERROR 분기(254-274)와 그 위 `v`/`flagged`/`editing`/`cardNums` 파생은 보존하되 `cardNums`는 DeckViewer가 대체하므로 미사용 시 제거.
```tsx
  const v = deck.verify
  const editing = mode === 'edit'
  const badge = factBadgeState(v, deck.canReverify !== false)
  const saveLabel = saving ? '저장 중…' : dirty ? '저장' : '저장됨'

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-canvas-subtle" style={{ wordBreak: 'keep-all' }}>
      <DeckTopBar
        filename={deck.filename ?? '덱'}
        editing={editing}
        badge={badge}
        onBadgeClick={onBadgeClick}
        onToggleMode={toggleMode}
        onExport={() => setShowExport(true)}
        canUndo={history.canUndo}
        canRedo={history.canRedo}
        onUndo={() => editorRef.current?.undo()}
        onRedo={() => editorRef.current?.redo()}
        saveLabel={saveLabel}
      />

      {editWarnings.length > 0 && (
        <div className="mx-auto mt-3 w-full max-w-[460px] rounded-lg border border-risk-medium-border bg-risk-medium-faint p-3 shrink-0">
          {editWarnings.map((w, i) => <p key={i} className="text-[11px] text-risk-medium leading-snug">{w}</p>)}
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {/* 중앙 */}
        <main className="flex-1 min-w-0 overflow-hidden">
          {editing ? (
            <div className="h-full overflow-y-auto flex flex-col items-center py-6 gap-3">
              {page.count > 1 && (
                <div className="flex items-center justify-center gap-3 select-none">
                  <button onClick={() => editorRef.current?.setPage(page.index - 1)} disabled={page.index <= 0}
                    aria-label="이전 카드" className="w-9 h-9 rounded-full border border-border text-ink-2 disabled:opacity-30">‹</button>
                  <span className="text-[13px] tabular-nums text-ink-2 min-w-[52px] text-center">{page.index + 1} / {page.count}</span>
                  <button onClick={() => editorRef.current?.setPage(page.index + 1)} disabled={page.index >= page.count - 1}
                    aria-label="다음 카드" className="w-9 h-9 rounded-full border border-border text-ink-2 disabled:opacity-30">›</button>
                </div>
              )}
              <div className="relative w-full max-w-[460px]">
                <DeckEditor
                  ref={editorRef}
                  html={deck.html as string}
                  mode={mode}
                  onSelected={setSelected}
                  onDeselected={() => setSelected(null)}
                  onDirty={() => { setDirty(true); setPending(null) }}
                  onHistory={setHistory}
                  onPage={setPage}
                />
                {(proposing || !!pending) && (
                  <div className="absolute inset-0 z-10 cursor-not-allowed" aria-hidden="true"
                    title={proposing ? 'AI가 제안 중…' : 'AI 제안 확인 중 — 적용/취소 후 편집하세요'} />
                )}
              </div>
            </div>
          ) : (
            <DeckViewer jobId={jobId} cardCount={deck.cardCount || 7} ver={ver} onEditCard={enterEditAt} />
          )}
        </main>

        {/* 우측 */}
        <aside className="w-[360px] shrink-0 border-l border-border bg-surface min-h-0">
          {editing ? (
            <DeckRightTabs
              active={rightTab}
              onTab={setRightTab}
              ai={
                <DeckAIAssistant
                  selected={selected}
                  proposing={proposing}
                  pending={!!pending}
                  committing={committing}
                  beforeText={pending?.beforeText ?? selected?.quotedText ?? null}
                  afterText={pending?.afterText ?? null}
                  onPropose={handlePropose}
                  onCommit={handleCommit}
                  onDiscard={handleDiscard}
                  canRevert={snapshots.length > 0}
                  reverting={reverting}
                  onRevert={handleRevert}
                />
              }
              inspector={
                <div className="flex flex-col gap-5">
                  <DeckMediaPanel jobId={jobId} onInsert={(p) => { editorRef.current?.insertImage(p); setDirty(true) }} />
                  <div className="h-px bg-border" />
                  <DeckElementPanel
                    selected={selected}
                    onStyle={(prop, value) => editorRef.current?.applyStyle(prop, value)}
                    onDelete={() => editorRef.current?.deleteElement()}
                    onMove={(dir) => editorRef.current?.moveElement(dir)}
                    onRevertFlow={() => editorRef.current?.revertFlow()}
                    onAlign={(axis) => editorRef.current?.align(axis)}
                    onDistribute={(axis) => editorRef.current?.distribute(axis)}
                    onSetRect={(r) => editorRef.current?.setRect(r)}
                  />
                </div>
              }
              fact={<DeckFactPanel verify={v} canReverify={deck.canReverify !== false} />}
            />
          ) : (
            <div className="p-5 overflow-y-auto h-full">
              <DeckFactPanel verify={v} canReverify={deck.canReverify !== false} />
            </div>
          )}
        </aside>
      </div>

      {showExport && (
        <DeckExportModal
          jobId={jobId}
          filename={deck.filename ?? '덱'}
          cardCount={deck.cardCount || 7}
          unverified={v?.unverified ?? 0}
          onClose={() => setShowExport(false)}
        />
      )}
    </div>
  )
```

- [ ] **Step 6: orphan 제거** — `handleExport`(구 인라인 export, 이제 모달이 대체)·`exporting` 상태·`cardNums`·`flagged`(DeckFactPanel로 이동)가 미사용이면 제거. `getDeckCardUrl` import는 DeckViewer가 쓰므로 page에서 미사용 시 제거. tsc가 orphan을 알려줌.

- [ ] **Step 7: 검증**
```
cd web && npx tsc --noEmit    # no errors (orphan 참조 없어야)
cd web && npm run lint         # page.tsx 신규 에러 없음(기존 경고 OK)
```

- [ ] **Step 8: 커밋**
```bash
git add web/src/app/deck/[jobId]/page.tsx
git commit -m "[WEB] deck 페이지 크롬 재조립 — 상단바+뷰어+우측 탭셸+Export 모달 (스펙 ①)"
```

---

## Task 8: 라이브 E2E + 회귀

**Files:** (없음)

iframe·컴포넌트는 node 유닛 불가 → 실브라우저. 로그인 벽은 signup 자동로그인 + DB 시드로 우회(②에서 검증된 방법). 무비용.

- [ ] **Step 1: 프론트 재컴파일** — deck 페이지 대규모 변경 → `web/.next` stale 가능성. 필요 시 `.next` 삭제 후 재기동(web/CLAUDE.md).
- [ ] **Step 2: 라이브 스모크(wmux `browser eval`)** — 테스트 계정 signup(자동로그인) → 기존 덱 html 시드(job='e2e-chrome') → `/deck/e2e-chrome`:
  - **뷰**: 상단바(로고·파일명·팩트 배지) 렌더 · DeckViewer 빅카드+썸네일 스트립 · "이 카드 편집" 클릭 → 편집 모드 그 index 진입.
  - **편집**: 상단바 undo/redo·저장상태 · 우측 탭[AI 도우미·직접 편집·팩트 체크] 전환 동작 · 팩트 배지 클릭 → 팩트 탭 점프.
  - **Export**: 내보내기 → 모달(Portal) 열림 · unverified≥1이면 경고 표시(하드블록 없음) · 취소/ESC 닫힘.
  - 시드 데이터·테스트 유저 **정리**.
- [ ] **Step 3: 회귀** — `cd web && npx vitest run`(factBadge 포함 전부) · `npx tsc --noEmit` · 백엔드 무변 확인(`git status` 백엔드 파일 없음).
- [ ] **Step 4: 결과 보고** (커밋 불요).

---

## Self-Review (스펙 §4.1·§4.4·§4.5·§4.6 커버리지)

| 스펙 요구 | 태스크 |
|---|---|
| 상단바(로고·파일명·undo/redo·저장·내보내기) | 2·7 |
| 좌 도구(축소) — 도형/차트 defer, 이미지=직접편집 탭 | 7(inspector 탭에 DeckMediaPanel) |
| 우 패널 탭[AI 도우미·직접 편집·팩트 체크] | 5·7 |
| 뷰 A안: 빅카드+썸네일+이 카드 편집(index 진입) | 4·7(enterEditAt) |
| 팩트 배지 적응형(초록/주황)·클릭→상세 | 1·2·7(onBadgeClick) |
| 팩트 체크 카피 강등·출처 금지 | 3 |
| Export modal·소프트경고·하드블록 없음 | 6·7 |
| forest-green·라이트 크롬·@layer base·토큰만 | 전 태스크(TONE/토큰 클래스) |
| GenerationTheater·ERROR·② 핸들러 보존 | 7 |

**Placeholder scan:** 전 컴포넌트 실제 코드. ✅ **타입 일관성:** `BadgeState`(factBadge↔TopBar), `DeckTab`(Tabs↔page), `VerifyData` 재사용. ✅ **스코프:** ①=크롬만. ③(인스펙터 시각 개편)·④(자동저장 분리)는 별도. ✅

---

**한 줄 요약**: 기존 편집 컴포넌트를 그대로 얹은 채 **상단바+빅카드뷰+우측 탭셸+적응형 팩트배지+Export 모달**로 `/deck`을 전문 에디터 크롬으로 재조립. 백엔드 무변, forest-green 라이트 크롬.
