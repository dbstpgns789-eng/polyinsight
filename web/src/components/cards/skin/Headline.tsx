// Headline — 카드 제목. *별표* 구간을 accent 강조(em)로 렌더(parseEmphasis 사용).
// edit 모드: raw 텍스트 편집(별표 노출). render/thumbnail: 별표 파싱 → accent em.

import EditableText from '../shared/EditableText'
import { parseEmphasis } from './parse'

interface HeadlineProps {
  value: string
  fieldKey: string
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

const headlineStyle = {
  display: 'block',
  fontFamily: 'var(--set-font)',
  fontSize: 'var(--set-headline)',
  fontWeight: 800,
  lineHeight: 1.16,
  letterSpacing: '-0.025em',
  color: 'var(--set-ink-strong)',
  wordBreak: 'keep-all' as const,
}

export default function Headline({ value, fieldKey, mode, onFieldChange, onFieldFocus, focused }: HeadlineProps) {
  if (mode === 'edit') {
    return (
      <EditableText
        fieldKey={fieldKey}
        value={value}
        mode={mode}
        multiline
        onFieldChange={onFieldChange}
        onFieldFocus={onFieldFocus}
        focused={focused}
        style={headlineStyle}
      />
    )
  }
  return (
    <div style={headlineStyle}>
      {parseEmphasis(value).map((seg, i) =>
        seg.em
          ? <em key={i} style={{ color: 'var(--set-accent)', fontStyle: 'normal' }}>{seg.text}</em>
          : <span key={i}>{seg.text}</span>
      )}
    </div>
  )
}
