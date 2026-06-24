// FunnelChart — 위에서 아래로 좁아지는 퍼널(N단계). 각 밴드 너비 ∝ 값. 색 소유는 피부.
// funnel 뼈대가 조립해 쓴다. stages = StatItem(label, value, unit). 병목 단계는 accent 강조.
import EditableText from '../shared/EditableText'
import { compareBarValue } from './parse'
import type { StatItem } from './parse'

interface Props {
  stages: StatItem[]
  bottleneck?: string        // 병목으로 강조할 단계 label
  mode: 'edit' | 'render' | 'thumbnail'
  onStageChange?: (index: number, field: 'label' | 'value' | 'unit', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function FunnelChart({ stages, bottleneck, mode, onStageChange, onFieldFocus, focusedField }: Props) {
  const valid = stages.filter((s) => s.label.length > 0)
  const max = Math.max(1, ...valid.map((s) => compareBarValue(s.value)))
  const bn = bottleneck?.trim()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center', fontFamily: 'var(--set-font)' }}>
      {valid.map((s, i) => {
        const ratio = Math.max(0.28, compareBarValue(s.value) / max)  // 최소 28% 너비(가독성)
        const isBn = bn && s.label.trim() === bn
        return (
          <div key={i} style={{
            width: `${ratio * 100}%`, minWidth: 0,
            background: isBn ? 'var(--set-accent)' : 'var(--set-surface)',
            border: isBn ? 'none' : '1px solid var(--set-surface-border)',
            color: isBn ? 'var(--set-accent-ink)' : 'var(--set-ink-strong)',
            borderRadius: 'var(--set-radius-box)', padding: '18px 26px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
            transition: 'none',
          }}>
            <EditableText
              fieldKey={`funnel_label_${i}`} value={s.label} mode={mode}
              onFieldChange={onStageChange ? (_fk, v) => onStageChange(i, 'label', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `funnel_label_${i}`}
              style={{ fontSize: 'var(--set-body)', fontWeight: 700, wordBreak: 'keep-all', color: 'inherit' }}
            />
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, flexShrink: 0 }}>
              <EditableText
                fieldKey={`funnel_value_${i}`} value={s.value} mode={mode}
                onFieldChange={onStageChange ? (_fk, v) => onStageChange(i, 'value', v) : undefined}
                onFieldFocus={onFieldFocus} focused={focusedField === `funnel_value_${i}`}
                style={{ fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'inherit' }}
              />
              <EditableText
                fieldKey={`funnel_unit_${i}`} value={s.unit} mode={mode}
                onFieldChange={onStageChange ? (_fk, v) => onStageChange(i, 'unit', v) : undefined}
                onFieldFocus={onFieldFocus} focused={focusedField === `funnel_unit_${i}`}
                style={{ fontSize: 'var(--set-caption)', fontWeight: 700, color: 'inherit', opacity: 0.8 }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
