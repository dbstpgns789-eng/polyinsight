// BigStat — 큰 수치 + 단위 + 캡션. fidelity 정체성 컴포넌트(우리만 필요).
// 수치/단위/캡션 모두 편집 가능.

import EditableText from '../shared/EditableText'

interface BigStatProps {
  value: string         // 수치 (예: "238")
  unit: string          // 단위 (예: "MPa")
  caption: string       // 맥락 캡션
  mode: 'edit' | 'render' | 'thumbnail'
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function BigStat({ value, unit, caption, mode, onFieldChange, onFieldFocus, focusedField }: BigStatProps) {
  return (
    <div style={{ fontFamily: 'var(--set-font)' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 14 }}>
        <EditableText
          fieldKey="stat_value"
          value={value}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'stat_value'}
          style={{
            fontSize: 'var(--set-display)',
            fontWeight: 900,
            lineHeight: 0.9,
            letterSpacing: '-0.04em',
            color: 'var(--set-ink-strong)',
          }}
        />
        <EditableText
          fieldKey="stat_unit"
          value={unit}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'stat_unit'}
          style={{
            fontSize: 'var(--set-subhead)',
            fontWeight: 800,
            color: 'var(--set-accent)',
          }}
        />
      </div>
      <EditableText
        fieldKey="stat_caption"
        value={caption}
        mode={mode}
        multiline
        onFieldChange={onFieldChange}
        onFieldFocus={onFieldFocus}
        focused={focusedField === 'stat_caption'}
        style={{
          display: 'block',
          marginTop: 14,
          fontSize: 'var(--set-body)',
          fontWeight: 400,
          lineHeight: 1.5,
          color: 'var(--set-ink-muted)',
          wordBreak: 'keep-all',
        }}
      />
    </div>
  )
}
