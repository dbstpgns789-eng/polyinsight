// CoverCard — backend/templates/cover.html 미러.
// 이미지 슬롯: bg.
// 필드: title (88px), subtitle (underline accent), edition?, org

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function CoverCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const title = fieldValue(card, 'title')
  const subtitle = fieldValue(card, 'subtitle')
  const edition = fieldValue(card, 'edition')
  const org = fieldValue(card, 'org')
  const bgImage = card.image_url

  return (
    <div style={{ width: '100%', height: '100%', background: '#0A0F1E', position: 'relative' }}>
      {/* bg image */}
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
          <EditableImage slotKey="bg" mode={mode} onImageRequest={onImageRequest} />
        </div>
      )}

      {/* overlay */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'linear-gradient(160deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.30) 50%, rgba(0,0,0,0.70) 100%)',
        zIndex: 1,
      }} />

      {/* dark triangle */}
      <div style={{
        position: 'absolute', bottom: 0, right: 0,
        width: 480, height: 480,
        background: 'rgba(10,15,30,0.85)',
        clipPath: 'polygon(100% 0, 100% 100%, 0 100%)',
        zIndex: 3,
      }} />

      {/* accent triangle */}
      <div style={{
        position: 'absolute', bottom: 0, right: 0,
        width: 220, height: 220,
        background: 'var(--theme-primary)',
        clipPath: 'polygon(100% 0, 100% 100%, 0 100%)',
        zIndex: 4,
      }} />

      {/* body */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center',
        padding: '80px 72px',
        zIndex: 10,
      }}>
        {(edition || mode === 'edit') && (
          <EditableText
            fieldKey="edition"
            value={edition}
            mode={mode}
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'edition'}
            style={{
              display: 'inline-block',
              padding: '8px 28px',
              border: '1.5px solid rgba(255,255,255,0.35)',
              borderRadius: 100,
              fontSize: 20, fontWeight: 600,
              color: 'rgba(255,255,255,0.80)',
              letterSpacing: '0.04em',
              marginBottom: 36,
              alignSelf: 'flex-start',
            }}
          />
        )}

        <EditableText
          fieldKey="title"
          value={title}
          mode={mode}
          multiline
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'title'}
          style={{
            fontSize: 88, fontWeight: 900,
            lineHeight: 1.08, letterSpacing: '-0.025em',
            color: '#fff', wordBreak: 'keep-all',
            marginBottom: 28, maxWidth: 820,
            display: 'block',
          }}
        />

        <EditableText
          fieldKey="subtitle"
          value={subtitle}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'subtitle'}
          style={{
            fontSize: 28, fontWeight: 500,
            color: 'rgba(255,255,255,0.80)',
            letterSpacing: '0.01em', wordBreak: 'keep-all',
            paddingBottom: 14,
            borderBottom: '3px solid var(--theme-primary)',
            display: 'inline-block',
            alignSelf: 'flex-start',
          }}
        />
      </div>

      {/* org footer */}
      <div style={{
        position: 'absolute', bottom: 44, left: 72,
        zIndex: 10,
      }}>
        <EditableText
          fieldKey="org"
          value={org}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'org'}
          style={{
            fontSize: 19, fontWeight: 600,
            color: 'rgba(255,255,255,0.50)',
            letterSpacing: '0.02em',
          }}
        />
      </div>
    </div>
  )
}
