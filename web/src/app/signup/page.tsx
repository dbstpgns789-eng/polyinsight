import { Suspense } from 'react';
import AuthLayout from '@/components/auth/AuthLayout';
import AuthForm from '@/components/auth/AuthForm';

export const metadata = { title: '회원가입 — PolyInsight' };

export default function SignupPage() {
  return (
    <AuthLayout>
      {/* AuthForm이 useSearchParams 사용 — Suspense 경계 필수 */}
      <Suspense>
        <AuthForm mode="signup" />
      </Suspense>
    </AuthLayout>
  );
}
