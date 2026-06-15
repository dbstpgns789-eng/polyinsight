'use client';

import { useRouter } from 'next/navigation';

export default function LogoutButton() {
  const router = useRouter();
  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    router.replace('/login');
  }
  return (
    <button type="button" className="btn btn-outline" onClick={handleLogout}>
      로그아웃
    </button>
  );
}
