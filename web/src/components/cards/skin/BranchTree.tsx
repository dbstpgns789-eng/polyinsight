// BranchTree — 의사결정 분기(루트 조건 + 예/아니오 결과). 색 소유는 피부.
// decision_tree 뼈대가 조립해 쓴다. root=string, branches=TableRow(attr=조건, a=예결과, b=아니오결과).
import EditableText from '../shared/EditableText'
import type { TableRow } from './parse'

interface Props {
  root: string
  branches: TableRow[]
  mode: 'edit' | 'render' | 'thumbnail'
  onRootChange?: (text: string) => void
  onBranchChange?: (index: number, field: 'attr' | 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

function Outcome({ tag, value, fieldKey, accent, mode, onChange, onFieldFocus, focused }: {
  tag: string; value: string; fieldKey: string; accent: boolean
  mode: Props['mode']; onChange?: (text: string) => void
  onFieldFocus?: Props['onFieldFocus']; focused: boolean
}) {
  return (
    <div style={{
      flex: 1, minWidth: 0, background: 'var(--set-surface)',
      border: accent ? '1.5px solid var(--set-accent)' : '1px solid var(--set-surface-border)',
      borderRadius: 'var(--set-radius-box)', padding: '16px 20px',
    }}>
      <div style={{ fontSize: 'var(--set-caption)', fontWeight: 800, color: accent ? 'var(--set-accent)' : 'var(--set-ink-faint)', marginBottom: 4 }}>{tag}</div>
      <EditableText
        fieldKey={fieldKey} value={value} mode={mode} multiline
        onFieldChange={onChange ? (_fk, v) => onChange(v) : undefined}
        onFieldFocus={onFieldFocus} focused={focused}
        style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 600, lineHeight: 1.4, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
      />
    </div>
  )
}

export default function BranchTree({ root, branches, mode, onRootChange, onBranchChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: 'var(--set-font)' }}>
      {/* 루트 조건 */}
      <div style={{
        alignSelf: 'center', textAlign: 'center', maxWidth: '80%',
        background: 'var(--set-accent)', color: 'var(--set-accent-ink)',
        borderRadius: 'var(--set-radius-box)', padding: '20px 30px',
      }}>
        <EditableText
          fieldKey="root" value={root} mode={mode} multiline
          onFieldChange={onRootChange ? (_fk, v) => onRootChange(v) : undefined}
          onFieldFocus={onFieldFocus} focused={focusedField === 'root'}
          style={{ display: 'block', fontSize: 'var(--set-subhead)', fontWeight: 800, lineHeight: 1.3, color: 'inherit', wordBreak: 'keep-all' }}
        />
      </div>
      {branches.map((b, i) => (
        <div key={i}>
          <div style={{ fontSize: 'var(--set-caption)', fontWeight: 700, color: 'var(--set-ink-muted)', marginBottom: 8, textAlign: 'center' }}>
            <EditableText
              fieldKey={`branch_cond_${i}`} value={b.attr} mode={mode}
              onFieldChange={onBranchChange ? (_fk, v) => onBranchChange(i, 'attr', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `branch_cond_${i}`}
              style={{ fontSize: 'var(--set-caption)', fontWeight: 700, color: 'var(--set-ink-muted)' }}
            />
          </div>
          <div style={{ display: 'flex', gap: 14 }}>
            <Outcome tag="예 →" value={b.a} fieldKey={`branch_yes_${i}`} accent mode={mode}
              onChange={onBranchChange ? (v) => onBranchChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `branch_yes_${i}`} />
            <Outcome tag="아니오 →" value={b.b} fieldKey={`branch_no_${i}`} accent={false} mode={mode}
              onChange={onBranchChange ? (v) => onBranchChange(i, 'b', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `branch_no_${i}`} />
          </div>
        </div>
      ))}
    </div>
  )
}
