// 카드 컴포넌트 레지스트리.
// Phase 2에서 12개 템플릿 컴포넌트가 등록될 예정. 현재는 비어 있음.
//
// 등록 후 사용:
//   import { CARD_COMPONENTS } from '@/components/cards'
//   const Comp = CARD_COMPONENTS[card.template_type]

import type { ComponentType } from 'react'
import type { CardComponentProps } from './types'

export const CARD_COMPONENTS: Record<string, ComponentType<CardComponentProps>> = {
  // Phase 2에서 추가:
  // brand:      BrandCard,
  // closing:    ClosingCard,
  // problem:    ProblemCard,
  // cover:      CoverCard,
  // hook:       HookCard,
  // showcase:   ShowcaseCard,
  // definition: DefinitionCard,
  // data:       DataCard,
  // flow:       FlowCard,
  // compare2:   Compare2Card,
  // grid4:      Grid4Card,
  // circle3:    Circle3Card,
}

export { default as CardRenderer } from './CardRenderer'
export { default as CardFrame, cardStyles } from './CardFrame'
export type { CardComponentProps, CardMode } from './types'
export { fieldValue } from './types'
