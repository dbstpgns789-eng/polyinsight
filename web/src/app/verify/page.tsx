'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type State = 'loading' | 'ok' | 'fail';

export default function VerifyPage() {
  const [state, setState] = useState<State>('loading');

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token');
    if (!token) {
      setState('fail');
      return;
    }
    fetch('/api/auth/confirm-verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ token }),
    })
      .then((r) => setState(r.ok ? 'ok' : 'fail'))
      .catch(() => setState('fail'));
  }, []);

  return (
    <div className="verify-wrap">
      <div className="verify-card">
        <Link href="/" className="verify-logo" aria-label="PaperSweep 홈">
          Paper<span>Sweep</span>
        </Link>

        {state === 'loading' && <p className="verify-msg">이메일 인증 중…</p>}

        {state === 'ok' && (
          <>
            <h1 className="verify-title">이메일 인증이 완료됐습니다</h1>
            <p className="verify-msg">이제 PaperSweep를 편하게 이용하세요.</p>
            <Link href="/dashboard" className="btn btn-primary btn-lg">대시보드로 가기</Link>
          </>
        )}

        {state === 'fail' && (
          <>
            <h1 className="verify-title">인증 링크가 유효하지 않습니다</h1>
            <p className="verify-msg">링크가 만료됐거나 이미 사용됐습니다. 로그인 후 인증 메일을 다시 요청해 주세요.</p>
            <Link href="/login" className="btn btn-outline btn-lg">로그인</Link>
          </>
        )}
      </div>
    </div>
  );
}
