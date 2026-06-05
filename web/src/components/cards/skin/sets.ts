// 피부(SET) 정의 — 카드 전용 --set-* 토큰의 단일 출처.
// 새 세트 = 이 파일에 SetTokens 하나 더 정의(씨앗색만 갈아끼움). 뼈대·컴포넌트 불변.
// 앱-크롬 OKLCH 토큰(globals.css :root)과 분리된 네임스페이스(--set-*).

import type { CSSProperties } from 'react'

/** CSS 커스텀 프로퍼티 이름(--set-*) → 값. CardFrame inner style에 그대로 spread. */
export type SetTokens = Record<string, string>

export interface CardSet {
  set_key: string
  seed: string          // Material 3 씨앗(참고용)
  tokens: SetTokens
}

// 첫 세트 — 딥틸. 씨앗 #0E5E60 + 골드 강조.
// 값은 승인된 목업(first-set-render.html)을 1080 스케일로 환산.
export const DEEP_TEAL_SET: CardSet = {
  set_key: 'deep_teal',
  seed: '#0E5E60',
  tokens: {
    '--set-font': "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    // 색 — 3색 규율
    '--set-bg': '#0E5E60',
    '--set-bg-grad': '#062E30',
    '--set-bg-gradient': 'linear-gradient(155deg, #0E5E60 0%, #08393B 58%, #062E30 100%)',
    '--set-accent': '#FFC94A',
    '--set-accent-ink': '#062E30',
    '--set-ink-strong': '#FFFFFF',
    '--set-ink-muted': 'rgba(255,255,255,0.66)',
    '--set-ink-faint': 'rgba(255,255,255,0.45)',
    '--set-surface': 'rgba(255,255,255,0.10)',
    '--set-surface-border': 'rgba(255,255,255,0.16)',
    // 타이포 — 1080 절대 px
    '--set-display': '220px',   // 스펙 §3.2의 88px 대체(드리프트 노트 참조)
    '--set-headline': '60px',
    '--set-subhead': '32px',
    '--set-body': '26px',
    '--set-caption': '19px',
    '--set-eyebrow': '18px',
    // 간격/모양
    '--set-pad': '80px',        // 스펙 §3.3의 64px → 80px(숨 여백)
    '--set-gap': '24px',
    '--set-radius-box': '22px',
    '--set-radius-pill': '100px',
  },
}

/** CardFrame이 토큰을 inline style로 주입할 때 쓰는 헬퍼(타입 캐스트 일원화). */
export function setTokenStyle(set: CardSet): CSSProperties {
  return set.tokens as CSSProperties
}
