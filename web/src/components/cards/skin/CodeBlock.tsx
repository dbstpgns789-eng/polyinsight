// CodeBlock — 코드/프롬프트 스니펫 창. 상단 신호등 + 언어 라벨 + 모노스페이스 본문. 색 소유는 피부.
// terminal_block 뼈대가 조립해 쓴다. 다크 강제 대신 set 표면 토큰 + 모노스페이스로 '코드' 시그널.
import EditableText from '../shared/EditableText'

interface Props {
  code: string
  lang: string
  mode: 'edit' | 'render' | 'thumbnail'
  onCodeChange?: (text: string) => void
  onLangChange?: (text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}

export default function CodeBlock({ code, lang, mode, onCodeChange, onLangChange, onFieldFocus, focusedField }: Props) {
  return (
    <div style={{
      fontFamily: 'var(--set-font)', borderRadius: 'var(--set-radius-box)', overflow: 'hidden',
      border: '1px solid var(--set-surface-border)', background: 'var(--set-surface)',
    }}>
      {/* 헤더 바 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14, padding: '16px 22px',
        borderBottom: '1px solid var(--set-surface-border)',
      }}>
        <div style={{ display: 'flex', gap: 8 }} aria-hidden>
          {['var(--set-ink-faint)', 'var(--set-ink-faint)', 'var(--set-accent)'].map((c, i) => (
            <span key={i} style={{ width: 14, height: 14, borderRadius: '50%', background: c }} />
          ))}
        </div>
        <EditableText
          fieldKey="lang" value={lang} mode={mode}
          onFieldChange={onLangChange ? (_fk, v) => onLangChange(v) : undefined}
          onFieldFocus={onFieldFocus} focused={focusedField === 'lang'}
          style={{ fontSize: 'var(--set-caption)', fontWeight: 700, letterSpacing: '0.04em', color: 'var(--set-ink-muted)' }}
        />
      </div>
      {/* 코드 본문 */}
      <div style={{ padding: '26px 28px' }}>
        <EditableText
          fieldKey="code" value={code} mode={mode} multiline
          onFieldChange={onCodeChange ? (_fk, v) => onCodeChange(v) : undefined}
          onFieldFocus={onFieldFocus} focused={focusedField === 'code'}
          style={{
            display: 'block',
            fontFamily: "var(--set-mono, 'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace)",
            fontSize: 'var(--set-body)', fontWeight: 500, lineHeight: 1.6,
            color: 'var(--set-ink-strong)', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          }}
        />
      </div>
    </div>
  )
}
