// ChatLog — 대화형 메신저 버블(N개). 발화자에 따라 좌/우 정렬·색 분기. 색 소유는 피부.
// chat 뼈대가 조립해 쓴다. messages = Pair(a=발화자, b=메시지).
// 발화자 'a'/'질문자'(첫 등장) → 좌측 surface, 'b'/응답 → 우측 accent.
import EditableText from '../shared/EditableText'
import type { Pair } from './parse'

export default function ChatLog({ messages, mode, onMsgChange, onFieldFocus, focusedField }: {
  messages: Pair[]
  mode: 'edit' | 'render' | 'thumbnail'
  onMsgChange?: (index: number, text: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focusedField?: string | null
}) {
  // 첫 발화자를 좌측 기준으로 잡고, 다른 발화자는 우측.
  const firstSpeaker = messages[0]?.a?.trim().toLowerCase() ?? 'a'
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, fontFamily: 'var(--set-font)' }}>
      {messages.map((m, i) => {
        const isRight = (m.a?.trim().toLowerCase() ?? '') !== firstSpeaker
        return (
          <div key={i} style={{ display: 'flex', justifyContent: isRight ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '78%',
              background: isRight ? 'var(--set-accent)' : 'var(--set-surface)',
              border: isRight ? 'none' : '1px solid var(--set-surface-border)',
              color: isRight ? 'var(--set-accent-ink)' : 'var(--set-ink-strong)',
              borderRadius: 22,
              borderBottomRightRadius: isRight ? 6 : 22,
              borderBottomLeftRadius: isRight ? 22 : 6,
              padding: '18px 24px',
            }}>
              <EditableText
                fieldKey={`chat_${i}`} value={m.b} mode={mode} multiline
                onFieldChange={onMsgChange ? (_fk, v) => onMsgChange(i, v) : undefined}
                onFieldFocus={onFieldFocus} focused={focusedField === `chat_${i}`}
                style={{ display: 'block', fontSize: 'var(--set-body)', fontWeight: 500, lineHeight: 1.45, wordBreak: 'keep-all', color: 'inherit' }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
