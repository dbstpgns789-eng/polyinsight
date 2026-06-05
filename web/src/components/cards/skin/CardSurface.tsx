// CardSurface — 뼈대의 루트 표면. 피부가 소유하는 배경/패딩/폰트/잉크 기본값.
// 뼈대는 <CardSurface>로 감싸기만 하고 배경·색을 직접 정의하지 않는다(강제규칙).

import type { ReactNode } from 'react'
import BgMotif from './BgMotif'

interface CardSurfaceProps {
  children: ReactNode
  motif?: boolean   // 배경 모티프 표시(기본 true)
}

export default function CardSurface({ children, motif = true }: CardSurfaceProps) {
  return (
    <div style={{
      width: '100%', height: '100%',
      position: 'relative', overflow: 'hidden',
      background: 'var(--set-bg-gradient)',
      fontFamily: 'var(--set-font)',
      color: 'var(--set-ink-strong)',
      boxSizing: 'border-box',
    }}>
      {motif && <BgMotif />}
      <div style={{
        position: 'relative', zIndex: 1,
        width: '100%', height: '100%',
        padding: 'var(--set-pad)',
        boxSizing: 'border-box',
        display: 'flex', flexDirection: 'column',
      }}>
        {children}
      </div>
    </div>
  )
}
