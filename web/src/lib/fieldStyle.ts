// 요소 미세조정 — 토큰-바운드 부분 스타일을 base CSSProperties에 머지.
// 자유 CSS 금지(doc 18 강제 규칙): 크기=역할 토큰×배수, 색=--set-* 토큰만.

import type { CSSProperties } from 'react'
import type { FieldStyle } from '@/types/editor'

export const SIZE_MULTIPLIERS: Record<NonNullable<FieldStyle['size']>, number> = {
  S: 0.85, M: 1, L: 1.18, XL: 1.4,
}
export const TRACKING_MIN = -0.05
export const TRACKING_MAX = 0.1

const COLOR_TOKENS: Record<NonNullable<FieldStyle['color']>, string> = {
  'ink-strong': 'var(--set-ink-strong)',
  'ink-muted': 'var(--set-ink-muted)',
  accent: 'var(--set-accent)',
}
const WEIGHTS: Record<NonNullable<FieldStyle['weight']>, number> = {
  regular: 400, bold: 700,
}

export function clampTracking(n: number): number {
  if (Number.isNaN(n)) return 0
  return Math.min(TRACKING_MAX, Math.max(TRACKING_MIN, n))
}

export function applyFieldStyle(base: CSSProperties, fs?: FieldStyle): CSSProperties {
  if (!fs) return base
  const out: CSSProperties = { ...base }
  if (fs.size) {
    const baseSize = base.fontSize
    if (typeof baseSize === 'string') {
      out.fontSize = `calc((${baseSize}) * ${SIZE_MULTIPLIERS[fs.size]})`
    }
  }
  if (fs.weight) out.fontWeight = WEIGHTS[fs.weight]
  if (fs.align) out.textAlign = fs.align
  if (typeof fs.tracking === 'number') out.letterSpacing = `${clampTracking(fs.tracking)}em`
  if (fs.color) out.color = COLOR_TOKENS[fs.color]
  return out
}
