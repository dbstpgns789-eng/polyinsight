/**
 * 플랜 게이트 — 무료체험(export-gate 순수잠금)의 프론트 판정.
 *
 * ★402(플랜 벽)와 429(브루트포스 차단)를 반드시 구분한다. 429에 페이월을 띄우면
 * 잘못된 유저에게 결제를 요구하게 된다.
 */

export type PlanGateKind = 'author' | 'export' | 'credit'

// 작업별 크레딧 단가 — backend/core/plans.py의 DECK_COST·AIEDIT_COST와 동기 유지(표시용).
export const CREDIT_COST = { deck: 10, aiEdit: 2 } as const

export type PlanState = {
  plan: string
  freeDecksUsed: number
  freeDeckLimit: number
}

type MaybeApiError = Error & { status?: number; code?: string }

export function planGateKind(err: unknown): PlanGateKind | null {
  const e = err as MaybeApiError
  if (!e || e.status !== 402) return null
  if (e.code === 'ERR-PLAN-EXPORT') return 'export'
  if (e.code === 'ERR-PLAN-AUTHOR') return 'author'
  if (e.code === 'ERR-CREDIT-LOW') return 'credit'   // 유료 잔액 부족 → 충전 유도
  return null
}

export function isPlanGateError(err: unknown): boolean {
  return planGateKind(err) !== null
}

/** 무료 유저에게만 보여줄 사용량 라벨. 유료면 null(미터 자체를 감춘다). */
export function trialLabel(state: PlanState): string | null {
  if (state.plan !== 'free') return null
  return `무료 체험 · ${state.freeDecksUsed} / ${state.freeDeckLimit} 덱 사용`
}
