// CardRenderer — card.template_type을 보고 적절한 React 컴포넌트를 dispatch.
//
// Phase 1: 모든 템플릿에 대해 "구현 대기 중" placeholder.
// Phase 2: CARD_COMPONENTS 레지스트리에 12개 템플릿 등록되면 자동으로 dispatch.

'use client'

import CardFrame from './CardFrame'
import { CARD_COMPONENTS } from './index'
import { FieldStylesProvider } from './skin/fieldStyleContext'
import { getSet } from './skin/sets'
import type { CardComponentProps } from './types'

interface CardRendererProps extends CardComponentProps {
  scale?: number
  bgColor?: string
  accentColor?: string
  fontPairing?: string
  setKey?: string
}

export default function CardRenderer({ scale = 1, bgColor, accentColor, fontPairing, setKey, ...props }: CardRendererProps) {
  const { card } = props
  const Component = CARD_COMPONENTS[card.template_type]

  return (
    <FieldStylesProvider value={card.field_styles ?? {}}>
      <CardFrame set={getSet(setKey)} bgColor={bgColor} accentColor={accentColor} fontPairing={fontPairing} scale={scale}>
        {Component ? <Component {...props} /> : <UnimplementedTemplate templateType={card.template_type} />}
      </CardFrame>
    </FieldStylesProvider>
  )
}

function UnimplementedTemplate({ templateType }: { templateType: string }) {
  return (
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--set-bg, #111111)',
      color: '#666', fontFamily: 'Noto Sans KR, sans-serif', gap: 16,
    }}>
      <div style={{ fontSize: 80 }}>🚧</div>
      <div style={{ fontSize: 40, fontWeight: 700 }}>{templateType}</div>
      <div style={{ fontSize: 22, color: '#999' }}>Phase 2에서 구현 예정</div>
    </div>
  )
}
