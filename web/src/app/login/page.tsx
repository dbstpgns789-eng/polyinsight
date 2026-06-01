import AuthLayout from '@/components/auth/AuthLayout';
import AuthForm from '@/components/auth/AuthForm';

export const metadata = { title: '로그인 — PolyInsight' };

export default function LoginPage() {
  return (
    <AuthLayout>
      <AuthForm mode="login" />
    </AuthLayout>
  );
}
