'use client'

import { useRouter } from 'next/navigation'

type SaveState = 'saving' | 'saved' | 'idle' | 'error'

interface Props {
  filename?: string
  saveState?: SaveState
  onSaveNow?: () => void
  onExport?: () => void
}

// ── 아이콘 ────────────────────────────────────────────────────────────────
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
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06-.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
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

// ── 컴포넌트 ──────────────────────────────────────────────────────────────
export default function Topbar({ filename, onSaveNow, onExport }: Props) {
  const router = useRouter()
  const docTitle = filename ?? 'Research Paper'

  return (
    <header
      className="sticky top-0 z-50 w-full flex items-stretch shrink-0"
      style={{
        height: 64,
        background: 'color-mix(in oklch, var(--surface) 90%, transparent)',
        backdropFilter: 'blur(12px) saturate(140%)',
        WebkitBackdropFilter: 'blur(12px) saturate(140%)',
        borderBottom: '1px solid var(--surface-border)',
      }}
      role="banner"
    >
      <div
        className="w-full grid items-center"
        style={{ padding: '0 24px', gridTemplateColumns: 'auto 1fr auto', gap: 24 }}
      >

        {/* ── LEFT — Brand + doc chip ── */}
        <div className="flex items-center min-w-0" style={{ gap: 14 }}>

          <a
            href="/dashboard"
            className="inline-flex items-center shrink-0 no-underline"
            style={{ gap: 10, color: 'var(--ink)' }}
            aria-label="PolyInsight 홈"
          >
            <span
              className="flex items-center justify-center text-white"
              style={{
                width: 32, height: 32, borderRadius: 8,
                background: 'var(--brand-600)',
                boxShadow: '0 1px 2px rgba(15, 27, 22, 0.04)',
              }}
              aria-hidden="true"
            >
              <IconDoc />
            </span>
            <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1, color: 'var(--ink)' }}>
              PolyInsight
            </span>
          </a>

          <span
            className="shrink-0"
            style={{ width: 1, height: 22, background: 'var(--surface-border)' }}
            aria-hidden="true"
          />

          <button
            type="button"
            aria-label="프로젝트 이름 편집"
            className="inline-flex items-center min-w-0 transition-colors"
            style={{ gap: 6, height: 32, paddingLeft: 10, paddingRight: 8, borderRadius: 6, background: 'transparent', border: 0, cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-subtle)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <span
              className="whitespace-nowrap overflow-hidden text-ellipsis"
              style={{ fontSize: 14, fontWeight: 500, color: 'var(--ink-secondary)', lineHeight: 1, maxWidth: 'clamp(100px, 12vw, 220px)' }}
            >
              {docTitle}
            </span>
            <span style={{ color: 'var(--ink-muted)', display: 'inline-flex', transition: 'color 120ms ease' }} aria-hidden="true">
              <IconEdit />
            </span>
          </button>
        </div>

        {/* ── CENTER — breadcrumb ── */}
        <nav
          className="flex items-center justify-center min-w-0"
          style={{ gap: 10, fontSize: 14, lineHeight: 1 }}
          aria-label="경로"
        >
          <button
            type="button"
            onClick={() => router.push('/dashboard')}
            className="whitespace-nowrap transition-colors"
            style={{ color: 'var(--ink-muted)', padding: '6px 8px', borderRadius: 6, background: 'transparent', border: 0, cursor: 'pointer', fontFamily: 'inherit', fontSize: 'inherit' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-subtle)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-secondary)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-muted)' }}
          >
            My Projects
          </button>
          <span style={{ color: 'var(--ink-muted)', display: 'inline-flex', flexShrink: 0 }} aria-hidden="true">
            <IconChevron />
          </span>
          <span
            className="whitespace-nowrap overflow-hidden text-ellipsis"
            style={{
              color: 'var(--ink)', fontWeight: 600,
              textDecoration: 'underline', textUnderlineOffset: 5, textDecorationThickness: 1.5,
              maxWidth: 'clamp(120px, 14vw, 280px)',
            }}
            aria-current="page"
          >
            {docTitle}
          </span>
        </nav>

        {/* ── RIGHT — actions ── */}
        <div className="flex items-center" style={{ gap: 4 }}>

          {/* Cloud / sync */}
          <button
            type="button"
            aria-label="동기화 상태"
            className="relative inline-flex items-center justify-center transition-colors"
            style={{ width: 36, height: 36, borderRadius: 6, border: 0, background: 'transparent', color: 'var(--ink-secondary)', cursor: 'pointer' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-subtle)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-secondary)' }}
          >
            <IconCloud />
            <span
              className="absolute rounded-full"
              style={{
                top: 6, right: 6, width: 8, height: 8,
                background: 'var(--status-error)',
                borderWidth: 1.5, borderStyle: 'solid', borderColor: 'var(--surface)',
                boxShadow: '0 0 0 0.5px rgba(15, 27, 22, 0.06)',
              }}
              aria-label="동기화되지 않음"
            />
          </button>

          {/* Gear / settings */}
          <button
            type="button"
            aria-label="설정"
            className="inline-flex items-center justify-center transition-colors"
            style={{ width: 36, height: 36, borderRadius: 6, border: 0, background: 'transparent', color: 'var(--ink-secondary)', cursor: 'pointer' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-subtle)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--ink-secondary)' }}
          >
            <IconGear />
          </button>

          {/* Avatar */}
          <button
            type="button"
            aria-label="내 계정"
            className="inline-flex items-center justify-center transition-colors"
            style={{
              width: 36, height: 36, borderRadius: '50%',
              borderWidth: 1.25, borderStyle: 'solid', borderColor: 'var(--surface-border)',
              background: 'var(--surface)', color: 'var(--ink-secondary)',
              cursor: 'pointer', margin: '0 6px 0 4px',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-subtle)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'oklch(82% 0.012 152)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--surface-border)' }}
          >
            <IconUser />
          </button>

          {/* Export */}
          <button
            type="button"
            onClick={onExport}
            className="inline-flex items-center transition-colors active:translate-y-[0.5px]"
            style={{
              gap: 8, height: 36, padding: '0 16px',
              borderRadius: 10,
              borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--surface-border)',
              background: 'var(--surface)', color: 'var(--ink-secondary)',
              fontFamily: 'inherit', fontSize: 14, fontWeight: 600,
              letterSpacing: '-0.005em', cursor: 'pointer',
            }}
            onMouseEnter={e => {
              const b = e.currentTarget as HTMLButtonElement
              b.style.background = 'var(--surface-subtle)'
              b.style.borderColor = 'oklch(82% 0.012 152)'
              b.style.color = 'var(--ink)'
            }}
            onMouseLeave={e => {
              const b = e.currentTarget as HTMLButtonElement
              b.style.background = 'var(--surface)'
              b.style.borderColor = 'var(--surface-border)'
              b.style.color = 'var(--ink-secondary)'
            }}
          >
            <IconDownload />
            <span>내보내기</span>
          </button>

          {/* Save */}
          <button
            type="button"
            onClick={onSaveNow}
            className="inline-flex items-center transition-colors active:translate-y-[0.5px]"
            style={{
              gap: 8, height: 36, padding: '0 16px',
              borderRadius: 10, border: 0,
              background: 'var(--brand-600)', color: '#fff',
              fontFamily: 'inherit', fontSize: 14, fontWeight: 600,
              letterSpacing: '-0.005em', cursor: 'pointer',
              boxShadow: '0 1px 2px rgba(15, 27, 22, 0.04)',
            }}
            onMouseEnter={e => ((e.currentTarget as HTMLButtonElement).style.background = 'var(--brand-700)')}
            onMouseLeave={e => ((e.currentTarget as HTMLButtonElement).style.background = 'var(--brand-600)')}
          >
            <span>저장</span>
            <IconDownload />
          </button>
        </div>

      </div>
    </header>
  )
}
