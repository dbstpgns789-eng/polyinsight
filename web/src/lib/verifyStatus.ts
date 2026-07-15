// V2 파생수치(derived) 판독 — 산수 불일치(suspect)를 팩트 패널에 표면화하기 위한 순수함수.
//
// 배경: 검증이 계산만 하고 화면에 안 나오면 로그일 뿐이다. 170% 오기도 "수치가 원문에 존재"라
// VERIFIED로 통과해 그대로 발행됐다 — 표면화가 곧 해자의 완성이다(헌법 §2).
// unresolved(검산 불가)는 렌더하지 않는다 — 모르면 죄 아님(노이즈로 신뢰를 깎지 않는다).

export interface DerivedClaim {
  value: string
  kind: string
  suspect: boolean
  unresolved: boolean
  verified: boolean
  context: string
  card?: number | null // 구 덱엔 없음
}

export interface VerifyClaim {
  value: string
  context: string
  verified: boolean
  card?: number | null // 구 덱엔 없음
}

export interface VerifyData {
  verified: number
  unverified: number
  claims: VerifyClaim[]
  derived?: DerivedClaim[] // 구 덱엔 없음 — optional(하위호환)
}

export function suspectClaims(verify: VerifyData | null | undefined): DerivedClaim[] {
  return (verify?.derived ?? []).filter((d) => d.suspect)
}

export function isAllClear(verify: VerifyData | null | undefined): boolean {
  if (!verify) return false
  return verify.unverified === 0 && suspectClaims(verify).length === 0
}

/** 사용자가 훑어야 할 항목(확인 필요) — 패널·문맥 바가 공유하는 단일 순서. */
export interface ReviewItem {
  value: string
  context: string
  card: number | null
  reason: 'mismatch' | 'missing'   // 계산이 안 맞음 / 원문에 없음
}

export function reviewQueue(verify: VerifyData | null | undefined): ReviewItem[] {
  const mismatch: ReviewItem[] = suspectClaims(verify).map((d) => ({
    value: d.value, context: d.context, card: d.card ?? null, reason: 'mismatch' as const,
  }))
  const missing: ReviewItem[] = (verify?.claims ?? [])
    .filter((c) => !c.verified)
    .map((c) => ({ value: c.value, context: c.context, card: c.card ?? null, reason: 'missing' as const }))
  return [...mismatch, ...missing]
}
