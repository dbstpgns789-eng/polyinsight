// CardFrame — 1080×1080 카드 래퍼.
// 역할:
//  1) 카드 콘텐츠를 고정 사이즈 박스에 담음
//  2) 테마 CSS 변수 (--theme-primary, --theme-dark)를 컴포넌트 스코프에 주입
//     → globals.css에 누출되지 않음
//  3) scale prop으로 transform: scale() 적용 (썸네일·미니맵에서 사용)

import { type CSSProperties, type ReactNode } from 'react'
import type { CardTheme } from '@/types/editor'
import styles from './cards.module.css'
import { DEEP_TEAL_SET, type CardSet } from './skin/sets'

const CARD_SIZE = 1080

interface CardFrameProps {
  theme: CardTheme
  bgColor?: string
  scale?: number              // 1 = 1080px 원본, 0.5 = 540px 표시
  set?: CardSet               // 피부 토큰(--set-*) 주입. 기본 딥틸.
  children: ReactNode
  className?: string
}

export default function CardFrame({ theme, bgColor = '#111111', scale = 1, set = DEEP_TEAL_SET, children, className }: CardFrameProps) {
  // Wrapper는 시각적 크기 (scaled). overflow:hidden으로 inner의 layout overflow를 클립.
  const wrapperStyle: CSSProperties = {
    width: CARD_SIZE * scale,
    height: CARD_SIZE * scale,
    position: 'relative',
    overflow: 'hidden',
  }

  // Inner는 1080×1080 원본. 테마 CSS 변수 주입 + transform으로 visual scale.
  const innerStyle: CSSProperties = {
    ...set.tokens,                 // --set-* 피부 토큰 주입(섬 12개는 안 읽으므로 무해)
    '--theme-primary': theme.primary,
    '--theme-dark': theme.dark,
    '--theme-bg': bgColor,
    width: CARD_SIZE,
    height: CARD_SIZE,
    position: 'relative',
    overflow: 'hidden',
    background: 'var(--theme-bg)',
    fontFamily: "'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    boxSizing: 'border-box',
    ...(scale === 1
      ? {}
      : { transform: `scale(${scale})`, transformOrigin: 'top left' }),
  } as CSSProperties

  return (
    <div style={wrapperStyle} className={className}>
      <div className={styles.scope} style={innerStyle}>
        {children}
      </div>
    </div>
  )
}

// Re-export styles for templates so they can mix scoped class names.
export { styles as cardStyles }
