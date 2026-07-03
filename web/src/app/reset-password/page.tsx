'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function ResetPasswordPage() {
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get('token') ?? '');
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!password || password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return;
    }
    if (password !== confirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data?.detail?.message ?? '재설정에 실패했습니다. 링크가 만료됐을 수 있습니다.');
        setLoading(false);
        return;
      }
      setDone(true);
    } catch {
      setError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.');
      setLoading(false);
    }
  }

  return (
    <div className="verify-wrap">
      <div className="verify-card">
        <Link href="/" className="verify-logo" aria-label="PolyInsight 홈">
          Poly<span>Insight</span>
        </Link>

        {done ? (
          <>
            <h1 className="verify-title">비밀번호가 변경됐습니다</h1>
            <p className="verify-msg">
              보안을 위해 모든 기기에서 로그아웃됐습니다. 새 비밀번호로 다시 로그인해 주세요.
            </p>
            <Link href="/login" className="btn btn-primary btn-lg">로그인</Link>
          </>
        ) : token === null ? (
          <p className="verify-msg">링크 확인 중…</p>
        ) : token === '' ? (
          <>
            <h1 className="verify-title">유효하지 않은 링크입니다</h1>
            <p className="verify-msg">재설정 메일을 다시 요청해 주세요.</p>
            <Link href="/forgot-password" className="btn btn-outline btn-lg">다시 요청하기</Link>
          </>
        ) : (
          <>
            <h1 className="verify-title">새 비밀번호 설정</h1>
            <form onSubmit={handleSubmit} noValidate style={{ display: 'grid', gap: 12, textAlign: 'left' }}>
              <input
                type="password"
                className="auth-input"
                placeholder="새 비밀번호 (8자 이상)"
                value={password}
                onChange={e => { setPassword(e.target.value); setError(''); }}
                autoComplete="new-password"
                aria-label="새 비밀번호"
              />
              <input
                type="password"
                className="auth-input"
                placeholder="새 비밀번호 확인"
                value={confirm}
                onChange={e => { setConfirm(e.target.value); setError(''); }}
                autoComplete="new-password"
                aria-label="새 비밀번호 확인"
              />
              {error && <p className="auth-field__error" role="alert">{error}</p>}
              <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
                {loading ? '변경 중…' : '비밀번호 변경'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
