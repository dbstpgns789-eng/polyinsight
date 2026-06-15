'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

// /api/auth/me로 세션 확인. 401이면 /login으로 리다이렉트.
// httpOnly 쿠키라 JS가 직접 못 읽으므로 서버에 확인 요청한다.
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => {
        if (cancelled) return;
        if (r.ok) setOk(true);
        else router.replace('/login');
      })
      .catch(() => { if (!cancelled) router.replace('/login'); });
    return () => { cancelled = true; };
  }, [router]);

  if (!ok) return null;
  return <>{children}</>;
}
