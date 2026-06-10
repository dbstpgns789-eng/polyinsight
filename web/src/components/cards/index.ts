// 카드 컴포넌트 레지스트리. card.template_type → React 컴포넌트(skin/skeleton 디자인 시스템 8뼈대).
//   import { CARD_COMPONENTS } from '@/components/cards'
//   const Comp = CARD_COMPONENTS[card.template_type]

import type { ComponentType } from 'react'
import type { CardComponentProps } from './types'
import BigStatCompare from './skeletons/BigStatCompare'
import Cover from './skeletons/Cover'
import Statement from './skeletons/Statement'
import Feature from './skeletons/Feature'
import Process from './skeletons/Process'
import Reasons from './skeletons/Reasons'
import Grid from './skeletons/Grid'
import Closing from './skeletons/Closing'
import Definition from './skeletons/Definition'
import ImageHero from './skeletons/ImageHero'
import Callout from './skeletons/Callout'
import MultiStat from './skeletons/MultiStat'
import Quote from './skeletons/Quote'
import CompareTable from './skeletons/CompareTable'

export const CARD_COMPONENTS: Record<string, ComponentType<CardComponentProps>> = {
  cover_v2:        Cover,
  statement:       Statement,
  feature:         Feature,
  process_v2:      Process,
  bigstat_compare: BigStatCompare,
  reasons:         Reasons,
  grid_v2:         Grid,
  closing_v2:      Closing,
  // 확장 레이아웃 (6)
  definition:      Definition,
  image_hero:      ImageHero,
  callout:         Callout,
  multistat:       MultiStat,
  quote:           Quote,
  compare_table:   CompareTable,
}

export { default as CardRenderer } from './CardRenderer'
export { default as CardFrame, cardStyles } from './CardFrame'
export type { CardComponentProps, CardMode } from './types'
export { fieldValue } from './types'
