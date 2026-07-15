'use client'
import { type ReactNode, useLayoutEffect, useRef } from 'react'
import BgMotif from './BgMotif'
import { useImageMode } from './imageModeContext'

// CardSurface — 뼈대의 루트 표면. 피부가 소유하는 배경/패딩/폰트/잉크 기본값.
// 뼈대는 <CardSurface>로 감싸기만 하고 배경·색을 직접 정의하지 않는다(강제규칙).
// 단, image_mode가 backdrop/ghost일 때는 CardFrame의 이미지 레이어가 보이도록 투명화된다.
//
// 동적 맞춤(fit): 본문이 1080 카드를 넘치면(S6가 길이 상한을 무시) 잘린 채 PNG로 구워지는
// 참사를 막기 위해, 내부 컬럼의 오버플로를 측정해 transform: scale로 한 번에 줄여 담는다.
// 폰트·토큰·skin·contenteditable 로직을 건드리지 않는 가장 안전한 지점(공통 루트).

const MIN_FIT = 0.62  // 이 아래로는 가독성 손실 — 나머지는 overflow:hidden이 클립

interface CardSurfaceProps {
  children: ReactNode
  motif?: boolean
}

export default function CardSurface({ children, motif = true }: CardSurfaceProps) {
  const imageMode = useImageMode()
  // ghost 모드는 CardFrame의 이미지 opacity(0.09 고정)에 의존해 잉크색 대비를 유지한다.
  const isOverlay = imageMode === 'backdrop' || imageMode === 'ghost'
  const colRef = useRef<HTMLDivElement>(null)

  // 매 렌더 후 측정·보정(imperative — React 리렌더 루프 없음). 폰트 로드 후 1회 재측정.
  useLayoutEffect(() => {
    const el = colRef.current
    if (!el) return
    const fit = () => {
      el.style.transform = 'none'              // 자연 높이 측정을 위해 리셋
      const avail = el.clientHeight
      const need = el.scrollHeight
      if (need > avail + 2 && avail > 0) {
        const f = Math.max(MIN_FIT, avail / need)
        el.style.transform = `scale(${f})`
        el.style.transformOrigin = 'top center'
      }
    }
    fit()
    let cancelled = false
    const fonts = (document as Document & { fonts?: FontFaceSet }).fonts
    fonts?.ready?.then(() => { if (!cancelled) fit() })
    return () => { cancelled = true }
  })

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
      <div ref={colRef} style={{
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
