// Circle3Card — backend/templates/circle3.html 미러.
// 이미지 슬롯: bg.
// 필드: title, body, c1/c2/c3 (colon parsed: "텍스트:서브")

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import { parseColon, joinColon } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

const CIRCLE_KEYS = ['c1', 'c2', 'c3'] as const

export default function Circle3Card(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const body = fieldValue(card, 'body')
  const bgImage = card.image_url

  const handlePartChange = (circleKey: string, part: 'label' | 'sub') => (_fk: string, value: string) => {
    const current = parseColon(fieldValue(card, circleKey))
    const next = part === 'label'
      ? joinColon(value, current.sub)
      : joinColon(current.label, value)
    onFieldChange?.(circleKey, next)
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
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.60)', zIndex: 1 }} />

      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        padding: '64px 68px 60px',
        zIndex: 10,
      }}>
        <div style={{
          fontSize: 19, fontWeight: 700,
          color: 'rgba(255,255,255,0.25)',
          letterSpacing: '0.06em',
          alignSelf: 'flex-end',
        }}>
          {String(card.card_num).padStart(2, '0')}
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
            fontSize: 60, fontWeight: 900,
            lineHeight: 1.15, letterSpacing: '-0.02em',
            color: '#fff', wordBreak: 'keep-all',
            marginTop: 16, marginBottom: 40,
            display: 'block',
          }}
        />

        {/* circles */}
        <div style={{
          display: 'flex', gap: 20,
          justifyContent: 'center',
          marginBottom: 32,
          flexShrink: 0,
        }}>
          {CIRCLE_KEYS.map((circleKey) => {
            const { label, sub } = parseColon(fieldValue(card, circleKey))
            return (
              <div key={circleKey} style={{
                width: 200, height: 200, borderRadius: '50%',
                background: 'var(--theme-dark)',
                border: '2px solid rgba(255,255,255,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexDirection: 'column', gap: 4,
                flexShrink: 0,
              }}>
                <EditableText
                  fieldKey={`${circleKey}.label`}
                  value={label}
                  mode={mode}
                  multiline
                  onFieldChange={handlePartChange(circleKey, 'label')}
                  onFieldFocus={onFieldFocus}
                  focused={focusedField === `${circleKey}.label`}
                  style={{
                    fontSize: 26, fontWeight: 800,
                    color: '#fff', textAlign: 'center',
                    lineHeight: 1.3, wordBreak: 'keep-all',
                    padding: '0 12px',
                  }}
                />
                {(sub || mode === 'edit') && (
                  <EditableText
                    fieldKey={`${circleKey}.sub`}
                    value={sub}
                    mode={mode}
                    onFieldChange={handlePartChange(circleKey, 'sub')}
                    onFieldFocus={onFieldFocus}
                    focused={focusedField === `${circleKey}.sub`}
                    style={{
                      fontSize: 18, fontWeight: 400,
                      color: 'rgba(255,255,255,0.60)',
                      textAlign: 'center',
                    }}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* body white card */}
        <div style={{
          background: 'rgba(255,255,255,0.95)',
          borderRadius: 22,
          padding: '32px 44px',
          flex: 1,
          display: 'flex', alignItems: 'center',
        }}>
          <EditableText
            fieldKey="body"
            value={body}
            mode={mode}
            multiline
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'body'}
            style={{
              fontSize: 24, fontWeight: 400,
              lineHeight: 1.75, color: '#212529',
              wordBreak: 'keep-all', textAlign: 'center',
              width: '100%',
              display: 'block',
            }}
          />
        </div>
      </div>
    </div>
  )
}
