import { Suspense } from 'react';
import AuthLayout from '@/components/auth/AuthLayout';
import AuthForm from '@/components/auth/AuthForm';

export const metadata = { title: '로그인 — PaperSweep' };

export default function LoginPage() {
  return (
    <AuthLayout>
      {/* AuthForm이 useSearchParams(?error=) 사용 — Suspense 경계 필수 */}
      <Suspense>
        <AuthForm mode="login" />
      </Suspense>
    </AuthLayout>
  );
}
