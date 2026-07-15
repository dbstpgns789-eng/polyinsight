'use client';

import { useState } from 'react';
import Link from 'next/link';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('유효한 이메일 주소를 입력해 주세요.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (res.status === 429) {
        setError('요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.');
        return;
      }
      if (!res.ok) {
        setError('요청에 실패했습니다. 잠시 후 다시 시도해 주세요.');
        return;
      }
      // 존재 여부와 무관하게 항상 성공 화면 (열거 대칭)
      setSent(true);
    } catch {
      setError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="verify-wrap">
      <div className="verify-card">
        <Link href="/" className="verify-logo" aria-label="PolyInsight 홈">
          Poly<span>Insight</span>
        </Link>

        {sent ? (
          <>
            <h1 className="verify-title">메일함을 확인해 주세요</h1>
            <p className="verify-msg">
              가입된 이메일이라면 비밀번호 재설정 링크를 보내 드렸습니다.
              링크는 2시간 후 만료됩니다. (스팸함도 확인해 주세요)
            </p>
            <Link href="/login" className="btn btn-outline btn-lg">로그인으로 돌아가기</Link>
          </>
        ) : (
          <>
            <h1 className="verify-title">비밀번호 재설정</h1>
            <p className="verify-msg">가입한 이메일 주소를 입력하면 재설정 링크를 보내 드립니다.</p>
            <form onSubmit={handleSubmit} noValidate style={{ display: 'grid', gap: 12, textAlign: 'left' }}>
              <input
                type="email"
                className="auth-input"
                placeholder="이메일 주소"
                value={email}
                onChange={e => { setEmail(e.target.value); setError(''); }}
                autoComplete="email"
                aria-label="이메일 주소"
              />
              {error && <p className="auth-field__error" role="alert">{error}</p>}
              <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
                {loading ? '전송 중…' : '재설정 링크 보내기'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
