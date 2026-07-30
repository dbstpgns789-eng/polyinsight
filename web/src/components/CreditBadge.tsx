'use client'

// 크레딧 잔액 상시 표시 배지 (Mirra 벤치마크 #1: "유저가 크레딧을 전혀 모른다" 해소).
// 티어별로 다르게: pro=잔액+충전링크 / free=무료 체험 잔여 / lab·service=무제한.
// pro인데 생성 못 하는 잔액이면(canAuthor=false) 경고 톤으로 충전을 당긴다.
// compact: 밀집한 편집기 탑바용 — 라벨('크레딧'·'체험')을 빼 폭을 줄인다.
import Link from 'next/link'
import { useMe } from '@/lib/useMe'

function Diamond() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path d="M6 1 11 6 6 11 1 6Z" fill="currentColor" opacity="0.9" />
    </svg>
  )
}

export default function CreditBadge({ compact = false }: { compact?: boolean }) {
  const me = useMe()

  // 로딩 — 레이아웃 크기 맞춘 스켈레톤(스피너 금지)
  if (!me) return <span className="credit-badge credit-badge--skeleton" aria-hidden="true" />

  // lab/내부 서비스 = 무제한(충전 링크 없음)
  if (me.plan === 'lab' || me.role === 'service') {
    return (
      <span className="credit-badge credit-badge--lab" title="무제한 사용">
        <Diamond /> 무제한
      </span>
    )
  }

  // 무료 체험 = 크레딧이 아니라 무료 덱 잔여를 보여주고 충전(업그레이드)로 유도
  if (me.plan === 'free') {
    const left = Math.max(0, me.freeDeckLimit - me.freeDecksUsed)
    return (
      <Link href="/upgrade" className="credit-badge credit-badge--free" title="무료 체험 중. 업그레이드하면 크레딧으로 계속 만들 수 있어요">
        {compact ? `무료 ${left}/${me.freeDeckLimit}` : `무료 체험 · ${left}/${me.freeDeckLimit}`}
      </Link>
    )
  }

  // pro = 잔액. 생성 불가 잔액이면 경고 톤(--low)으로 충전을 당긴다
  const low = !me.canAuthor
  return (
    <Link
      href="/upgrade"
      className={`credit-badge${low ? ' credit-badge--low' : ''}`}
      title={low ? '크레딧이 부족해요. 충전하면 계속 만들 수 있어요' : '크레딧 충전'}
    >
      <Diamond />
      <span className="credit-badge__num">{me.credits.toLocaleString()}</span>
      {!compact && '크레딧'}
    </Link>
  )
}
