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
// 확장 레이아웃 (15~30) — docs/23_layout_catalog.md
import RadarChartCard from './skeletons/RadarChart'
import TradeOffMatrix from './skeletons/TradeOffMatrix'
import TerminalBlock from './skeletons/TerminalBlock'
import TimelineCard from './skeletons/Timeline'
import ChecklistCard from './skeletons/Checklist'
import Mythbuster from './skeletons/Mythbuster'
import GrowthChart from './skeletons/GrowthChart'
import ABSplit from './skeletons/ABSplit'
import Funnel from './skeletons/Funnel'
import DataPath from './skeletons/DataPath'
import TechGrid from './skeletons/TechGrid'
import DecisionTree from './skeletons/DecisionTree'
import TickerCard from './skeletons/Ticker'
import DoDont from './skeletons/DoDont'
import SwipeBait from './skeletons/SwipeBait'
import Chat from './skeletons/Chat'

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
  // 확장 레이아웃 (15~30) — docs/23_layout_catalog.md
  radar_chart:     RadarChartCard,
  tradeoff_matrix: TradeOffMatrix,
  terminal_block:  TerminalBlock,
  timeline:        TimelineCard,
  checklist:       ChecklistCard,
  mythbuster:      Mythbuster,
  growth_chart:    GrowthChart,
  ab_split:        ABSplit,
  funnel:          Funnel,
  datapath:        DataPath,
  tech_grid:       TechGrid,
  decision_tree:   DecisionTree,
  ticker:          TickerCard,
  do_dont:         DoDont,
  swipe_bait:      SwipeBait,
  chat:            Chat,
}

export { default as CardRenderer } from './CardRenderer'
export { default as CardFrame, cardStyles } from './CardFrame'
export type { CardComponentProps, CardMode } from './types'
export { fieldValue } from './types'
