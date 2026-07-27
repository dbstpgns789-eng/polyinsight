'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';

// /api/auth/me로 세션 확인. 401/403(진짜 미인증)일 때만 /login으로 보낸다.
// ★네트워크 throw나 5xx(일시적 실패)엔 로그아웃하지 않는다 — 짧게 재시도하고, 그래도 안 되면
// 세션을 유지한 채 진행(쿠키는 유효, 개별 API 호출이 각자 처리). 대용량 업로드 직후 순간
// 연결 블립에 fetch가 throw하면서 사용자를 로그인창으로 튕기던 버그 방지.
// httpOnly 쿠키라 JS가 직접 못 읽으므로 서버에 확인 요청한다.
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      for (let attempt = 0; attempt < 3 && !cancelled; attempt++) {
        try {
          const r = await fetch('/api/auth/me', { credentials: 'include' });
          if (cancelled) return;
          if (r.status === 401 || r.status === 403) { router.replace('/login'); return; }
          if (!r.ok) {                              // 5xx 등 일시적 서버 오류 → 백오프 재시도
            await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
            continue;
          }
          const data = await r.json().catch(() => null);
          if (data?.onboarded === false && pathname !== '/onboarding') {
            router.replace('/onboarding');
            return;
          }
          setOk(true);
          return;
        } catch {                                   // 네트워크 throw → 재시도(로그아웃 금지)
          if (cancelled) return;
          await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
        }
      }
      // 재시도 다 실패(서버를 일시적으로 확인 불가). 쿠키는 유효할 가능성이 크니 로그아웃 없이 진행.
      // 세션이 정말 만료됐다면 서버가 401을 줬을 것(위에서 이미 /login 처리).
      if (!cancelled) setOk(true);
    };
    check();
    return () => { cancelled = true; };
  }, [router, pathname]);

  if (!ok) return null;
  return <>{children}</>;
}
