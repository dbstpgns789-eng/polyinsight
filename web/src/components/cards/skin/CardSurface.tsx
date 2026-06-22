import type { ReactNode } from 'react'
import BgMotif from './BgMotif'
import { useImageMode } from './imageModeContext'

interface CardSurfaceProps {
  children: ReactNode
  motif?: boolean
}

export default function CardSurface({ children, motif = true }: CardSurfaceProps) {
  const imageMode = useImageMode()
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
