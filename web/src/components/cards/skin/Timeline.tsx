// Timeline — 세로 타임라인(N단계). 각 노드 = 점 + 연도(accent) + 제목 + 설명. 색 소유는 피부.
// timeline 뼈대가 조립해 쓴다. events = TableRow(attr=연도, a=제목, b=설명).
import EditableText from '../shared/EditableText'
import type { TableRow } from './parse'

interface Props {
  events: TableRow[]
  mode: 'edit' | 'render' | 'thumbnail'
  onEventChange?: (index: number, field: 'attr' | 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function Timeline({ events, mode, onEventChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', fontFamily: 'var(--set-font)' }}>
      {events.map((e, i) => (
        <div key={i} style={{ display: 'flex', gap: 22, alignItems: 'stretch' }}>
          {/* 레일 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, width: 22 }}>
            <div style={{ width: 18, height: 18, borderRadius: '50%', background: 'var(--set-accent)', flexShrink: 0, marginTop: 4 }} />
            {i < events.length - 1 && <div style={{ flex: 1, width: 3, background: 'var(--set-surface-border)', marginTop: 4 }} />}
          </div>
          <div style={{ flex: 1, paddingBottom: i < events.length - 1 ? 26 : 0, minWidth: 0 }}>
            <EditableText
              fieldKey={`tl_year_${i}`} value={e.attr} mode={mode}
              onFieldChange={onEventChange ? (_fk, v) => onEventChange(i, 'attr', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `tl_year_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-caption)', fontWeight: 800, letterSpacing: '0.04em', color: 'var(--set-accent)', marginBottom: 4 }}
            />
            <EditableText
              fieldKey={`tl_title_${i}`} value={e.a} mode={mode}
              onFieldChange={onEventChange ? (_fk, v) => onEventChange(i, 'a', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `tl_title_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-subhead)', fontWeight: 800, color: 'var(--set-ink-strong)', wordBreak: 'keep-all', marginBottom: 4 }}
            />
            <EditableText
              fieldKey={`tl_desc_${i}`} value={e.b} mode={mode} multiline
              onFieldChange={onEventChange ? (_fk, v) => onEventChange(i, 'b', v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `tl_desc_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 400, lineHeight: 1.5, color: 'var(--set-ink-muted)', wordBreak: 'keep-all' }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
