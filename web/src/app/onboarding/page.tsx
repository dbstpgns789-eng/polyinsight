'use client'

// 첫 방문 환영 온보딩 (무료체험 배관 Task 8). AuthGuard가 onboarded=false인 유저를
// 여기로 보낸다 — 처음 온 사람에게 정확히 1회만 뜬다. 재방문 무료 유저는 오지 않는다.
// 전환 넛지(결제 안 한 사람 대상)는 여기 소관이 아니다 — 대시보드 미터·export 벽·/upgrade가 담당(축이 다르다).
// 이메일 인증은 여기서 요구하지 않는다 — 무료 덱 뒤로 미룬다.

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import AuthGuard from '@/components/auth/AuthGuard'

function OnboardingInner() {
  const router = useRouter()
  const [leaving, setLeaving] = useState(false)

  async function finish(dest: string) {
    setLeaving(true)
    try {
      // 멱등 — 실패해도 진행을 막지 않는다(온보딩이 유저를 가두면 안 된다).
      await fetch('/api/auth/onboarded', { method: 'POST', credentials: 'include' })
    } catch {
      /* noop */
    }
    router.replace(dest)
  }

  return (
    <main className="onboarding">
      <div className="onboarding__card">
        <p className="onboarding__eyebrow">환영합니다</p>
        <h1 className="onboarding__title">논문 한 편이면,<br />카드뉴스 한 세트가 됩니다.</h1>
        <p className="onboarding__lede">
          PDF를 올리면 스토리·디자인·검증까지 한 번에 만들어 드려요.
          모든 수치는 원문과 대조해 <strong>✓ 확인</strong> 배지를 답니다.
        </p>

        <ol className="onboarding__steps">
          <li><span>1</span> 논문 PDF 업로드</li>
          <li><span>2</span> 카드뉴스 자동 저작 + 수치 검증</li>
          <li><span>3</span> 화면에서 확인하고 편집</li>
        </ol>

        <p className="onboarding__note">
          지금은 <strong>무료 체험 1덱</strong>이에요. 만들고 검증까지 전부 볼 수 있고,
          파일 내보내기는 업그레이드 후 이용할 수 있어요.
        </p>

        <div className="onboarding__actions">
          <button className="btn btn-primary" disabled={leaving} onClick={() => finish('/deck/new')}>
            첫 논문 올리기 →
          </button>
          <button className="btn btn-ghost" disabled={leaving} onClick={() => finish('/dashboard')}>
            나중에 할게요
          </button>
        </div>
      </div>
    </main>
  )
}

export default function OnboardingPage() {
  return (
    <AuthGuard>
      <OnboardingInner />
    </AuthGuard>
  )
}
