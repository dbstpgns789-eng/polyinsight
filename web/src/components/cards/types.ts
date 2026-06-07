// 카드 컴포넌트가 공통으로 따르는 props 계약.

import type { Card, CardTheme } from '@/types/editor'

export type CardMode = 'edit' | 'render' | 'thumbnail'

export interface CardComponentProps {
  card: Card
  theme: CardTheme
  mode: CardMode
  onFieldChange?: (fieldKey: string, value: string) => void
  onImageRequest?: (slotKey: string) => void
  onFocalChange?: (focal: { x: number; y: number }) => void
  onFitChange?: (fit: 'cover' | 'contain') => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

/** 필드 값 추출 헬퍼: card.fields[key].value를 안전하게 꺼냄. */
export function fieldValue(card: Card, key: string): string {
  return card.fields?.[key]?.value ?? ''
}
