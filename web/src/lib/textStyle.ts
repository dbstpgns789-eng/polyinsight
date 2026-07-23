// 선택 요소의 computed 텍스트 스타일을 인스펙터 UI 상태로 정규화하는 순수 헬퍼.
// getComputedStyle은 letter-spacing "normal"과 line-height를 px로 해석해 돌려주므로,
// 슬라이더/스텝 UI가 쓸 수 있게 재변환한다. 적용(APPLY_STYLE)은 제네릭이라 여기선 읽기만 다룬다.

// 자간(px). "normal"·빈값·파싱실패 → 0.
export function parseLetterSpacingPx(v: string | undefined): number {
  if (!v || v === 'normal') return 0
  const n = parseFloat(v)
  return Number.isNaN(n) ? 0 : n
}

// 행간 배수. computed line-height는 px로 해석되므로 fontSize로 나눠 배수화(소수 1자리).
// "normal"·비px 단위없는 값은 그대로, fontSize 결측/0이면 기본 1.4.
export function parseLineHeightRatio(lineHeight: string | undefined, fontSize: string | undefined): number {
  if (!lineHeight || lineHeight === 'normal') return 1.4
  const lh = parseFloat(lineHeight)
  if (Number.isNaN(lh)) return 1.4
  if (!lineHeight.includes('px')) return Math.round(lh * 10) / 10   // 이미 단위없는 배수
  const fs = parseFloat(fontSize || '')
  if (Number.isNaN(fs) || fs <= 0) return 1.4
  return Math.round((lh / fs) * 10) / 10
}

// 굵기 스케일 스텝 중 현재값에 가장 가까운 것(동률이면 낮은 쪽). 결측=400 기준.
export function nearestWeightStep(fontWeight: string | undefined, steps: number[]): number {
  const w = parseInt(fontWeight || '', 10)
  const cur = Number.isNaN(w) ? 400 : w
  return steps.reduce((best, s) => (Math.abs(s - cur) < Math.abs(best - cur) ? s : best), steps[0])
}

// 그림자 있음 여부(프리셋 "없음" 활성 판정용). computed "none"·빈값 = 없음.
export function hasTextShadow(v: string | undefined): boolean {
  return !!v && v !== 'none'
}
