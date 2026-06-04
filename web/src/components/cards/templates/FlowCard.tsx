// FlowCard — backend/templates/flow.html 미러.
// 이미지 슬롯: bg.
// 필드: title, steps_text (dot 또는 newline 구분된 단계 목록)

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import { joinDot } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

function parseSteps(value: string): string[] {
  if (!value) return []
  if (value.includes('·')) {
    return value.split('·').map((s) => s.trim()).filter(Boolean)
  }
  return value.split(/\n/).map((s) => s.trim()).filter(Boolean)
}

export default function FlowCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const stepsRaw = fieldValue(card, 'steps_text')
  const bgImage = card.image_url
  const steps = parseSteps(stepsRaw)

  const handleStepChange = (idx: number) => (_fk: string, value: string) => {
    const next = [...steps]
    next[idx] = value
    onFieldChange?.('steps_text', joinDot(next))
  }

  return (
    <div style={{ width: '100%', height: '100%', background: 'var(--theme-bg, #111111)', position: 'relative' }}>
      {bgImage ? (
        <img
          src={bgImage}
          alt=""
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', zIndex: 0 }}
        />
      ) : mode === 'edit' && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <EditableImage slotKey="bg" mode={mode} onImageRequest={onImageRequest} />
        </div>
      )}
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 1 }} />

      <div style={{
        position: 'absolute', top: 60, right: 60,
        fontSize: 19, fontWeight: 700,
        color: 'rgba(255,255,255,0.20)',
        letterSpacing: '0.06em',
        zIndex: 20,
      }}>
        {String(card.card_num).padStart(2, '0')}
      </div>

      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        padding: '68px 68px 60px',
        zIndex: 10,
      }}>
        <div style={{
          fontSize: 18, fontWeight: 600,
          color: 'var(--theme-primary)',
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          marginBottom: 10,
        }}>
          Process Flow
        </div>

        <EditableText
          fieldKey="title"
          value={title}
          mode={mode}
          multiline
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'title'}
          style={{
            fontSize: 52, fontWeight: 900,
            lineHeight: 1.15, letterSpacing: '-0.02em',
            color: '#fff', wordBreak: 'keep-all',
            marginBottom: 40,
            display: 'block',
          }}
        />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 0 }}>
          {steps.map((step, idx) => (
            <div key={idx}>
              {idx > 0 && (
                <div style={{
                  width: 2, height: 24,
                  background: 'var(--theme-primary)',
                  opacity: 0.30, marginLeft: 29,
                }} />
              )}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24 }}>
                <div style={{
                  width: 60, height: 60, borderRadius: '50%',
                  background: 'var(--theme-primary)',
                  color: '#fff', fontSize: 24, fontWeight: 900,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  {idx + 1}
                </div>
                <div style={{ flex: 1, paddingTop: 12 }}>
                  <EditableText
                    fieldKey={`steps_text.${idx}`}
                    value={step}
                    mode={mode}
                    multiline
                    onFieldChange={handleStepChange(idx)}
                    onFieldFocus={onFieldFocus}
                    focused={focusedField === `steps_text.${idx}`}
                    style={{
                      fontSize: 26, fontWeight: 500,
                      color: 'rgba(255,255,255,0.90)',
                      lineHeight: 1.55, wordBreak: 'keep-all',
                      display: 'block',
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
