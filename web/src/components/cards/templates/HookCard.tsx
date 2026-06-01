// HookCard — backend/templates/hook.html 미러.
// 이미지 슬롯: bg (블러 처리로 텍스트 우선).
// 필드: title (question), highlight?, body?, source_credit?

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function HookCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const highlight = fieldValue(card, 'highlight')
  const body = fieldValue(card, 'body')
  const sourceCredit = fieldValue(card, 'source_credit')
  const bgImage = card.image_url

  return (
    <div style={{ width: '100%', height: '100%', background: '#111', position: 'relative' }}>
      {/* bg image (blurred) */}
      {bgImage ? (
        <img
          src={bgImage}
          alt=""
          style={{
            position: 'absolute', inset: 0,
            width: '100%', height: '100%',
            objectFit: 'cover', objectPosition: 'center',
            zIndex: 0,
            filter: 'blur(8px)',
            transform: 'scale(1.08)',
          }}
        />
      ) : mode === 'edit' && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          <EditableImage slotKey="bg" mode={mode} onImageRequest={onImageRequest} />
        </div>
      )}

      {/* overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0.50) 40%, rgba(0,0,0,0.78) 100%)',
        zIndex: 1,
      }} />

      {/* body */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '72px 72px 64px',
        zIndex: 10,
      }}>
        <div style={{
          fontSize: 19, fontWeight: 700,
          color: 'rgba(255,255,255,0.30)',
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
            fontSize: 64, fontWeight: 900,
            lineHeight: 1.15, letterSpacing: '-0.02em',
            color: '#fff', wordBreak: 'keep-all',
            maxWidth: 900,
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {(highlight || mode === 'edit') && (
            <EditableText
              fieldKey="highlight"
              value={highlight}
              mode={mode}
              multiline
              onFieldChange={onFieldChange}
              onFieldFocus={onFieldFocus}
              focused={focusedField === 'highlight'}
              style={{
                fontSize: 32, fontWeight: 700,
                color: 'var(--theme-primary)',
                lineHeight: 1.4, wordBreak: 'keep-all',
                display: 'block',
              }}
            />
          )}
          {(body || mode === 'edit') && (
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
                color: 'rgba(255,255,255,0.70)',
                lineHeight: 1.65, wordBreak: 'keep-all',
                display: 'block',
              }}
            />
          )}
          {(sourceCredit || mode === 'edit') && (
            <div style={{
              fontSize: 17, fontWeight: 400,
              color: 'rgba(255,255,255,0.30)',
            }}>
              이미지 출처:{' '}
              <EditableText
                fieldKey="source_credit"
                value={sourceCredit}
                mode={mode}
                onFieldChange={onFieldChange}
                onFieldFocus={onFieldFocus}
                focused={focusedField === 'source_credit'}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
