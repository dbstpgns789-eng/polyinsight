// ClippedReveal — 다음 장 넘기기 유도. 항목 열이 우측에서 의도적으로 잘리고 페이드. 색 소유는 피부.
// swipe_bait 뼈대가 조립해 쓴다. items = string[](우측이 잘려 보임), teaser=다음장 예고.
// fidelity: 잘리는 쪽에 핵심 수치/결론을 두지 않는다(다음 카드에서 공개) — 뼈대/콘텐츠 책임.
import EditableText from '../shared/EditableText'

interface Props {
  teaser: string
  items: string[]
  mode: 'edit' | 'render' | 'thumbnail'
  onTeaserChange?: (text: string) => void
  onItemChange?: (index: number, text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function ClippedReveal({ teaser, items, mode, onTeaserChange, onItemChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ fontFamily: 'var(--set-font)', position: 'relative' }}>
      {/* 잘리는 항목 열(가로 오버플로) */}
      <div style={{ display: 'flex', gap: 16, overflow: 'hidden', paddingRight: 40 }}>
        {items.map((it, i) => (
          <div key={i} style={{
            flex: '0 0 300px', background: 'var(--set-surface)',
            border: '1px solid var(--set-surface-border)', borderRadius: 'var(--set-radius-box)', padding: '24px 28px',
          }}>
            <EditableText
              fieldKey={`cut_${i}`} value={it} mode={mode} multiline
              onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `cut_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 600, lineHeight: 1.4, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
            />
          </div>
        ))}
      </div>
      {/* 우측 페이드(잘림 시각화) */}
      <div aria-hidden style={{
        position: 'absolute', top: 0, right: 0, width: 120, height: '100%',
        background: 'linear-gradient(90deg, transparent, var(--set-bg))', pointerEvents: 'none',
      }} />
      {/* 다음장 예고 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 26, color: 'var(--set-accent)' }}>
        <EditableText
          fieldKey="teaser" value={teaser} mode={mode}
          onFieldChange={onTeaserChange ? (_fk, v) => onTeaserChange(v) : undefined}
          onFieldFocus={onFieldFocus} focused={focusedField === 'teaser'}
          style={{ fontSize: 'var(--set-subhead)', fontWeight: 800, color: 'var(--set-accent)', wordBreak: 'keep-all' }}
        />
        <span aria-hidden style={{ fontSize: 'var(--set-subhead)', fontWeight: 900 }}>›</span>
      </div>
    </div>
  )
}
