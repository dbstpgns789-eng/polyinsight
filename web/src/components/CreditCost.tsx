'use client'

// 버튼·액션의 크레딧 단가 인라인 표시 (Mirra "생성하기 (5크레딧)" 패턴).
// 유료(pro)만 크레딧을 소모하므로 pro에게만 보인다 — free는 무료카운터, lab은 무제한이라 숫자가 오히려 혼란.
import { useMe } from '@/lib/useMe'

export default function CreditCost({ n, className = 'credit-cost' }: { n: number; className?: string }) {
  const me = useMe()
  if (!me || me.plan !== 'pro') return null
  return <span className={className}>{n} 크레딧</span>
}
