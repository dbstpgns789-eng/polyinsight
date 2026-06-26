// VersusPanels — A vs B 두 패널 + 승자 강조(왕관). 색 소유는 피부.
// ab_split 뼈대가 조립해 쓴다. 각 패널 = 라벨 + 값(편집 가능).
import EditableText from '../shared/EditableText'

interface PanelData { label: string; value: string }

interface Props {
  a: PanelData
  b: PanelData
  winner: 'a' | 'b'
  mode: 'edit' | 'render' | 'thumbnail'
  onChange?: (side: 'a' | 'b', field: 'label' | 'value', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

function Panel({ data, side, win, mode, onChange, onFieldFocus, focusedField }: {
  data: PanelData; side: 'a' | 'b'; win: boolean
  mode: Props['mode']; onChange?: Props['onChange']
  onFieldFocus?: Props['onFieldFocus']; focusedField?: Props['focusedField']
}) {
  return (
    <div style={{
      flex: 1, minWidth: 0, position: 'relative', textAlign: 'center',
      background: 'var(--set-surface)',
      border: win ? '2px solid var(--set-accent)' : '1px solid var(--set-surface-border)',
      borderRadius: 'var(--set-radius-box)', padding: '40px 28px',
      boxShadow: win ? '0 8px 30px rgba(0,0,0,0.10)' : 'none',
    }}>
      {win && <div aria-hidden style={{ position: 'absolute', top: -22, left: '50%', transform: 'translateX(-50%)', fontSize: 40 }}>👑</div>}
      <EditableText
        fieldKey={`variant_${side}_label`} value={data.label} mode={mode}
        onFieldChange={onChange ? (_fk, v) => onChange(side, 'label', v) : undefined}
        onFieldFocus={onFieldFocus} focused={focusedField === `variant_${side}_label`}
        style={{ display: 'block', fontSize: 'var(--set-subhead)', fontWeight: 800, color: win ? 'var(--set-accent)' : 'var(--set-ink-muted)', marginBottom: 14, wordBreak: 'keep-all' }}
      />
      <EditableText
        fieldKey={`variant_${side}_value`} value={data.value} mode={mode}
        onFieldChange={onChange ? (_fk, v) => onChange(side, 'value', v) : undefined}
        onFieldFocus={onFieldFocus} focused={focusedField === `variant_${side}_value`}
        style={{ display: 'block', fontSize: 'var(--set-headline)', fontWeight: 900, lineHeight: 1, letterSpacing: '-0.03em', color: 'var(--set-ink-strong)' }}
      />
    </div>
  )
}

export default function VersusPanels({ a, b, winner, mode, onChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--set-gap)', fontFamily: 'var(--set-font)' }}>
      <Panel data={a} side="a" win={winner === 'a'} mode={mode} onChange={onChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
      <div aria-hidden style={{ fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'var(--set-ink-faint)', flexShrink: 0 }}>VS</div>
      <Panel data={b} side="b" win={winner === 'b'} mode={mode} onChange={onChange} onFieldFocus={onFieldFocus} focusedField={focusedField} />
    </div>
  )
}
