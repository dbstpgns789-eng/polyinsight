// Compare2Card — backend/templates/compare2.html 미러.
// 이미지 슬롯: bg (블러 처리).
// 필드: title, subtitle?, label_a, label_b, points_a (dot), points_b (dot)

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import { parseDot, joinDot } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function Compare2Card(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const subtitle = fieldValue(card, 'subtitle')
  const labelA = fieldValue(card, 'label_a')
  const labelB = fieldValue(card, 'label_b')
  const pointsA = parseDot(fieldValue(card, 'points_a'))
  const pointsB = parseDot(fieldValue(card, 'points_b'))
  const bgImage = card.image_url

  const handlePointChange = (fieldKey: 'points_a' | 'points_b', points: string[]) => (idx: number) => (_fk: string, value: string) => {
    const next = [...points]
    next[idx] = value
    onFieldChange?.(fieldKey, joinDot(next))
  }

  return (
    <div style={{
      width: '100%', height: '100%',
      background: 'var(--theme-bg, #111111)',
      display: 'flex', flexDirection: 'column',
      padding: '64px 60px 56px',
      position: 'relative',
    }}>
      {/* center image */}
      {bgImage ? (
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <img
            src={bgImage}
            alt=""
            style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'blur(6px)', transform: 'scale(1.06)' }}
          />
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(26, 29, 46, 0.82)' }} />
        </div>
      ) : mode === 'edit' && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <EditableImage slotKey="bg" mode={mode} onImageRequest={onImageRequest} />
        </div>
      )}

      <div style={{
        position: 'absolute', top: 60, right: 60,
        fontSize: 19, fontWeight: 700,
        color: 'rgba(255,255,255,0.20)',
        letterSpacing: '0.06em',
        zIndex: 10,
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
          marginBottom: 10, position: 'relative', zIndex: 10,
          display: 'block',
        }}
      />

      {(subtitle || mode === 'edit') && (
        <EditableText
          fieldKey="subtitle"
          value={subtitle}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'subtitle'}
          style={{
            fontSize: 24, fontWeight: 600,
            color: 'var(--theme-primary)',
            marginBottom: 36, position: 'relative', zIndex: 10,
            display: 'block',
          }}
        />
      )}

      <div style={{
        flex: 1,
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: 16, position: 'relative', zIndex: 10,
      }}>
        {(['a', 'b'] as const).map((side) => {
          const label = side === 'a' ? labelA : labelB
          const points = side === 'a' ? pointsA : pointsB
          const labelFieldKey = side === 'a' ? 'label_a' : 'label_b'
          const pointsFieldKey = side === 'a' ? 'points_a' : 'points_b'
          const handler = handlePointChange(pointsFieldKey as 'points_a' | 'points_b', points)

          return (
            <div key={side} style={{
              background: 'rgba(255,255,255,0.96)',
              borderRadius: 22,
              padding: '32px 32px 36px',
              display: 'flex', flexDirection: 'column',
            }}>
              <EditableText
                fieldKey={labelFieldKey}
                value={label}
                mode={mode}
                onFieldChange={onFieldChange}
                onFieldFocus={onFieldFocus}
                focused={focusedField === labelFieldKey}
                style={{
                  display: 'inline-block',
                  padding: '8px 22px',
                  background: 'var(--theme-dark)',
                  borderRadius: 100,
                  fontSize: 20, fontWeight: 800,
                  color: '#fff', letterSpacing: '0.04em',
                  marginBottom: 24,
                  alignSelf: 'flex-start',
                }}
              />
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {points.map((pt, idx) => (
                  <li key={idx} style={{
                    fontSize: 22, fontWeight: 400,
                    color: '#212529', lineHeight: 1.5,
                    wordBreak: 'keep-all',
                    paddingLeft: 18, position: 'relative',
                  }}>
                    <span style={{
                      position: 'absolute', left: 0,
                      color: 'var(--theme-primary)', fontWeight: 700,
                    }}>-</span>
                    <EditableText
                      fieldKey={`${pointsFieldKey}.${idx}`}
                      value={pt}
                      mode={mode}
                      multiline
                      onFieldChange={handler(idx)}
                      onFieldFocus={onFieldFocus}
                      focused={focusedField === `${pointsFieldKey}.${idx}`}
                    />
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
