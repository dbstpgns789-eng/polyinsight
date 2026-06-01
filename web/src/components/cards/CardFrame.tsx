// CardFrame — 1080×1080 카드 래퍼.
// 역할:
//  1) 카드 콘텐츠를 고정 사이즈 박스에 담음
//  2) 테마 CSS 변수 (--theme-primary, --theme-dark)를 컴포넌트 스코프에 주입
//     → globals.css에 누출되지 않음 (썸네일에서 카드별로 다른 테마 가능)
//  3) scale prop으로 transform: scale() 적용 (썸네일·미니맵에서 사용)

import { type CSSProperties, type ReactNode } from 'react'
import type { CardTheme } from '@/types/editor'
import styles from './cards.module.css'

interface CardFrameProps {
  theme: CardTheme
  scale?: number              // 1 = 1080px 원본, 0.5 = 540px 표시
  children: ReactNode
  className?: string
}

export default function CardFrame({ theme, scale = 1, children, className }: CardFrameProps) {
  const themeVars = {
    '--theme-primary': theme.primary,
    '--theme-dark': theme.dark,
  } as CSSProperties

  // scale=1이면 transform 비활성화 (불필요한 layer 생성 방지)
  const wrapperStyle: CSSProperties = scale === 1
    ? { width: 1080, height: 1080 }
    : {
        width: 1080 * scale,
        height: 1080 * scale,
      }

  const innerStyle: CSSProperties = scale === 1
    ? themeVars
    : { ...themeVars, transform: `scale(${scale})`, transformOrigin: 'top left' }

  return (
    <div style={wrapperStyle} className={className}>
      <div className={`${styles.scope} ${styles.cardCanvas}`} style={innerStyle}>
        {children}
      </div>
    </div>
  )
}

// Re-export styles for templates so they can mix scoped class names.
export { styles as cardStyles }
