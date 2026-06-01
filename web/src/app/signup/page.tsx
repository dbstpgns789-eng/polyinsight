import AuthLayout from '@/components/auth/AuthLayout';
import AuthForm from '@/components/auth/AuthForm';

export const metadata = { title: '회원가입 — PolyInsight' };

export default function SignupPage() {
  return (
    <AuthLayout>
      <AuthForm mode="signup" />
    </AuthLayout>
  );
}
