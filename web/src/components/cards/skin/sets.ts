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

// 정보카드 에디토리얼 — 밝은 종이 + 진한 포레스트 committed + 굵은 타이포.
// 앱 'Academic Desk'(globals.css hue 152)와 통일. 색은 OKLCH(#000/#fff 금지).
// 미감 방향 C — 2026-06-07 시각 스파이크로 확정(P1 세트 전문화 기본 세트).
export const EDITORIAL_LIGHT_SET: CardSet = {
  set_key: 'editorial_light',
  seed: 'oklch(40% 0.15 152)',
  tokens: {
    '--set-font': "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    '--set-bg': 'oklch(98% 0.008 152)',
    '--set-bg-grad': 'oklch(94% 0.02 152)',
    '--set-bg-gradient': 'linear-gradient(168deg, oklch(99% 0.006 152) 0%, oklch(94.5% 0.022 152) 100%)',
    '--set-accent': 'oklch(40% 0.15 152)',
    '--set-accent-ink': 'oklch(99% 0.005 152)',
    '--set-ink-strong': 'oklch(27% 0.07 152)',
    '--set-ink-muted': 'oklch(44% 0.05 152)',
    '--set-ink-faint': 'oklch(70% 0.03 152)',
    '--set-surface': 'oklch(91% 0.035 152)',
    '--set-surface-border': 'oklch(84% 0.05 152)',
    '--set-display': '248px',
    '--set-headline': '66px',
    '--set-subhead': '33px',
    '--set-body': '27px',
    '--set-caption': '20px',
    '--set-eyebrow': '19px',
    '--set-pad': '80px',
    '--set-gap': '26px',
    '--set-radius-box': '14px',
    '--set-radius-pill': '100px',
  },
}

/** CardFrame이 토큰을 inline style로 주입할 때 쓰는 헬퍼(타입 캐스트 일원화). */
export function setTokenStyle(set: CardSet): CSSProperties {
  return set.tokens as CSSProperties
}
