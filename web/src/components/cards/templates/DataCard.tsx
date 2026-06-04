// DataCard — backend/templates/data.html 미러.
// 이미지 슬롯: none (바 차트).
// 필드: title, data_unit?, bars (pipe-then-colon: "label:val|label:val"), bar_max (정규화 분모), source?

'use client'

import EditableText from '../shared/EditableText'
import { parsePipe, parseColon, joinColon, joinPipe } from '../shared/delimiters'
import type { CardComponentProps } from '../types'
import { fieldValue } from '../types'

const CHART_HEIGHT = 560

function numericPart(raw: string): number {
  // "23%" / "340만" / "73.2%" → 숫자만 추출. Jinja replace 동작 미러.
  const cleaned = raw.replace(/[만천%,\s]/g, '')
  const n = parseFloat(cleaned)
  return Number.isFinite(n) ? n : 0
}

export default function DataCard(props: CardComponentProps) {
  const { card, mode, onFieldChange, onFieldFocus, focusedField } = props
  const title = fieldValue(card, 'title')
  const dataUnit = fieldValue(card, 'data_unit')
  const bars = fieldValue(card, 'bars')
  const barMaxRaw = fieldValue(card, 'bar_max')
  const source = fieldValue(card, 'source')

  const barMax = Math.max(1, parseInt(barMaxRaw, 10) || 100)
  const items = parsePipe(bars).map((item) => parseColon(item))

  const handleBarPartChange = (idx: number, part: 'label' | 'sub') => (_fk: string, value: string) => {
    const current = [...items]
    if (!current[idx]) current[idx] = { label: '', sub: '' }
    const c = current[idx]
    const next = part === 'label'
      ? joinColon(value, c.sub)
      : joinColon(c.label, value)
    const reassembled = joinPipe(current.map((p, i) => i === idx ? next : joinColon(p.label, p.sub)))
    onFieldChange?.('bars', reassembled)
  }

  return (
    <div style={{
      width: '100%', height: '100%',
      background: 'var(--theme-bg, #111111)',
      display: 'flex', flexDirection: 'column',
      padding: '68px 64px 56px',
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute', top: 60, right: 60,
        fontSize: 19, fontWeight: 700,
        color: 'rgba(255,255,255,0.20)',
        letterSpacing: '0.06em',
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
          fontSize: 56, fontWeight: 900,
          lineHeight: 1.15, letterSpacing: '-0.02em',
          color: '#fff', wordBreak: 'keep-all',
          marginBottom: 8,
          display: 'block',
        }}
      />

      {(dataUnit || mode === 'edit') && (
        <EditableText
          fieldKey="data_unit"
          value={dataUnit}
          mode={mode}
          onFieldChange={onFieldChange}
          onFieldFocus={onFieldFocus}
          focused={focusedField === 'data_unit'}
          style={{
            fontSize: 19, fontWeight: 400,
            color: 'rgba(255,255,255,0.40)',
            marginBottom: 40,
            display: 'block',
          }}
        />
      )}

      {/* 바 차트 */}
      <div style={{
        flex: 1,
        display: 'flex', alignItems: 'flex-end',
        gap: 16, paddingBottom: 48,
        position: 'relative',
      }}>
        {/* Y축 구분선 */}
        <div style={{
          position: 'absolute', bottom: 48, left: 0, right: 0,
          height: 1, background: 'rgba(255,255,255,0.10)',
        }} />

        {items.map((item, idx) => {
          const valNum = numericPart(item.sub)
          const height = Math.round((valNum / barMax) * CHART_HEIGHT)
          return (
            <div key={idx} style={{
              flex: 1,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              gap: 10,
              position: 'relative',
            }}>
              <EditableText
                fieldKey={`bars.${idx}.sub`}
                value={item.sub}
                mode={mode}
                onFieldChange={handleBarPartChange(idx, 'sub')}
                onFieldFocus={onFieldFocus}
                focused={focusedField === `bars.${idx}.sub`}
                style={{
                  fontSize: 22, fontWeight: 800,
                  color: 'var(--theme-primary)',
                }}
              />
              <div style={{
                width: '100%',
                borderRadius: '10px 10px 0 0',
                background: 'var(--theme-primary)',
                opacity: 0.85,
                minHeight: 20,
                height: Math.max(20, height),
              }} />
              <div style={{ position: 'absolute', bottom: 16, width: '100%' }}>
                <EditableText
                  fieldKey={`bars.${idx}.label`}
                  value={item.label}
                  mode={mode}
                  onFieldChange={handleBarPartChange(idx, 'label')}
                  onFieldFocus={onFieldFocus}
                  focused={focusedField === `bars.${idx}.label`}
                  style={{
                    fontSize: 18, fontWeight: 500,
                    color: 'rgba(255,255,255,0.55)',
                    textAlign: 'center',
                    display: 'block',
                    width: '100%',
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {(source || mode === 'edit') && (
        <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.30)', textAlign: 'center', marginTop: 8 }}>
          출처:{' '}
          <EditableText
            fieldKey="source"
            value={source}
            mode={mode}
            onFieldChange={onFieldChange}
            onFieldFocus={onFieldFocus}
            focused={focusedField === 'source'}
            style={{ fontWeight: 400 }}
          />
        </div>
      )}
    </div>
  )
}
