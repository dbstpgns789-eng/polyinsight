// ProblemCard — backend/templates/problem.html 미러.
// 이미지 슬롯: bg (전체 배경, 어두운 오버레이).
// 필드: title, body, emphasis?

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function ProblemCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const body = fieldValue(card, 'body')
  const emphasis = fieldValue(card, 'emphasis')
  const bgImage = card.image_url

  return (
    <div style={{ width: '100%', height: '100%', background: '#111', position: 'relative' }}>
      {/* bg image + overlay */}
      {bgImage ? (
        <img
          src={bgImage}
          alt=""
          style={{
            position: 'absolute', inset: 0,
            width: '100%', height: '100%',
            objectFit: 'cover', objectPosition: 'center',
            zIndex: 0,
          }}
        />
      ) : mode === 'edit' && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <EditableImage
            slotKey="bg"
            mode={mode}
            onImageRequest={onImageRequest}
          />
        </div>
      )}
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.58)', zIndex: 1 }} />

      {/* body */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        padding: '72px 68px 64px',
        zIndex: 10,
      }}>
        <div style={{
          fontSize: 19, fontWeight: 700,
          color: 'rgba(255,255,255,0.25)',
          letterSpacing: '0.06em',
          alignSelf: 'flex-end',
          marginBottom: 'auto',
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
            fontSize: 68, fontWeight: 900,
            lineHeight: 1.12, letterSpacing: '-0.02em',
            color: '#fff', wordBreak: 'keep-all',
            marginBottom: 32,
          }}
        />

        <div style={{
          background: 'rgba(255,255,255,0.95)',
          borderRadius: 24,
          padding: '40px 48px',
          flexShrink: 0,
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
              fontSize: 26, fontWeight: 400,
              lineHeight: 1.75, color: '#212529',
              wordBreak: 'keep-all', textAlign: 'center',
              display: 'block',
            }}
          />
          {(emphasis || mode === 'edit') && (
            <EditableText
              fieldKey="emphasis"
              value={emphasis}
              mode={mode}
              onFieldChange={onFieldChange}
              onFieldFocus={onFieldFocus}
              focused={focusedField === 'emphasis'}
              style={{
                marginTop: 20,
                fontSize: 28, fontWeight: 700,
                color: 'var(--theme-primary)',
                textAlign: 'center',
                display: 'block',
              }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
