// CompareTable — 속성별 A vs B 비교 표(DataTable). 소재·방법 비교. 피부만 조립.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, DataTable, SourceTag, parseTableRows, tableRowsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function CompareTable(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const rows = parseTableRows(fieldValue(card, 'rows'))
  const onRowChange = (i: number, field: 'attr' | 'a' | 'b', text: string) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, [field]: text } : r))
    onFieldChange?.('rows', tableRowsToRaw(next))
  }
  const onHeaderChange = (field: 'a' | 'b', text: string) => {
    onFieldChange?.(field === 'a' ? 'col_a' : 'col_b', text)
  }
  return (
    <CardSurface>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Eyebrow value={fieldValue(card, 'eyebrow')} fieldKey="eyebrow" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'eyebrow'} />
        <BrandMark />
      </div>
      <div style={{ marginTop: 18 }}>
        <Headline value={fieldValue(card, 'headline')} fieldKey="headline" mode={mode}
          onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'headline'} />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: 28 }}>
        <DataTable rows={rows} colA={fieldValue(card, 'col_a')} colB={fieldValue(card, 'col_b')} mode={mode}
          onRowChange={onRowChange} onHeaderChange={onHeaderChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
      <SourceTag value={fieldValue(card, 'source_ref')} fieldKey="source_ref" mode={mode}
        onFieldChange={onFieldChange} onFieldFocus={onFieldFocus} focused={focusedField === 'source_ref'} />
    </CardSurface>
  )
}
