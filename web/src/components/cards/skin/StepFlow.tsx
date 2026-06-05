// StepFlow — N단계 흐름(세로). 각 단계 = accent 번호 + 텍스트. 적응형(N개).
import EditableText from '../shared/EditableText'

interface StepFlowProps {
  steps: string[]
  mode: 'edit' | 'render' | 'thumbnail'
  onStepChange?: (index: number, text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function StepFlow({ steps, mode, onStepChange, onFieldFocus, focusedField }: StepFlowProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, fontFamily: 'var(--set-font)' }}>
      {steps.map((s, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 20 }}>
          <div style={{
            width: 56, height: 56, borderRadius: 'var(--set-radius-pill)',
            background: 'var(--set-accent)', color: 'var(--set-accent-ink)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 'var(--set-subhead)', fontWeight: 900, flexShrink: 0,
          }}>{i + 1}</div>
          <EditableText
            fieldKey={`step_${i}`} value={s} mode={mode} multiline
            onFieldChange={onStepChange ? (_fk, v) => onStepChange(i, v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `step_${i}`}
            style={{
              display: 'block', flex: 1, alignSelf: 'center',
              fontSize: 'var(--set-body)', fontWeight: 600,
              lineHeight: 1.4, color: 'var(--set-ink-strong)', wordBreak: 'keep-all',
            }}
          />
        </div>
      ))}
    </div>
  )
}
