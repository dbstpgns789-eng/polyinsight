'use client';

import { useEffect } from 'react';
import posthog from 'posthog-js';

// 행동 분석 + 세션 리플레이. NEXT_PUBLIC_POSTHOG_KEY가 없으면 완전 no-op.
// 데이터 잔류 해외 OK 확인되어 PostHog Cloud 사용. 입력값은 마스킹.
export default function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (!key) return; // 키 미설정 → 비활성
    if (typeof window === 'undefined') return;
    if (posthog.__loaded) return; // 중복 init 방지
    posthog.init(key, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? 'https://us.i.posthog.com',
      capture_pageview: true,
      autocapture: true,
      session_recording: { maskAllInputs: true },
    });
  }, []);

  return <>{children}</>;
}
