// 템플릿(TEMPLATE) 정의 — 카드 전용 --set-* 토큰 + 시그니처 컴포넌트의 단일 출처.
// 템플릿 = 유저가 고르는 "덱 전체 비주얼 월드"(옛 "세트"). 색만이 아니라 배지·프레임 등
// 시그니처 컴포넌트까지 담는다. 새 템플릿 = 이 파일에 Template 하나 더(씨앗색 + 시그니처).
// 뼈대(레이아웃 30종)는 --set-* 토큰 계약으로만 받으므로 템플릿을 모른다(불변).
//
// 2026-06-24 개정: 토큰만 가졌던 빈 5세트 삭제. 출시 가능한 템플릿은 lab_note 하나뿐(기본).
// 어휘: docs/23 + 메모리 reference_design_vocabulary. (CSS 토큰 네임스페이스는 --set-* 유지.)

import type { CSSProperties } from 'react'

/** CSS 커스텀 프로퍼티 이름(--set-*) → 값. CardFrame inner style에 그대로 spread. */
export type TemplateTokens = Record<string, string>

export interface Template {
  template_key: string
  seed: string          // Material 3 씨앗(참고용)
  tokens: TemplateTokens
  badge?: { labelPrefix: string }   // 정의된 템플릿만 우상단 식별 배지 렌더
  frame?: { tickCount: number }     // 정의된 템플릿만 하단 눈금 프레임 렌더
}

// 랩 노트 — 개인 연구자의 연구노트 톤. 종이빛 중성 배경 + 그래파이트 잉크 + 머스타드 악센트.
// 첫(현재 유일) 출시 가능 템플릿. 토큰 + 시그니처 컴포넌트(배지+눈금 프레임)를 가진 비주얼 월드.
// 관청/공식 톤 배제(빨강 금지), 마스코트·일러스트 없음. 색 OKLCH.
export const LAB_NOTE_TEMPLATE: Template = {
  template_key: 'lab_note',
  seed: 'oklch(70% 0.14 95)',
  badge: { labelPrefix: 'Note' },
  frame: { tickCount: 7 },
  tokens: {
    '--set-font': "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
    '--set-mono': "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, 'SF Mono', monospace",
    '--set-bg': 'oklch(97% 0.006 80)',
    '--set-bg-grad': 'oklch(94% 0.012 80)',
    '--set-bg-gradient': 'linear-gradient(168deg, oklch(98% 0.005 80) 0%, oklch(94.5% 0.014 80) 100%)',
    '--set-accent': 'oklch(70% 0.14 95)',
    '--set-accent-ink': 'oklch(22% 0.02 95)',
    '--set-ink-strong': 'oklch(28% 0.01 80)',
    '--set-ink-muted': 'oklch(46% 0.008 80)',
    '--set-ink-faint': 'oklch(68% 0.006 80)',
    '--set-surface': 'oklch(99% 0.003 80)',
    '--set-surface-border': 'oklch(88% 0.012 80)',
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

// ── 템플릿 레지스트리 — 덱이 template_key로 선택. 미설정/미지 키 → 기본(lab_note) ──
export const DEFAULT_TEMPLATE = LAB_NOTE_TEMPLATE

export const TEMPLATES: Record<string, Template> = {
  lab_note: LAB_NOTE_TEMPLATE,
}

export interface TemplateOption { key: string; label: string; sub: string }
/** 업로드 후 / RightPanel 템플릿 선택 UI에 노출(준비된 것만). 현재 1개 — #2·#3 추가 시 늘어남. */
export const TEMPLATE_OPTIONS: TemplateOption[] = [
  { key: 'lab_note', label: '랩 노트', sub: '배지+눈금 · 개인 연구자' },
]

export function getTemplate(key?: string): Template {
  return (key && TEMPLATES[key]) || DEFAULT_TEMPLATE
}

/** CardFrame이 토큰을 inline style로 주입할 때 쓰는 헬퍼(타입 캐스트 일원화). */
export function templateTokenStyle(template: Template): CSSProperties {
  return template.tokens as CSSProperties
}
