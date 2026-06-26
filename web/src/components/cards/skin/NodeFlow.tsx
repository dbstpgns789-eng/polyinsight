// NodeFlow — 모듈 노드 + 화살표 흐름(데이터패스). 노드 박스를 흐름선으로 연결. 색 소유는 피부.
// datapath 뼈대가 조립해 쓴다. nodes = string[]. 2~3개씩 줄바꿈되는 가로 흐름.
import EditableText from '../shared/EditableText'

interface Props {
  nodes: string[]
  mode: 'edit' | 'render' | 'thumbnail'
  onNodeChange?: (index: number, text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function NodeFlow({ nodes, mode, onNodeChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'center', gap: 16, fontFamily: 'var(--set-font)' }}>
      {nodes.map((node, i) => (
        <div key={i} style={{ display: 'contents' }}>
          <div style={{
            background: 'var(--set-surface)', border: '1.5px solid var(--set-surface-border)',
            borderRadius: 'var(--set-radius-box)', padding: '20px 26px', maxWidth: 280,
          }}>
            <EditableText
              fieldKey={`node_${i}`} value={node} mode={mode} multiline
              onFieldChange={onNodeChange ? (_fk, v) => onNodeChange(i, v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `node_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 700, lineHeight: 1.35, color: 'var(--set-ink-strong)', wordBreak: 'keep-all', textAlign: 'center' }}
            />
          </div>
          {i < nodes.length - 1 && (
            <span aria-hidden style={{ fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'var(--set-accent)', flexShrink: 0 }}>→</span>
          )}
        </div>
      ))}
    </div>
  )
}
