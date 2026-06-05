// FeatureColumn — 세로 근거 목록(N개). 각 = accent 번호 + 제목 + 본문. 적응형.
import EditableText from '../shared/EditableText'

export interface FeatureItem {
  title: string
  body: string
}

interface FeatureColumnProps {
  items: FeatureItem[]
  mode: 'edit' | 'render' | 'thumbnail'
  onItemChange?: (index: number, field: 'title' | 'body', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function FeatureColumn({ items, mode, onItemChange, onFieldFocus, focusedField }: FeatureColumnProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28, fontFamily: 'var(--set-font)' }}>
      {items.map((it, i) => (
        <div key={i} style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
          <div style={{
            fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'var(--set-accent)',
            lineHeight: 1.1, flexShrink: 0, minWidth: 40,
          }}>{String(i + 1).padStart(2, '0')}</div>
          <div style={{ flex: 1 }}>
            <EditableText
              fieldKey={`reason_title_${i}`} value={it.title} mode={mode}
              onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'title', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `reason_title_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-subhead)', fontWeight: 800, color: 'var(--set-ink-strong)', wordBreak: 'keep-all', marginBottom: 8 }}
            />
            <EditableText
              fieldKey={`reason_body_${i}`} value={it.body} mode={mode} multiline
              onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'body', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `reason_body_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 400, lineHeight: 1.55, color: 'var(--set-ink-muted)', wordBreak: 'keep-all' }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
