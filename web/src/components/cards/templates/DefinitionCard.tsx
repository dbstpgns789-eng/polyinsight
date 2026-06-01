// DefinitionCard — backend/templates/definition.html 미러 (inset_right 모드).
// 이미지 슬롯: inset_right (우측 420px 패널).
// 필드: term (72px), term_detail?, definition_text, body?

'use client'

import EditableText from '../shared/EditableText'
import EditableImage from '../shared/EditableImage'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

export default function DefinitionCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField, onImageRequest } = props
  const term = fieldValue(card, 'term')
  const termDetail = fieldValue(card, 'term_detail')
  const definitionText = fieldValue(card, 'definition_text')
  const body = fieldValue(card, 'body')
  const bgImage = card.image_url
  const hasImage = !!bgImage || mode === 'edit'

  return (
    <div style={{ width: '100%', height: '100%', background: '#0F1117', position: 'relative' }}>
      {/* 우측 이미지 패널 */}
      {hasImage && (
        <div style={{
          position: 'absolute', top: 0, right: 0, bottom: 0,
          width: 420, overflow: 'hidden', zIndex: 0,
        }}>
          {bgImage ? (
            <>
              <img
                src={bgImage}
                alt=""
                style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center', display: 'block' }}
              />
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(90deg, rgba(15,17,23,1) 0%, rgba(15,17,23,0.30) 40%, rgba(15,17,23,0) 100%)',
              }} />
            </>
          ) : mode === 'edit' ? (
            <EditableImage slotKey="inset_right" mode={mode} onImageRequest={onImageRequest} />
          ) : null}
        </div>
      )}

      {/* card_num 우상단 */}
      <div style={{
        position: 'absolute', top: 60, right: 60,
        fontSize: 19, fontWeight: 700,
        color: 'rgba(255,255,255,0.20)',
        letterSpacing: '0.06em',
        zIndex: 20,
      }}>
        {String(card.card_num).padStart(2, '0')}
      </div>

      {/* 좌측 텍스트 */}
      <div style={{
        position: 'absolute', inset: 0,
        right: hasImage ? 420 : 0,
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center',
        padding: hasImage ? '72px 56px 72px 72px' : '72px',
        zIndex: 10,
      }}>
        <EditableText
          fieldKey="term"
          value={term}
          mode={mode}
          multiline
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'term'}
          style={{
            fontSize: 72, fontWeight: 900,
            lineHeight: 1.1, letterSpacing: '-0.025em',
            color: '#fff', wordBreak: 'keep-all',
            marginBottom: 4,
            display: 'block',
          }}
        />
        {(termDetail || mode === 'edit') && (
          <EditableText
            fieldKey="term_detail"
            value={termDetail}
            mode={mode}
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'term_detail'}
            style={{
              fontSize: 21, fontWeight: 400,
              color: 'rgba(255,255,255,0.40)',
              marginBottom: 24,
              display: 'block',
            }}
          />
        )}
        <div style={{
          width: 56, height: 5,
          background: 'var(--theme-primary)',
          borderRadius: 3,
          marginBottom: 28,
        }} />
        <div style={{
          fontSize: 27, fontWeight: 500,
          color: 'rgba(255,255,255,0.90)',
          lineHeight: 1.55, wordBreak: 'keep-all',
          marginBottom: 28,
          display: 'flex',
          gap: 8,
        }}>
          <span>:</span>
          <EditableText
            fieldKey="definition_text"
            value={definitionText}
            mode={mode}
            multiline
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'definition_text'}
            style={{ flex: 1 }}
          />
        </div>
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
              fontSize: 21, fontWeight: 400,
              color: 'rgba(255,255,255,0.58)',
              lineHeight: 1.75, wordBreak: 'keep-all',
              display: 'block',
            }}
          />
        )}
      </div>
    </div>
  )
}
