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
  onSave?: () => void
  saveDisabled?: boolean
}

const TONE: Record<BadgeState['tone'], string> = {
  ok: 'bg-forest-green-wash text-forest-green-deep border-forest-green/30',
  warn: 'bg-risk-medium-faint text-risk-medium border-risk-medium-border',
  muted: 'bg-bg-subtle text-ink-3 border-border',
}

export default function DeckTopBar({
  filename, editing, badge, onBadgeClick, onToggleMode, onExport,
  canUndo, canRedo, onUndo, onRedo, saveLabel, onSave, saveDisabled,
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
          <button onClick={onUndo} disabled={!canUndo} title="실행 취소 (Ctrl+Z)" aria-label="실행 취소"
            className="w-8 h-8 rounded-lg border border-border text-ink-2 disabled:opacity-30">↶</button>
          <button onClick={onRedo} disabled={!canRedo} title="다시 실행 (Ctrl+Shift+Z)" aria-label="다시 실행"
            className="w-8 h-8 rounded-lg border border-border text-ink-2 disabled:opacity-30">↷</button>
          <button onClick={onSave} disabled={saveDisabled}
            className={`text-[12px] font-semibold ml-1 px-3 py-1.5 rounded-lg border ${
              saveDisabled ? 'border-transparent text-ink-3' : 'border-forest-green text-forest-green'}`}>
            {saveLabel}
          </button>
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
