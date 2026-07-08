// 팩트 배지 상태 파생 — 뷰·편집 상단바 공통. 출처/정합 주장 금지(헌법: 코드가 증명 못 하는 것 표기 X).
export interface VerifyLike { verified: number; unverified: number; claims: unknown[] }
export type BadgeTone = 'ok' | 'warn' | 'muted'
export interface BadgeState { tone: BadgeTone; label: string; icon: string }

export function factBadgeState(verify: VerifyLike | null | undefined, canReverify: boolean): BadgeState {
  if (!verify) return { tone: 'muted', label: '검증 없음', icon: '—' }
  if (!canReverify) return { tone: 'muted', label: '재검증 안 됨', icon: '—' }
  if (verify.unverified >= 1) return { tone: 'warn', label: `${verify.unverified}개 확인 필요`, icon: '⚠' }
  return { tone: 'ok', label: `수치 ${verify.verified} 확인`, icon: '✓' }
}
