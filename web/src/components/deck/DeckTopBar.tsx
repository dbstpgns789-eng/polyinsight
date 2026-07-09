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
  onToggleMode: () => void
  onExport: () => void
  dirty?: boolean         // 편집 미저장 — 나가기 전 확인용
  // 편집 전용
  canUndo?: boolean
  canRedo?: boolean
  onUndo?: () => void
  onRedo?: () => void
  saveLabel?: string      // '저장됨' | '저장 중…' | '저장'
  savedAt?: string        // 마지막 저장 시각 'hh:mm'
  onSave?: () => void
  saveDisabled?: boolean
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

export default function DeckTopBar({
  filename, editing, verified, unverified, onBadgeClick, factOpen, onToggleMode, onExport, dirty,
  canUndo, canRedo, onUndo, onRedo, saveLabel, savedAt, onSave, saveDisabled,
}: Props) {
  const guardLeave = (e: MouseEvent) => {
    if (editing && dirty && !window.confirm('저장하지 않은 편집이 있어요. 나가면 사라집니다. 나가시겠어요?')) e.preventDefault()
  }
  const showMoat = verified != null && unverified != null
  const total = (verified ?? 0) + (unverified ?? 0)

  return (
    <header className="flex items-center gap-2.5 px-4 h-14 bg-surface border-b border-deck-line shrink-0">
      {/* ① 정체성·탈출 — 브랜드=홈 + ‹대시보드  ·  ② 위치 — 덱 제목 */}
      <Link href="/dashboard" onClick={guardLeave} title="PolyInsight 홈" className="flex items-center gap-2 shrink-0 rounded-lg">
        <div className="w-7 h-7 rounded-lg grid place-items-center text-canvas text-[13px] font-bold"
             style={{ background: 'linear-gradient(150deg, var(--accent-bright), var(--accent))' }}>P</div>
        <span className="text-[14px] font-bold text-ink hidden md:inline">PolyInsight</span>
      </Link>
      <nav aria-label="위치" className="flex items-center gap-2 min-w-0 flex-1">
        <Link href="/dashboard" onClick={guardLeave}
          className="text-[13px] font-semibold text-ink-3 hover:text-ink-2 shrink-0 transition-colors flex items-center gap-1">
          <span aria-hidden="true">‹</span>대시보드</Link>
        <span className="text-ink-3/70 shrink-0 text-[13px]" aria-hidden="true">/</span>
        <span className="text-[13.5px] font-semibold text-ink truncate min-w-0" title={filename}>{filename}</span>
      </nav>

      {/* ③ 상태·해자 — 진행 링 + N/M 검증 · K 검토. 클릭=팩트체크 열기 */}
      {showMoat && (
        <button onClick={onBadgeClick} aria-expanded={!!factOpen} aria-haspopup="dialog" aria-controls="fact-drawer"
          title="팩트 체크 — 수치 원문 대조 상세"
          className="group flex items-center gap-2 rounded-full border border-deck-line bg-surface pl-1.5 pr-2.5 py-1 shrink-0 hover:bg-bg-subtle transition-colors">
          <MoatRing verified={verified!} total={total} />
          <span className="text-[12px] font-semibold text-ink"><b className="tabular-nums">{verified}/{total}</b> 검증</span>
          {(unverified ?? 0) > 0 && (
            <span className="text-[12px] font-semibold text-risk-medium tabular-nums border-l border-deck-line pl-2">{unverified} 검토</span>
          )}
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
            className={`text-ink-3 opacity-60 transition-transform ${factOpen ? 'rotate-180' : ''}`}><path d="m6 9 6 6 6-6" /></svg>
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

      {/* 편집 전용 — undo/redo + 저장 상태·시각 */}
      {editing && (
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={onUndo} disabled={!canUndo} title="실행 취소 (Ctrl+Z)" aria-label="실행 취소"
            className="w-8 h-8 rounded-lg border border-deck-line text-ink-2 disabled:opacity-30 hover:text-ink transition-colors">↶</button>
          <button onClick={onRedo} disabled={!canRedo} title="다시 실행 (Ctrl+Shift+Z)" aria-label="다시 실행"
            className="w-8 h-8 rounded-lg border border-deck-line text-ink-2 disabled:opacity-30 hover:text-ink transition-colors">↷</button>
          <button onClick={onSave} disabled={saveDisabled}
            className={`text-[12px] font-semibold ml-1 px-2.5 py-1.5 rounded-lg ${
              saveDisabled ? 'text-ink-3' : 'text-forest-green-deep hover:bg-forest-green-wash'} transition-colors`}>
            {saveLabel}{saveLabel === '저장됨' && savedAt ? ` · ${savedAt}` : ''}
          </button>
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
