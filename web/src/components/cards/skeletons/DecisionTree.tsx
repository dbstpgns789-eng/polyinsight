// DecisionTree — 예/아니오 분기 의사결정(BranchTree). 피부만 조립. 등록키 'decision_tree'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, BranchTree, parseTableRows, tableRowsToRaw } from '../skin'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function DecisionTree(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const branches = parseTableRows(fieldValue(card, 'branches'))
  const onBranch = (i: number, field: 'attr' | 'a' | 'b', text: string) => {
    const next = branches.map((r, idx) => (idx === i ? { ...r, [field]: text } : r))
    onFieldChange?.('branches', tableRowsToRaw(next))
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
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', marginTop: 24 }}>
        <BranchTree root={fieldValue(card, 'root')} branches={branches} mode={mode} onRootChange={(v) => onFieldChange?.('root', v)}
          onBranchChange={onBranch} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
