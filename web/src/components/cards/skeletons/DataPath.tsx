// DataPath — 모듈 노드 + 화살표 시스템 흐름(NodeFlow). 피부만 조립. 등록키 'datapath'.
'use client'
import { CardSurface, BrandMark, Eyebrow, Headline, NodeFlow } from '../skin'
import { parsePipe, joinPipe } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function DataPath(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const nodes = parsePipe(fieldValue(card, 'nodes'))
  const onNode = (i: number, text: string) => {
    const next = [...nodes]; next[i] = text
    onFieldChange?.('nodes', joinPipe(next))
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
        <NodeFlow nodes={nodes} mode={mode} onNodeChange={onNode}
          onFieldFocus={onFieldFocus} focusedField={focusedField} />
      </div>
    </CardSurface>
  )
}
