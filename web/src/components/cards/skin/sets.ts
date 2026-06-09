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

// 코퍼릿/리포트 라이트 — 쿨 라이트 배경 + 네이비 잉크 + 블루 악센트 + 강한 타이포 위계 + 넉넉한 여백.
// 참조 군집 A·C·E(라이트 프로) 합성. 연구·기관(KITECH) 핏. docs/22 §첫 세트. 색 OKLCH(#000/#fff 금지).
export const REPORT_LIGHT_SET: CardSet = {
  set_key: 'report_light',
  seed: 'oklch(52% 0.15 255)',
  tokens: {
    '--set-font': "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    '--set-bg': 'oklch(97% 0.012 255)',
    '--set-bg-grad': 'oklch(94% 0.022 255)',
    '--set-bg-gradient': 'linear-gradient(168deg, oklch(98.5% 0.01 255) 0%, oklch(94% 0.024 255) 100%)',
    '--set-accent': 'oklch(52% 0.15 255)',
    '--set-accent-ink': 'oklch(99% 0.005 255)',
    '--set-ink-strong': 'oklch(32% 0.09 262)',
    '--set-ink-muted': 'oklch(48% 0.06 260)',
    '--set-ink-faint': 'oklch(68% 0.035 258)',
    '--set-surface': 'oklch(99.5% 0.003 255)',
    '--set-surface-border': 'oklch(89% 0.02 255)',
    // 타이포 — 위계 강화(헤드라인 ↑, 본문 약간 ↓로 대비)
    '--set-display': '244px',
    '--set-headline': '70px',
    '--set-subhead': '32px',
    '--set-body': '26px',
    '--set-caption': '20px',
    '--set-eyebrow': '18px',
    // 여백 넉넉히
    '--set-pad': '88px',
    '--set-gap': '28px',
    '--set-radius-box': '18px',
    '--set-radius-pill': '100px',
  },
}

// 다크 테크 — near-black + 네온 바이올렛. 참조 B(docs/22). KITECH AI·전자·기계·생산기술 핏. 세트 #2.
export const DARK_TECH_SET: CardSet = {
  set_key: 'dark_tech',
  seed: 'oklch(64% 0.22 300)',
  tokens: {
    '--set-font': "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    '--set-bg': 'oklch(16% 0.02 290)',
    '--set-bg-grad': 'oklch(22% 0.04 290)',
    '--set-bg-gradient': 'linear-gradient(160deg, oklch(21% 0.035 290) 0%, oklch(13% 0.02 290) 100%)',
    '--set-accent': 'oklch(64% 0.22 300)',
    '--set-accent-ink': 'oklch(16% 0.03 300)',
    '--set-ink-strong': 'oklch(98% 0.005 290)',
    '--set-ink-muted': 'oklch(74% 0.03 290)',
    '--set-ink-faint': 'oklch(56% 0.03 290)',
    '--set-surface': 'rgba(255,255,255,0.06)',
    '--set-surface-border': 'rgba(255,255,255,0.14)',
    // 네온 정성 — 강한 보라 글로우 + 네온 외곽선(다크 전용)
    '--set-glow-opacity': '0.34',
    '--set-card-glow': 'inset 0 0 0 1.5px rgba(170,130,255,0.32), inset 0 0 90px rgba(124,58,237,0.10)',
    '--set-number-display': 'block',   // 우상단 번호 배지 표시(다크 테크 시그니처)
    '--set-display': '244px',
    '--set-headline': '70px',
    '--set-subhead': '32px',
    '--set-body': '26px',
    '--set-caption': '20px',
    '--set-eyebrow': '18px',
    '--set-pad': '88px',
    '--set-gap': '28px',
    '--set-radius-box': '18px',
    '--set-radius-pill': '100px',
  },
}

// ── 세트 레지스트리 — 덱이 set_key로 선택. 미설정/미지 키 → 기본(REPORT_LIGHT) ──
export const DEFAULT_SET = REPORT_LIGHT_SET

export const CARD_SETS: Record<string, CardSet> = {
  report_light: REPORT_LIGHT_SET,
  dark_tech: DARK_TECH_SET,
  editorial_light: EDITORIAL_LIGHT_SET,
  deep_teal: DEEP_TEAL_SET,
}

export interface SetOption { key: string; label: string; sub: string }
/** RightPanel 세트 선택 UI에 노출할 세트(준비된 것만). */
export const SET_OPTIONS: SetOption[] = [
  { key: 'report_light', label: '리포트 라이트', sub: '코퍼릿 · 연구/기관' },
  { key: 'dark_tech',    label: '다크 테크',     sub: '네온 · AI/전자/기계' },
]

export function getSet(key?: string): CardSet {
  return (key && CARD_SETS[key]) || DEFAULT_SET
}

/** CardFrame이 토큰을 inline style로 주입할 때 쓰는 헬퍼(타입 캐스트 일원화). */
export function setTokenStyle(set: CardSet): CSSProperties {
  return set.tokens as CSSProperties
}
