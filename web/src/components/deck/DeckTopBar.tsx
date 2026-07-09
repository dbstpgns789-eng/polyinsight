'use client'

// /deck 상단바 (스펙 §4.1) — 뷰·편집 공통. 라이트 크롬(다크 금지, 제약 2). 토큰만.
import Link from 'next/link'
import type { MouseEvent } from 'react'
import type { BadgeState } from '@/lib/factBadge'

interface Props {
  filename: string
  editing: boolean
  badge: BadgeState
  onBadgeClick: () => void
  factOpen?: boolean    // 팩트체크 드로어 열림 — 배지 disclosure 상태
  onToggleMode: () => void
  onExport: () => void
  dirty?: boolean       // 편집 미저장 — 나가기 전 확인용
  // 편집 전용
  canUndo?: boolean
  canRedo?: boolean
  onUndo?: () => void
  onRedo?: () => void
  saveLabel?: string   // '저장됨' | '저장 중…' | '저장'
  onSave?: () => void
  saveDisabled?: boolean
}

const TONE: Record<BadgeState['tone'], string> = {
  ok: 'bg-forest-green-wash text-forest-green-deep border-forest-green/30',
  warn: 'bg-risk-medium-faint text-risk-medium border-risk-medium-border',
  muted: 'bg-bg-subtle text-ink-3 border-deck-line',
}

export default function DeckTopBar({
  filename, editing, badge, onBadgeClick, factOpen, onToggleMode, onExport, dirty,
  canUndo, canRedo, onUndo, onRedo, saveLabel, onSave, saveDisabled,
}: Props) {
  // 편집 미저장 상태로 이탈 시 확인(브랜드·브레드크럼 링크 공유)
  const guardLeave = (e: MouseEvent) => {
    if (editing && dirty && !window.confirm('저장하지 않은 편집이 있어요. 나가면 사라집니다. 나가시겠어요?')) e.preventDefault()
  }
  return (
    <header className="flex items-center gap-2.5 px-4 h-14 bg-surface border-b border-deck-line shrink-0">
      {/* 브랜드 = 홈(대시보드) */}
      <Link href="/dashboard" onClick={guardLeave} title="PolyInsight 홈" className="shrink-0 rounded-lg">
        <div className="w-7 h-7 rounded-lg grid place-items-center text-canvas text-[13px] font-bold"
             style={{ background: 'linear-gradient(150deg, var(--accent-bright), var(--accent))' }}>P</div>
      </Link>

      {/* 브레드크럼 = 위치 + 탈출구. '대시보드'가 라벨된 명확한 나가기, › 현재 덱이 정체성 */}
      <nav aria-label="위치" className="flex items-center gap-2 min-w-0 flex-1">
        <Link href="/dashboard" onClick={guardLeave}
          className="text-[13px] font-semibold text-ink-3 hover:text-ink-2 shrink-0 transition-colors">대시보드</Link>
        <span className="text-ink-3 shrink-0 text-[13px]" aria-hidden="true">›</span>
        <span className="text-[13.5px] font-semibold text-ink truncate min-w-0" title={filename}>{filename}</span>
      </nav>

      {/* 편집: undo/redo + 저장상태 */}
      {editing && (
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={onUndo} disabled={!canUndo} title="실행 취소 (Ctrl+Z)" aria-label="실행 취소"
            className="w-8 h-8 rounded-lg border border-deck-line text-ink-2 disabled:opacity-30">↶</button>
          <button onClick={onRedo} disabled={!canRedo} title="다시 실행 (Ctrl+Shift+Z)" aria-label="다시 실행"
            className="w-8 h-8 rounded-lg border border-deck-line text-ink-2 disabled:opacity-30">↷</button>
          <button onClick={onSave} disabled={saveDisabled}
            className={`text-[12px] font-semibold ml-1 px-3 py-1.5 rounded-lg border ${
              saveDisabled ? 'border-transparent text-ink-3' : 'border-forest-green text-forest-green'}`}>
            {saveLabel}
          </button>
        </div>
      )}

      {/* 팩트 배지 = 팩트체크 드로어 disclosure 트리거(뷰·편집 공통) */}
      <button onClick={onBadgeClick}
        aria-expanded={!!factOpen} aria-haspopup="dialog" aria-controls="fact-drawer"
        title="팩트 체크 열기 — 수치 원문 대조 상세"
        className={`group flex items-center gap-1.5 text-[11.5px] font-semibold rounded-full border pl-3 pr-2 py-1.5 shrink-0 cursor-pointer hover:brightness-[0.98] transition ${TONE[badge.tone]}`}>
        <span aria-hidden="true">{badge.icon}</span>{badge.label}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"
          strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
          className={`opacity-60 transition-transform ${factOpen ? 'rotate-180' : ''}`}><path d="m6 9 6 6 6-6" /></svg>
      </button>

      {/* 보기│편집 세그먼트 모드 토글 — 양방향 상태를 명시(블랙박스 벤치 반영) */}
      <div role="group" aria-label="모드" className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line shrink-0">
        <button onClick={() => { if (editing) onToggleMode() }} aria-pressed={!editing}
          className={`text-[12.5px] font-semibold px-3 py-1 rounded-md transition-colors ${
            !editing ? 'bg-surface text-ink shadow-card' : 'text-ink-3 hover:text-ink-2'}`}>보기</button>
        <button onClick={() => { if (!editing) onToggleMode() }} aria-pressed={editing}
          className={`text-[12.5px] font-semibold px-3 py-1 rounded-md transition-colors ${
            editing ? 'bg-surface text-forest-green-deep shadow-card' : 'text-ink-3 hover:text-ink-2'}`}>✎ 편집</button>
      </div>

      {/* 내보내기 */}
      <button onClick={onExport}
        className="text-[12.5px] font-semibold px-4 py-1.5 rounded-lg bg-forest-green text-canvas shrink-0">
        내보내기
      </button>
    </header>
  )
}
