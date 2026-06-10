// 덱 글꼴 페어링 — CardDataPayload.font_pairing 키 → --set-font 오버라이드 값.
// 폰트는 app/layout.tsx <head>에서 로드(Pretendard=jsdelivr, 나머지=Google Fonts).
// 단일 토큰(--set-font)이라 현재는 페어링=단일 패밀리 선택. (head/body 분리는 후속.)

export const FONT_PAIRINGS: Record<string, string> = {
  pretendard: "'Pretendard Variable', Pretendard, 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif",
  serif: "'Noto Serif KR', 'Pretendard Variable', serif",
  gothic_a1: "'Gothic A1', 'Pretendard Variable', sans-serif",
}

export interface FontOption {
  key: string
  label: string
  sub: string
  family: string
}

// RightPanel 글꼴 섹션에 표시할 옵션(미리보기 포함). undefined=세트 기본(=pretendard).
export const FONT_OPTIONS: FontOption[] = [
  { key: 'pretendard', label: '프리텐다드', sub: '고딕 · 기본', family: FONT_PAIRINGS.pretendard },
  { key: 'serif',      label: '본명조',     sub: '명조 · 에디토리얼', family: FONT_PAIRINGS.serif },
  { key: 'gothic_a1',  label: 'Gothic A1',  sub: '기하학 고딕', family: FONT_PAIRINGS.gothic_a1 },
]
