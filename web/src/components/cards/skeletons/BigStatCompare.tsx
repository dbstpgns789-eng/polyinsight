// ⑤ BigStatCompare — beat7(핵심성능+vs+출처). 피부 컴포넌트만 조립.
// 필드: eyebrow, headline, stat_value, stat_unit, stat_caption, bars, source_ref
// bars 포맷: "label:value:isPrimary|..." (parseCompareRows)

'use client'

import {
  CardSurface, BrandMark, Eyebrow, Headline, BigStat, CompareBars, SourceTag,
  parseCompareRows, rowsToRaw,
} from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function BigStatCompare(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const rows = parseCompareRows(fieldValue(card, 'bars'))

  const handleRowChange = (index: number, field: 'label' | 'value', text: string) => {
    const next = rows.map((r, i) => (i === index ? { ...r, [field]: text } : r))
    onFieldChange?.('bars', rowsToRaw(next))
  }

  return (
    <CardSurface>
      {/* 상단: eyebrow(좌) + 브랜드(우) */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow
          value={fieldValue(card, 'eyebrow')}
          fieldKey="eyebrow"
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'eyebrow'}
        />
        <BrandMark />
      </div>

      {/* 제목 */}
      <div style={{ marginTop: 18 }}>
        <Headline
          value={fieldValue(card, 'headline')}
          fieldKey="headline"
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'headline'}
        />
      </div>

      {/* 큰 수치 */}
      <div style={{ marginTop: 28 }}>
        <BigStat
          value={fieldValue(card, 'stat_value')}
          unit={fieldValue(card, 'stat_unit')}
          caption={fieldValue(card, 'stat_caption')}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focusedField={focusedField}
        />
      </div>

      {/* 비교 막대 — 남은 공간 차지(축소 가능·내부 클립)로 출처박스 겹침 방지 */}
      <div style={{ marginTop: 28, flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <CompareBars
          rows={rows}
          mode={mode}
          onRowChange={handleRowChange}
          onFieldFocus={onFieldFocus}
          focusedField={focusedField}
        />
      </div>

      {/* 출처칩 */}
      <SourceTag
        value={fieldValue(card, 'source_ref')}
        fieldKey="source_ref"
        mode={mode}
        onFieldChange={onFieldChange}
        onFieldFocus={onFieldFocus}
        focused={focusedField === 'source_ref'}
      />
    </CardSurface>
  )
}
