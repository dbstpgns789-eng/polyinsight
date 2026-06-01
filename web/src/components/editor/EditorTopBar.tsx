'use client'

import { useRouter } from 'next/navigation'

type SaveState = 'saving' | 'saved' | 'idle' | 'error'

interface Props {
  filename?: string
  saveState?: SaveState
  onSaveNow?: () => void
}

function BetaLocked({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative group cursor-not-allowed inline-flex items-center">
      <div className="opacity-40 pointer-events-none inline-flex items-center">{children}</div>
      <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2.5 py-1.5 bg-ink text-surface text-[11px] font-medium rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-md">
        베타 서비스에서 제공하지 않는 기능입니다
      </div>
    </div>
  )
}

// ── 아이콘 (Stitch 원본 SVG 그대로) ────────────────────────

function IconDoc() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 3h9l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
      <path d="M14 3v5h5" />
      <path d="M8 13h8" />
      <path d="M8 17h6" />
    </svg>
  )
}

function IconEdit() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3Z" />
    </svg>
  )
}

function IconChevron() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6l6 6-6 6" />
    </svg>
  )
}

function IconCloud() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.5 19a4.5 4.5 0 1 0-1.5-8.74A6 6 0 0 0 4 12.5 3.5 3.5 0 0 0 7.5 19h10Z" />
    </svg>
  )
}

function IconGear() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
    </svg>
  )
}

function IconUser() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

function IconDownload() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}

// ── 컴포넌트 ─────────────────────────────────────────────────

export default function EditorTopBar({ filename, saveState = 'idle', onSaveNow }: Props) {
  const router = useRouter()

  const saveLabel =
    saveState === 'saving' ? '저장 중...' :
    saveState === 'saved'  ? '자동 저장됨' :
    saveState === 'error'  ? '저장 실패' :
    null

  const saveDotColor =
    saveState === 'saving' ? 'bg-status-run animate-pulse' :
    saveState === 'saved'  ? 'bg-status-done' :
    saveState === 'error'  ? 'bg-status-error' :
    null

  const docTitle = filename ?? '카드 에디터'

  return (
    <header className="fixed top-0 left-0 right-0 z-40 h-16 bg-surface/90 backdrop-blur-md backdrop-saturate-[140%] border-b border-surface-border flex items-center justify-between relative" style={{ padding: '0 clamp(16px, 1.5vw, 28px)' }}>
      <div className="contents">

        {/* ── LEFT: 브랜드 + 구분선 + 파일 칩 ── */}
        <div className="flex items-center gap-3.5 min-w-0">

          {/* 브랜드 */}
          <a
            href="/dashboard"
            className="inline-flex items-center gap-2.5 shrink-0 no-underline"
            aria-label="PolyInsight 홈"
          >
            <span className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-surface shadow-sm">
              <IconDoc />
            </span>
            <span className="text-[17px] font-bold tracking-[-0.01em] leading-none text-ink">PolyInsight</span>
          </a>

          <span className="w-px h-[22px] bg-surface-border shrink-0" aria-hidden="true" />

          {/* 파일명 칩 (편집 미구현) */}
          <BetaLocked>
            <button
              type="button"
              aria-label="프로젝트 이름 편집"
              className="inline-flex items-center gap-1.5 h-8 px-2.5 rounded-md hover:bg-surface-subtle transition-colors min-w-0"
            >
              <span className="text-[14px] font-medium text-ink-secondary leading-none whitespace-nowrap overflow-hidden text-ellipsis" style={{ maxWidth: 'clamp(120px, 14vw, 260px)' }}>
                {docTitle}
              </span>
              <span className="text-ink-muted inline-flex" aria-hidden="true">
                <IconEdit />
              </span>
            </button>
          </BetaLocked>

          {/* 저장 상태 */}
          {saveLabel && saveDotColor && (
            <div className="flex items-center gap-1.5 shrink-0">
              <span className={`w-1.5 h-1.5 rounded-full ${saveDotColor}`} />
              <span className="text-[11px] text-ink-muted">{saveLabel}</span>
            </div>
          )}
        </div>

        {/* ── CENTER: 브레드크럼 — 뷰포트 정중앙 절대 위치 ── */}
        <nav className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2.5 text-[14px] leading-none pointer-events-auto" aria-label="경로">
          <button
            type="button"
            onClick={() => router.push('/dashboard')}
            className="text-ink-muted px-2 py-1.5 rounded-md transition-colors hover:bg-surface-subtle hover:text-ink-secondary whitespace-nowrap"
          >
            프로젝트
          </button>
          <span className="text-ink-muted inline-flex shrink-0" aria-hidden="true">
            <IconChevron />
          </span>
          <span
            className="text-ink font-semibold underline underline-offset-[5px] decoration-[1.5px] whitespace-nowrap overflow-hidden text-ellipsis" style={{ maxWidth: 'clamp(140px, 16vw, 300px)' }}
            aria-current="page"
          >
            {docTitle}
          </span>
        </nav>

        {/* ── RIGHT ── */}
        <div className="flex items-center">

          {/* 유틸리티 아이콘 그룹 */}
          <div className="flex items-center gap-0.5">
            <BetaLocked>
              <button
                type="button"
                aria-label="동기화 상태"
                className="relative w-9 h-9 rounded-md bg-transparent text-ink-secondary inline-flex items-center justify-center transition-colors hover:bg-surface-subtle hover:text-ink"
              >
                <IconCloud />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-status-error border-[1.5px] border-surface" aria-label="동기화되지 않음" />
              </button>
            </BetaLocked>

            <BetaLocked>
              <button
                type="button"
                aria-label="설정"
                className="w-9 h-9 rounded-md bg-transparent text-ink-secondary inline-flex items-center justify-center transition-colors hover:bg-surface-subtle hover:text-ink"
              >
                <IconGear />
              </button>
            </BetaLocked>

            <BetaLocked>
              <button
                type="button"
                aria-label="내 계정"
                className="w-9 h-9 rounded-full border border-surface-border bg-surface text-ink-secondary inline-flex items-center justify-center transition-colors hover:bg-surface-subtle"
              >
                <IconUser />
              </button>
            </BetaLocked>
          </div>

          {/* 구분선 */}
          <div className="w-px h-5 bg-surface-border mx-4" aria-hidden="true" />

          {/* 저장 버튼 — DESIGN.md h-10(40px), px-6 */}
          <button
            type="button"
            onClick={onSaveNow}
            className="inline-flex items-center gap-3 h-10 px-6 rounded-[10px] bg-brand-600 text-surface font-semibold text-[14px] tracking-[-0.005em] shadow-sm transition-colors hover:bg-brand-700 active:translate-y-px focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600/40 focus-visible:ring-offset-2"
          >
            <span>저장</span>
            <IconDownload />
          </button>
        </div>

      </div>
    </header>
  )
}
