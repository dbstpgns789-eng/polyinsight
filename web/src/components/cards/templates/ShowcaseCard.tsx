// ShowcaseCard — backend/templates/showcase.html 미러 (inset_top 모드).
// 이미지 슬롯: inset_top (상단 420px).
// 필드: title, body, icon1/2/3 (colon parsed: "label:sub")

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import { parseColon, joinColon } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

const ICON_KEYS = ['icon1', 'icon2', 'icon3'] as const

export default function ShowcaseCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const body = fieldValue(card, 'body')
  const bgImage = card.image_url

  const handlePartChange = (iconKey: string, part: 'label' | 'sub') => (subkey: string, value: string) => {
    const current = parseColon(fieldValue(card, iconKey))
    const next = part === 'label'
      ? joinColon(value, current.sub)
      : joinColon(current.label, value)
    onFieldChange?.(iconKey, next)
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#111', position: 'relative' }}>
      {/* 상단 이미지 (420px) */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 420, overflow: 'hidden' }}>
        {bgImage ? (
          <>
            <img src={bgImage} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            <div style={{
              position: 'absolute', inset: 0,
              background: 'linear-gradient(180deg, rgba(0,0,0,0.40) 0%, rgba(0,0,0,0.70) 100%)',
            }} />
          </>
        ) : mode === 'edit' ? (
          <EditableImage slotKey="inset_top" mode={mode} onImageRequest={onImageRequest} />
        ) : null}
      </div>

      {/* 상단 텍스트 (이미지 위) */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        padding: '56px 64px 0',
        zIndex: 5,
        pointerEvents: 'none',
      }}>
        <div style={{
          fontSize: 19, fontWeight: 700,
          color: 'rgba(255,255,255,0.25)',
          letterSpacing: '0.06em',
          textAlign: 'right',
          marginBottom: 12,
        }}>
          {String(card.card_num).padStart(2, '0')}
        </div>
        <div style={{ pointerEvents: 'auto' }}>
          <EditableText
            fieldKey="title"
            value={title}
            mode={mode}
            multiline
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'title'}
            style={{
              fontSize: 56, fontWeight: 900,
              lineHeight: 1.15, letterSpacing: '-0.02em',
              color: '#fff', wordBreak: 'keep-all',
              display: 'block',
            }}
          />
        </div>
      </div>

      {/* 하단 흰 카드 (680px) */}
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        height: 680,
        background: 'rgba(255,255,255,0.97)',
        borderRadius: '28px 28px 0 0',
        padding: '36px 56px 48px',
        display: 'flex', flexDirection: 'column',
        zIndex: 10,
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
            wordBreak: 'keep-all',
            marginBottom: 32,
            flex: 1,
          }}
        />

        {/* 3-icon footer */}
        <div style={{
          display: 'flex', gap: 16,
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          {ICON_KEYS.map((iconKey) => {
            const raw = fieldValue(card, iconKey)
            const { label, sub } = parseColon(raw)
            if (!raw && mode !== 'edit') return null

            return (
              <div key={iconKey} style={{
                flex: 1, display: 'flex', flexDirection: 'column',
                alignItems: 'center', gap: 10,
              }}>
                <div style={{
                  width: 80, height: 80, borderRadius: '50%',
                  background: '#F0F0F0',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%',
                    background: 'var(--theme-dark)',
                  }} />
                </div>
                <EditableText
                  fieldKey={`${iconKey}.label`}
                  value={label}
                  mode={mode}
                  onFieldChange={handlePartChange(iconKey, 'label')}
                  onFieldFocus={onFieldFocus}
                  focused={focusedField === `${iconKey}.label`}
                  style={{
                    fontSize: 20, fontWeight: 700,
                    color: '#212529', textAlign: 'center',
                    wordBreak: 'keep-all',
                  }}
                />
                <EditableText
                  fieldKey={`${iconKey}.sub`}
                  value={sub}
                  mode={mode}
                  onFieldChange={handlePartChange(iconKey, 'sub')}
                  onFieldFocus={onFieldFocus}
                  focused={focusedField === `${iconKey}.sub`}
                  style={{
                    fontSize: 16, fontWeight: 400,
                    color: '#868E96', textAlign: 'center',
                    wordBreak: 'keep-all',
                  }}
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
