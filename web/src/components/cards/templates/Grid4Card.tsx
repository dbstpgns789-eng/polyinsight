// Grid4Card — backend/templates/grid4.html 미러.
// 이미지 슬롯: bg + 4× 아이템 이미지 (item1_image ~ item4_image, 각 필드 URL 문자열).
// 필드: title, subtitle, item{1-4}_{label, sub, image}

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

const ITEM_INDICES = [1, 2, 3, 4] as const

export default function Grid4Card(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const subtitle = fieldValue(card, 'subtitle')
  const bgImage = card.image_url

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
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.65)', zIndex: 1 }} />

      <div style={{
        position: 'absolute', top: 60, right: 60,
        fontSize: 19, fontWeight: 700,
        color: 'rgba(255,255,255,0.25)',
        letterSpacing: '0.06em',
        zIndex: 20,
      }}>
        {String(card.card_num).padStart(2, '0')}
      </div>

      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        padding: '60px 60px 56px',
        zIndex: 10,
      }}>
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
            marginBottom: 8,
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
              marginBottom: 28,
              display: 'block',
            }}
          />
        )}

        <div style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gridTemplateRows: '1fr 1fr',
          gap: 14,
        }}>
          {ITEM_INDICES.map((n) => {
            const labelKey = `item${n}_label`
            const subKey = `item${n}_sub`
            const imgKey = `item${n}_image`
            const labelVal = fieldValue(card, labelKey)
            const subVal = fieldValue(card, subKey)
            const imgVal = fieldValue(card, imgKey)

            return (
              <div key={n} style={{
                background: 'rgba(255,255,255,0.95)',
                borderRadius: 20,
                overflow: 'hidden',
                display: 'flex', flexDirection: 'column',
              }}>
                <div style={{
                  height: 140, flexShrink: 0,
                  overflow: 'hidden',
                  background: 'var(--surface-card, #F8F9FA)',
                }}>
                  {imgVal && (
                    <img
                      src={imgVal}
                      alt=""
                      style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                    />
                  )}
                </div>
                <div style={{ padding: '16px 20px', flex: 1 }}>
                  <EditableText
                    fieldKey={labelKey}
                    value={labelVal}
                    mode={mode}
                    onFieldChange={onFieldChange}
                    onFieldFocus={onFieldFocus}
                    focused={focusedField === labelKey}
                    style={{
                      fontSize: 20, fontWeight: 700,
                      color: '#212529', marginBottom: 4,
                      wordBreak: 'keep-all',
                      display: 'block',
                    }}
                  />
                  {(subVal || mode === 'edit') && (
                    <EditableText
                      fieldKey={subKey}
                      value={subVal}
                      mode={mode}
                      onFieldChange={onFieldChange}
                      onFieldFocus={onFieldFocus}
                      focused={focusedField === subKey}
                      style={{
                        fontSize: 17, fontWeight: 400,
                        color: '#868E96', wordBreak: 'keep-all',
                        display: 'block',
                      }}
                    />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
