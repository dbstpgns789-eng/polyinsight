// ClosingCard — backend/templates/closing.html 미러.
// 이미지 슬롯: inner (선택적, 흰 카드 내부 240px).
// 필드: title_white, title_accent?, body, image_url (inner_image)

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function ClosingCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const titleWhite = fieldValue(card, 'title_white')
  const titleAccent = fieldValue(card, 'title_accent')
  const body = fieldValue(card, 'body')
  const innerImage = card.image_url

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: 'var(--theme-dark)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '72px 68px 64px',
      }}
    >
      {/* 아이콘 링 */}
      <div style={{
        width: 72,
        height: 72,
        borderRadius: '50%',
        background: 'rgba(255,255,255,0.12)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 24,
        flexShrink: 0,
      }}>
        <div style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: 'var(--theme-primary)',
        }} />
      </div>

      {/* 타이틀 (white + accent) */}
      <div style={{
        fontSize: 64,
        fontWeight: 900,
        lineHeight: 1.15,
        letterSpacing: '-0.02em',
        color: '#fff',
        wordBreak: 'keep-all',
        textAlign: 'center',
        marginBottom: 8,
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0 16px',
        justifyContent: 'center',
      }}>
        <EditableText
          fieldKey="title_white"
          value={titleWhite}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'title_white'}
        />
        {(titleAccent || mode === 'edit') && (
          <EditableText
            fieldKey="title_accent"
            value={titleAccent}
            mode={mode}
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'title_accent'}
            style={{ color: 'var(--theme-primary)' }}
          />
        )}
      </div>

      {/* 흰 카드 */}
      <div style={{
        width: '100%',
        background: 'rgba(255,255,255,0.97)',
        borderRadius: 24,
        padding: '36px 44px',
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        marginTop: 32,
        flex: 1,
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
            fontSize: 24,
            fontWeight: 400,
            lineHeight: 1.75,
            color: '#212529',
            wordBreak: 'keep-all',
            textAlign: 'center',
          }}
        />
        {(innerImage || mode === 'edit') && (
          <div style={{
            borderRadius: 16,
            overflow: 'hidden',
            flexShrink: 0,
            height: 240,
          }}>
            <EditableImage
              slotKey="inner"
              imageUrl={innerImage}
              mode={mode}
              onImageRequest={onImageRequest}
            />
          </div>
        )}
      </div>
    </div>
  )
}
