'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

// /api/auth/me로 세션 확인. 401이면 /login으로 리다이렉트.
// 처음 온 사람(onboarded=false)은 /onboarding으로 — 단, 자기 자신(/onboarding)은 예외 처리해
// 무한 리다이렉트를 막는다(pathname 체크가 핵심).
// httpOnly 쿠키라 JS가 직접 못 읽으므로 서버에 확인 요청한다.
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/auth/me', { credentials: 'include' })
      .then(async (r) => {
        if (cancelled) return;
        if (!r.ok) { router.replace('/login'); return; }
        const data = await r.json().catch(() => null);
        if (data?.onboarded === false && pathname !== '/onboarding') {
          router.replace('/onboarding');
          return;
        }
        setOk(true);
      })
      .catch(() => { if (!cancelled) router.replace('/login'); });
    return () => { cancelled = true; };
  }, [router, pathname]);

  if (!ok) return null;
  return <>{children}</>;
}
