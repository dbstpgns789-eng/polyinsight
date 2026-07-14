'use client'

// /deck 상단바 — 6요소(정체성·탈출 / 위치 / 상태·해자 / 모드 / 행동 / 계정). 라이트 크롬. 토큰만.
import Link from 'next/link'
import type { MouseEvent } from 'react'
import DeckAccountMenu from './DeckAccountMenu'

interface Props {
  filename: string
  editing: boolean
  verified?: number       // 검증된 수치
  unverified?: number     // 검토 필요 수치
  onBadgeClick: () => void
  factOpen?: boolean      // 팩트체크 드로어 열림 — disclosure 상태
  factInline?: boolean    // 팩트가 화면에 상시 노출(뷰 3패널) → 배지는 상태만(디스클로저 아님)
  onToggleMode: () => void
  onExport: () => void
  // 편집 전용
  canUndo?: boolean
  canRedo?: boolean
  onUndo?: () => void
  onRedo?: () => void
  saveStatus?: 'clean' | 'dirty' | 'saving' | 'error'   // 자동저장 상태(편집 모드에서만 의미)
  savedAt?: string        // 마지막 저장 시각 'hh:mm'
  onRetrySave?: () => void   // error 상태에서 재시도
}

// ③ 상태·해자 진행 링 — 검증/전체 비율
function MoatRing({ verified, total }: { verified: number; total: number }) {
  const r = 8, circ = 2 * Math.PI * r
  const frac = total > 0 ? Math.min(verified / total, 1) : 0
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" className="shrink-0" aria-hidden="true">
      <circle cx="10" cy="10" r={r} fill="none" stroke="var(--deck-line)" strokeWidth="2.4" />
      <circle cx="10" cy="10" r={r} fill="none" stroke="var(--accent)" strokeWidth="2.4"
        strokeDasharray={circ} strokeDashoffset={circ * (1 - frac)} strokeLinecap="round" transform="rotate(-90 10 10)" />
    </svg>
  )
}

// ② 저장 상태 — "나가도 안전하다"를 형태로 증명한다(수동 저장 버튼을 대체)
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
  if (status === 'saving') return <span className="shrink-0 text-[12px] font-semibold text-ink-3">저장 중…</span>
  if (status === 'dirty') return <span className="shrink-0 text-[12px] font-semibold text-ink-3">변경사항 있음</span>
  return (
    <span className="flex items-center gap-1.5 shrink-0 text-[12px] font-semibold text-forest-green-deep">
      <span className="w-1.5 h-1.5 rounded-full bg-forest-green" aria-hidden="true" />
      모든 변경 저장됨{savedAt ? ` · ${savedAt}` : ''}
    </span>
  )
}

export default function DeckTopBar({
  filename, editing, verified, unverified, onBadgeClick, factOpen, factInline, onToggleMode, onExport,
  canUndo, canRedo, onUndo, onRedo, saveStatus, savedAt, onRetrySave,
}: Props) {
  // 자동저장이 도는 한 나가기는 안전한 행동이다 — 저장이 **실패한** 상태에서만 막는다.
  const guardLeave = (e: MouseEvent) => {
    if (editing && saveStatus === 'error' &&
        !window.confirm('마지막 편집이 저장되지 않았어요. 나가면 사라집니다. 나가시겠어요?')) {
      e.preventDefault()
    }
  }
  const showMoat = verified != null && unverified != null
  const total = (verified ?? 0) + (unverified ?? 0)

  return (
    <header className="flex items-center gap-2.5 px-4 h-14 bg-surface border-b border-deck-line shrink-0">
      {/* ① 탈출 — 상단바 **첫 요소**, 버튼 형태(클릭 가능함이 형태로 보이게).
          로고를 뺀 자리다: 이미 앱 안이라 브랜드 재확인보다 나가는 길이 중요하다. */}
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

      {/* ③ 상태·해자 — 진행 링 + N/M 검증 · K 검토. 편집=클릭 시 드로어 / 뷰=상태만(팩트 우측 상시) */}
      {showMoat && (
        <button onClick={onBadgeClick}
          {...(factInline ? {} : { 'aria-expanded': !!factOpen, 'aria-haspopup': 'dialog' as const, 'aria-controls': 'fact-drawer' })}
          title={factInline ? '수치 원문 대조 상태' : '팩트 체크 — 수치 원문 대조 상세'}
          className={`group flex items-center gap-2 rounded-full border border-deck-line bg-surface pl-1.5 pr-2.5 py-1 shrink-0 transition-colors ${factInline ? 'cursor-default' : 'hover:bg-bg-subtle'}`}>
          <MoatRing verified={verified!} total={total} />
          <span className="text-[12px] font-semibold text-ink"><b className="tabular-nums">{verified}/{total}</b> 검증</span>
          {(unverified ?? 0) > 0 && (
            <span className="text-[12px] font-semibold text-risk-medium tabular-nums border-l border-deck-line pl-2">{unverified} 검토</span>
          )}
          {!factInline && (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"
              strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
              className={`text-ink-3 opacity-60 transition-transform ${factOpen ? 'rotate-180' : ''}`}><path d="m6 9 6 6 6-6" /></svg>
          )}
        </button>
      )}

      {/* ④ 모드 — 뷰어│편집 세그먼트 토글 */}
      <div role="group" aria-label="모드" className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line shrink-0">
        <button onClick={() => { if (editing) onToggleMode() }} aria-pressed={!editing}
          className={`text-[12.5px] font-semibold px-3 py-1 rounded-md transition-colors ${
            !editing ? 'bg-surface text-ink shadow-card' : 'text-ink-3 hover:text-ink-2'}`}>뷰어</button>
        <button onClick={() => { if (!editing) onToggleMode() }} aria-pressed={editing}
          className={`text-[12.5px] font-semibold px-3 py-1 rounded-md transition-colors ${
            editing ? 'bg-surface text-forest-green-deep shadow-card' : 'text-ink-3 hover:text-ink-2'}`}>편집</button>
      </div>

      {/* 편집 전용 — undo/redo. (수동 저장 버튼은 자동저장 도입으로 제거됨 — 상태 표시가 대체) */}
      {editing && (
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={onUndo} disabled={!canUndo} title="실행 취소 (Ctrl+Z)" aria-label="실행 취소"
            className="w-8 h-8 rounded-lg border border-deck-line text-ink-2 disabled:opacity-30 hover:text-ink transition-colors">↶</button>
          <button onClick={onRedo} disabled={!canRedo} title="다시 실행 (Ctrl+Shift+Z)" aria-label="다시 실행"
            className="w-8 h-8 rounded-lg border border-deck-line text-ink-2 disabled:opacity-30 hover:text-ink transition-colors">↷</button>
        </div>
      )}

      {/* ⑤ 행동 — 내보내기(1전압) */}
      <button onClick={onExport}
        className="text-[12.5px] font-semibold px-4 py-1.5 rounded-lg bg-forest-green text-canvas shrink-0 hover:bg-forest-green-deep transition-colors">
        내보내기
      </button>

      {/* ⑥ 계정 */}
      <DeckAccountMenu />
    </header>
  )
}
