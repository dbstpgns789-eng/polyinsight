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
  // 공중부양 화살표 방지: wrap 금지. ≤3개=가로 1행(→), ≥4개=세로 스택(↓).
  // 화살표는 항상 연속 노드 사이에만 — 행 경계에서 홀로 떨어지지 않는다. 높이 넘침은 CardSurface fit이 처리.
  const vertical = nodes.length >= 4
  return (
    <div style={{
      display: 'flex', flexDirection: vertical ? 'column' : 'row',
      alignItems: 'center', justifyContent: 'center',
      gap: vertical ? 10 : 14, fontFamily: 'var(--set-font)',
    }}>
      {nodes.map((node, i) => (
        <div key={i} style={{ display: 'contents' }}>
          <div style={{
            background: 'var(--set-surface)', border: '1.5px solid var(--set-surface-border)',
            borderRadius: 'var(--set-radius-box)', padding: '18px 24px',
            width: vertical ? '76%' : undefined,
            flex: vertical ? undefined : '1 1 0', minWidth: 0, boxSizing: 'border-box',
          }}>
            <EditableText
              fieldKey={`node_${i}`} value={node} mode={mode} multiline
              onFieldChange={onNodeChange ? (_fk, v) => onNodeChange(i, v) : undefined}
              onFieldFocus={onFieldFocus} focused={focusedField === `node_${i}`}
              style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 700, lineHeight: 1.35, color: 'var(--set-ink-strong)', wordBreak: 'keep-all', textAlign: 'center' }}
            />
          </div>
          {i < nodes.length - 1 && (
            <span aria-hidden style={{ fontSize: 'var(--set-subhead)', fontWeight: 900, color: 'var(--set-accent)', flexShrink: 0, lineHeight: 1 }}>
              {vertical ? '↓' : '→'}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
