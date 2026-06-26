import type { ReactNode } from 'react'
import BgMotif from './BgMotif'
import { useImageMode } from './imageModeContext'

// CardSurface — 뼈대의 루트 표면. 피부가 소유하는 배경/패딩/폰트/잉크 기본값.
// 뼈대는 <CardSurface>로 감싸기만 하고 배경·색을 직접 정의하지 않는다(강제규칙).
// 단, image_mode가 backdrop/ghost일 때는 CardFrame의 이미지 레이어가 보이도록 투명화된다.

interface CardSurfaceProps {
  children: ReactNode
  motif?: boolean
}

export default function CardSurface({ children, motif = true }: CardSurfaceProps) {
  const imageMode = useImageMode()
  // ghost 모드는 CardFrame의 이미지 opacity(0.09 고정)에 의존해 잉크색 대비를 유지한다.
  const isOverlay = imageMode === 'backdrop' || imageMode === 'ghost'

  return (
    <div style={{
      width: '100%', height: '100%',
      position: 'relative', overflow: 'hidden',
      background: isOverlay ? 'transparent' : 'var(--set-bg-gradient)',
      fontFamily: 'var(--set-font)',
      color: 'var(--set-ink-strong)',
      boxSizing: 'border-box',
      boxShadow: isOverlay ? 'none' : 'var(--set-card-glow, none)',
    }}>
      {motif && !isOverlay && <BgMotif />}
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
