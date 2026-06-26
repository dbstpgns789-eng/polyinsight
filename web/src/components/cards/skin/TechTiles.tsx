// TechTiles — 기술/도구 타일 격자(N개). 각 = 아이콘 글리프 + 이름. 색 소유는 피부.
// tech_grid 뼈대가 조립해 쓴다. items = Pair(a=이름, b=아이콘ID).
// 아이콘ID는 작은 화이트리스트(없으면 이름 첫 글자 폴백) — 에셋 창고 ID 참조 개념.
import EditableText from '../shared/EditableText'
import type { Pair } from './parse'

const ICON_GLYPHS: Record<string, string> = {
  ai: '🧠', ml: '🧠', data: '📊', chart: '📈', code: '⌨️', cloud: '☁️',
  db: '🗄️', sensor: '📡', chip: '🔬', bio: '🧬', chem: '⚗️', energy: '⚡',
  robot: '🤖', web: '🌐', mobile: '📱', lock: '🔒', gear: '⚙️', flask: '🧪',
}

function glyph(iconId: string, name: string): string {
  const key = iconId.trim().toLowerCase()
  if (ICON_GLYPHS[key]) return ICON_GLYPHS[key]
  return (name.trim()[0] ?? '▣').toUpperCase()
}

interface Props {
  items: Pair[]
  mode: 'edit' | 'render' | 'thumbnail'
  onItemChange?: (index: number, field: 'a' | 'b', text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function TechTiles({ items, mode, onItemChange, onFieldFocus, focusedField }: Props) {
  const cols = items.length <= 3 ? Math.max(1, items.length) : 3
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 'var(--set-gap)', fontFamily: 'var(--set-font)' }}>
      {items.map((it, i) => (
        <div key={i} style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, textAlign: 'center',
          background: 'var(--set-surface)', border: '1px solid var(--set-surface-border)',
          borderRadius: 'var(--set-radius-box)', padding: '28px 18px',
        }}>
          <div aria-hidden style={{
            width: 64, height: 64, borderRadius: 16, flexShrink: 0,
            background: 'var(--set-accent)', color: 'var(--set-accent-ink)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 'var(--set-subhead)', fontWeight: 900,
          }}>{glyph(it.b, it.a)}</div>
          <EditableText
            fieldKey={`tech_name_${i}`} value={it.a} mode={mode}
            onFieldChange={onItemChange ? (_fk, v) => onItemChange(i, 'a', v) : undefined}
            onFieldFocus={onFieldFocus} focused={focusedField === `tech_name_${i}`}
            style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 700, color: 'var(--set-ink-strong)', wordBreak: 'keep-all' }}
          />
        </div>
      ))}
    </div>
  )
}
