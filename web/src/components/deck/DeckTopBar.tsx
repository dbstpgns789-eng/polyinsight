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
  filename, editing, badge, onBadgeClick, onToggleMode, onExport, dirty,
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

      {/* 팩트 배지 */}
      <button onClick={onBadgeClick}
        className={`flex items-center gap-1.5 text-[11.5px] font-semibold rounded-full border px-3 py-1.5 shrink-0 ${TONE[badge.tone]}`}>
        <span aria-hidden="true">{badge.icon}</span>{badge.label}
      </button>

      {/* 편집 토글 */}
      <button onClick={onToggleMode}
        className={`text-[12.5px] font-semibold px-3 py-1.5 rounded-lg border shrink-0 ${
          editing ? 'border-forest-green text-forest-green' : 'border-deck-line text-ink-2'}`}>
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
