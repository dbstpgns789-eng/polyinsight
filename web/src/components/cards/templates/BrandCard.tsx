// BrandCard — backend/templates/brand.html 미러.
// 이미지 슬롯: none.
// 필드: tagline, body, cta?, footer_text?

'use client'

import EditableText from '../shared/EditableText'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

const DEFAULT_FOOTER = 'PolyInsight · AI Card News Generator'

export default function BrandCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const tagline = fieldValue(card, 'tagline')
  const body = fieldValue(card, 'body')
  const cta = fieldValue(card, 'cta')
  const footerText = fieldValue(card, 'footer_text') || DEFAULT_FOOTER

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: 'linear-gradient(135deg, #1A4C96 0%, #2563EB 50%, #0EA5A0 100%)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* main */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '72px 80px',
      }}>
        <div style={{
          border: '2px solid rgba(255,255,255,0.45)',
          borderRadius: 20,
          padding: '56px 64px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 28,
          width: '100%',
        }}>
          <EditableText
            fieldKey="tagline"
            value={tagline}
            mode={mode}
            multiline
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'tagline'}
            style={{
              fontSize: 48,
              fontWeight: 900,
              lineHeight: 1.2,
              letterSpacing: '-0.01em',
              color: '#fff',
              textAlign: 'center',
              wordBreak: 'keep-all',
              width: '100%',
            }}
          />
          <div style={{
            width: 56,
            height: 4,
            background: 'rgba(255,255,255,0.50)',
            borderRadius: 2,
          }} />
          <EditableText
            fieldKey="body"
            value={body}
            mode={mode}
            multiline
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'body'}
            style={{
              fontSize: 26,
              fontWeight: 400,
              lineHeight: 1.75,
              color: 'rgba(255,255,255,0.85)',
              textAlign: 'center',
              wordBreak: 'keep-all',
              width: '100%',
            }}
          />
          {(cta || mode === 'edit') && (
            <EditableText
              fieldKey="cta"
              value={cta}
              mode={mode}
              onFieldChange={onFieldChange}
              onFieldFocus={onFieldFocus}
              focused={focusedField === 'cta'}
              style={{
                fontSize: 18,
                fontWeight: 500,
                color: 'rgba(255,255,255,0.55)',
                marginTop: 8,
                textAlign: 'center',
              }}
            />
          )}
        </div>
      </div>

      {/* footer */}
      <div style={{
        height: 72,
        flexShrink: 0,
        background: 'rgba(0,0,0,0.30)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <EditableText
          fieldKey="footer_text"
          value={footerText}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'footer_text'}
          style={{
            fontSize: 18,
            fontWeight: 500,
            color: 'rgba(255,255,255,0.55)',
            letterSpacing: '0.02em',
          }}
        />
      </div>
    </div>
  )
}
