// CardFrame — 1080×1080 카드 래퍼.
// 역할:
//  1) 카드 콘텐츠를 고정 사이즈 박스에 담음
//  2) 피부 토큰(--set-*) 주입 + 덱 오버라이드(bgColor/accentColor)를 --set-* 위에 덮음
//     → 레거시 --theme-*는 은퇴. globals.css에 누출되지 않음
//  3) scale prop으로 transform: scale() 적용 (썸네일·미니맵에서 사용)

import { type CSSProperties, type ReactNode } from 'react'
import styles from './cards.module.css'
import { REPORT_LIGHT_SET, type CardSet } from './skin/sets'
import { FONT_PAIRINGS } from './fontPairings'

const CARD_SIZE = 1080

interface CardFrameProps {
  bgColor?: string            // 덱 배경 오버라이드. 미설정 시 세트 기본(--set-bg-gradient)
  accentColor?: string        // 덱 강조 오버라이드. 미설정 시 세트 기본(--set-accent)
  fontPairing?: string        // 덱 글꼴 오버라이드(레지스트리 키). 미설정 시 세트 기본(--set-font)
  scale?: number              // 1 = 1080px 원본, 0.5 = 540px 표시
  set?: CardSet               // 피부 토큰(--set-*) 주입. 기본 에디토리얼 라이트.
  children: ReactNode
  className?: string
}

export default function CardFrame({ bgColor, accentColor, fontPairing, scale = 1, set = REPORT_LIGHT_SET, children, className }: CardFrameProps) {
  // Wrapper는 시각적 크기 (scaled). overflow:hidden으로 inner의 layout overflow를 클립.
  const wrapperStyle: CSSProperties = {
    width: CARD_SIZE * scale,
    height: CARD_SIZE * scale,
    position: 'relative',
    overflow: 'hidden',
  }

  // Inner는 1080×1080 원본. 세트 토큰 주입 후 덱 오버라이드를 --set-* 위에 선택적으로 덮음.
  const innerStyle: CSSProperties = {
    ...set.tokens,                 // --set-* 피부 토큰 주입
    ...(bgColor ? { '--set-bg': bgColor, '--set-bg-gradient': bgColor } : {}),
    ...(accentColor ? { '--set-accent': accentColor } : {}),
    ...(fontPairing && FONT_PAIRINGS[fontPairing] ? { '--set-font': FONT_PAIRINGS[fontPairing] } : {}),
    width: CARD_SIZE,
    height: CARD_SIZE,
    position: 'relative',
    overflow: 'hidden',
    background: 'var(--set-bg-gradient)',
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
