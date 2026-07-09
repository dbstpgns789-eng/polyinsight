'use client'

// ⑥ 계정 — 아바타(이니셜) + 드롭다운(로그인 계정·대시보드·로그아웃). /api/auth/me 로 이메일 조회.
import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function DeckAccountMenu() {
  const [email, setEmail] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const router = useRouter()

  useEffect(() => {
    let cancelled = false
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (!cancelled) setEmail(d?.email ?? null) })
      .catch(() => { /* 무시 */ })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDoc); document.removeEventListener('keydown', onKey) }
  }, [open])

  const initials = (email ?? '?').split('@')[0].replace(/[^a-zA-Z0-9]/g, '').slice(0, 2).toUpperCase() || '?'
  const logout = async () => {
    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }) } catch { /* 무시 */ }
    router.replace('/login')
  }

  return (
    <div className="relative shrink-0" ref={ref}>
      <button onClick={() => setOpen((o) => !o)} aria-haspopup="menu" aria-expanded={open} title={email ?? '계정'}
        className="w-8 h-8 rounded-full bg-forest-green-wash text-forest-green-deep text-[11px] font-bold grid place-items-center border border-forest-green/25 hover:brightness-[0.97] transition">
        {initials}
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-10 z-50 w-56 rounded-xl border border-deck-line bg-surface shadow-modal p-1.5">
          <div className="px-2.5 py-2 border-b border-deck-line-soft mb-1">
            <div className="text-[10px] uppercase tracking-wide text-ink-3">로그인 계정</div>
            <div className="text-[12.5px] font-semibold text-ink truncate">{email ?? '—'}</div>
          </div>
          <a href="/dashboard" className="block px-2.5 py-2 text-[12.5px] text-ink-2 rounded-lg hover:bg-bg-subtle transition-colors">대시보드</a>
          <button onClick={logout} className="w-full text-left px-2.5 py-2 text-[12.5px] text-ink-2 rounded-lg hover:bg-bg-subtle transition-colors">로그아웃</button>
        </div>
      )}
    </div>
  )
}
