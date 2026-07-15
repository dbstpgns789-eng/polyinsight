'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [email, setEmail] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 세션 쿠키로 실제 유저 이메일 조회 — 401이면 AuthGuard가 /login으로 보내므로 빈 값 유지
    fetch('/api/auth/me', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d?.email) setEmail(d.email); })
      .catch(() => {});
  }, []);

  const initial = email ? email[0].toUpperCase() : 'U';

  async function handleLogout() {
    // 서버 세션·쿠키 실제 무효화 — localStorage만 지우면 세션 살아있는 가짜 로그아웃
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    router.replace('/login');
  }

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  return (
    <>
      <header className="app-header">
        <div className="app-header__inner">
          <Link href="/" className="app-header__logo">
            Poly<span>Insight</span>
          </Link>

          <nav className="app-header__nav" aria-label="앱 내비게이션">
            <Link href="/dashboard" className="app-header__nav-link">대시보드</Link>
          </nav>

          <div className="app-header__actions">
            <Link href="/deck/new" className="btn btn-primary app-header__cta">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                <path d="M6.5 1.5v10M1.5 6.5h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              </svg>
              새 카드뉴스
            </Link>

            <div className="app-avatar" ref={menuRef}>
              <button
                className="app-avatar__btn"
                onClick={() => setMenuOpen(v => !v)}
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-label="계정 메뉴 열기"
              >
                {initial}
              </button>

              {menuOpen && (
                <div className="app-avatar__menu" role="menu">
                  {email && <p className="app-avatar__email">{email}</p>}
                  <button
                    className="app-avatar__item"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                    disabled
                  >
                    설정
                  </button>
                  <hr className="app-avatar__sep" />
                  <button
                    className="app-avatar__item"
                    role="menuitem"
                    onClick={handleLogout}
                  >
                    로그아웃
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">{children}</main>
    </>
  );
}
