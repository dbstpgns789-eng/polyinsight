// 템플릿별 필드 스키마 — Jinja2 카드 템플릿(`backend/templates/*.html`)을 미러링.
// 각 카드 컴포넌트가 어떤 필드를 받는지, 파싱이 필요한 필드는 어떤 구분자를 쓰는지 정의.
// 백엔드 _build_card_context (s7_renderer.py)와 항상 동기화 유지.

import type { DelimiterStrategy } from '@/components/cards/shared/delimiters'

export interface TemplateSchema {
  text: readonly string[]                              // 단순 텍스트 필드
  parsed: Readonly<Record<string, DelimiterStrategy>>  // 구분자 파싱 필드
}

export const TEMPLATE_FIELDS: Readonly<Record<string, TemplateSchema>> = {
  cover:      { text: ['title', 'subtitle', 'edition', 'org'],                    parsed: {} },
  hook:       { text: ['title', 'highlight', 'body', 'source_credit'],            parsed: {} },
  problem:    { text: ['title', 'body', 'emphasis'],                              parsed: {} },
  circle3:    { text: ['title', 'body'],                                          parsed: { c1: 'colon', c2: 'colon', c3: 'colon' } },
  compare2:   { text: ['title', 'subtitle', 'label_a', 'label_b'],                parsed: { points_a: 'dot', points_b: 'dot' } },
  grid4: {
    text: [
      'title', 'subtitle',
      'item1_label', 'item1_sub', 'item1_image',
      'item2_label', 'item2_sub', 'item2_image',
      'item3_label', 'item3_sub', 'item3_image',
      'item4_label', 'item4_sub', 'item4_image',
    ],
    parsed: {},
  },
  flow:       { text: ['title'],                                                  parsed: { steps_text: 'dot' } },
  showcase:   { text: ['title', 'body'],                                          parsed: { icon1: 'colon', icon2: 'colon', icon3: 'colon' } },
  definition: { text: ['term', 'term_detail', 'definition_text', 'body'],         parsed: {} },
  closing:    { text: ['title_white', 'title_accent', 'body'],                    parsed: {} },
  data:       { text: ['title', 'data_unit', 'source', 'bar_max'],                parsed: { bars: 'pipe' } },
  brand:      { text: ['tagline', 'body', 'cta', 'footer_text'],                  parsed: {} },
} as const

export function getTemplateSchema(templateType: string): TemplateSchema | null {
  return TEMPLATE_FIELDS[templateType] ?? null
}

export const TEMPLATE_TYPES = Object.keys(TEMPLATE_FIELDS)
