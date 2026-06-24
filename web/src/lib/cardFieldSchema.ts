// 14 레이아웃의 필드 명세 매니페스트. backend/agents/s6/prompts.py의 TEMPLATE_SPEC을
// 프론트에서 읽을 수 있게 미러링한 것 — 추가 전용 문서화 자료, 컴파일 타임 강제는 하지 않는다.
// 둘이 갈라지면 TEMPLATE_SPEC(백엔드)이 권위. docs/18_card_design_system.md §4 참고.

export type FieldShape =
  | 'text'          // 단일 문자열 (headline, body, eyebrow 등)
  | 'stat_array'     // "라벨:값:단위" | 구분 (multistat.stats)
  | 'pair_array'     // "라벨:서브" | 구분 (grid_v2.items, reasons.reasons)
  | 'table_rows'     // "속성:A값:B값" | 구분 (compare_table.rows)
  | 'compare_rows'   // "라벨:값:강조" | 구분 (bigstat_compare.bars)
  | 'step_array'     // "단계1|단계2|..." (process_v2.steps)
  | 'image'          // 업로드 슬롯 (image_hero 캡션 동반 필드)

export interface FieldSpec {
  key: string
  shape: FieldShape
  required: boolean
  note?: string
}

export const CARD_FIELD_SCHEMA: Record<string, FieldSpec[]> = {
  cover_v2: [
    { key: 'eyebrow', shape: 'text', required: true, note: '시리즈/권호 한 줄' },
    { key: 'headline', shape: 'text', required: true, note: '핵심 주제, *강조*' },
    { key: 'subtitle', shape: 'text', required: true, note: '한 줄 부제' },
    { key: 'org', shape: 'text', required: true, note: '기관명' },
  ],
  statement: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '독자를 끄는 큰 질문, *강조*' },
    { key: 'body', shape: 'text', required: true, note: '문제·한계 2~3문장' },
  ],
  feature: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '혁신 한 줄, *강조*' },
    { key: 'body', shape: 'text', required: true, note: '혁신 설명 2~3문장' },
  ],
  process_v2: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '공정 제목' },
    { key: 'steps', shape: 'step_array', required: true, note: '3~5단계, | 구분' },
    { key: 'caption', shape: 'text', required: false, note: '보조 한 줄' },
  ],
  bigstat_compare: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'stat_value', shape: 'text', required: true, note: '대표 수치, 숫자만' },
    { key: 'stat_unit', shape: 'text', required: true },
    { key: 'stat_caption', shape: 'text', required: true, note: '수치 맥락 한 줄' },
    { key: 'bars', shape: 'compare_rows', required: true, note: '라벨:값:강조(0|1), 2~4행' },
    { key: 'source_ref', shape: 'text', required: true, note: '출처: 저널(연도) · 섹션' },
  ],
  reasons: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'reasons', shape: 'pair_array', required: true, note: '제목:본문, 2~4개' },
  ],
  grid_v2: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'items', shape: 'pair_array', required: true, note: '라벨:서브, 2~4개' },
    { key: 'body', shape: 'text', required: false, note: '선택 요약 한 줄' },
  ],
  closing_v2: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'body', shape: 'text', required: true, note: '마무리 2~3문장' },
    { key: 'source_ref', shape: 'text', required: false },
  ],
  definition: [
    { key: 'eyebrow', shape: 'text', required: true, note: '예: "개념"' },
    { key: 'headline', shape: 'text', required: true, note: '용어/질문, *강조*' },
    { key: 'body', shape: 'text', required: true, note: '중학생도 알게 2~3문장' },
    { key: 'caption', shape: 'text', required: true, note: '한 줄 비유·요약' },
  ],
  image_hero: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'caption', shape: 'text', required: true, note: '그림 설명 한 줄' },
    { key: 'image_url', shape: 'image', required: false, note: '업로드 슬롯, 있을 때만 채움' },
  ],
  callout: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '핵심 한 줄, *강조*, 중앙정렬' },
    { key: 'body', shape: 'text', required: false, note: '보조 한 줄' },
  ],
  multistat: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'stats', shape: 'stat_array', required: true, note: '라벨:값:단위, 값은 숫자만, 2~4개' },
    { key: 'source_ref', shape: 'text', required: false },
  ],
  quote: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'quote', shape: 'text', required: true, note: '큰 인용문 한 문장, *강조* 가능' },
    { key: 'attribution', shape: 'text', required: true, note: '— 출처/연구자' },
  ],
  compare_table: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'col_a', shape: 'text', required: true, note: 'A 컬럼명(우리/제안)' },
    { key: 'col_b', shape: 'text', required: true, note: 'B 컬럼명(기존)' },
    { key: 'rows', shape: 'table_rows', required: true, note: '속성:A값:B값, 2~4행' },
    { key: 'source_ref', shape: 'text', required: false },
  ],
  // ── 확장 레이아웃 (15~30) — docs/23_layout_catalog.md ──
  radar_chart: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'axes', shape: 'table_rows', required: true, note: '축라벨:우리값:기존값, 값은 숫자만, 3~6축' },
    { key: 'source_ref', shape: 'text', required: true, note: '축마다 원문 source 필요' },
  ],
  tradeoff_matrix: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'pros', shape: 'pair_array', required: true, note: '제목:본문, 2~3' },
    { key: 'cons', shape: 'pair_array', required: true, note: '제목:본문, 2~3' },
  ],
  terminal_block: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'code', shape: 'text', required: true, note: '모노스페이스 본문, 줄바꿈 허용' },
    { key: 'lang', shape: 'text', required: false, note: '언어 라벨' },
  ],
  timeline: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'events', shape: 'table_rows', required: true, note: '연도:제목:설명, 3~5' },
  ],
  checklist: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'items', shape: 'step_array', required: true, note: '항목1|항목2, 3~6' },
  ],
  mythbuster: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'pairs', shape: 'pair_array', required: true, note: '오해:진실, 2~3' },
  ],
  growth_chart: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'series', shape: 'pair_array', required: true, note: 'x라벨:y값, y는 숫자만, 3~6점' },
    { key: 'source_ref', shape: 'text', required: true, note: '점마다 원문 source 필요' },
  ],
  ab_split: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'variant_a', shape: 'pair_array', required: true, note: '라벨:값 (1쌍)' },
    { key: 'variant_b', shape: 'pair_array', required: true, note: '라벨:값 (1쌍)' },
    { key: 'winner', shape: 'text', required: true, note: 'a 또는 b' },
  ],
  funnel: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'stages', shape: 'stat_array', required: true, note: '단계:값:단위, 위→아래, 값은 숫자만, 3~5' },
    { key: 'bottleneck', shape: 'text', required: false, note: '병목 단계명' },
    { key: 'source_ref', shape: 'text', required: true },
  ],
  datapath: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'nodes', shape: 'step_array', required: true, note: '노드1|노드2|...' },
    { key: 'edges', shape: 'pair_array', required: false, note: 'from:to (선택)' },
  ],
  tech_grid: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'items', shape: 'pair_array', required: true, note: '기술명:아이콘ID, 3~6' },
  ],
  decision_tree: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'root', shape: 'text', required: true, note: '첫 조건' },
    { key: 'branches', shape: 'table_rows', required: true, note: '조건:예결과:아니오결과, 1~3' },
  ],
  ticker: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'items', shape: 'table_rows', required: true, note: '지표명:값:등락(up|down|flat), 3~6' },
    { key: 'source_ref', shape: 'text', required: true },
  ],
  do_dont: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'dont', shape: 'pair_array', required: true, note: '제목:본문, 1~3' },
    { key: 'do', shape: 'pair_array', required: true, note: '제목:본문, 1~3' },
  ],
  swipe_bait: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: true, note: '*강조*' },
    { key: 'teaser', shape: 'text', required: true, note: '다음 장 예고 한 줄' },
    { key: 'cut_items', shape: 'step_array', required: false, note: '잘려 보일 항목들' },
  ],
  chat: [
    { key: 'eyebrow', shape: 'text', required: true },
    { key: 'headline', shape: 'text', required: false, note: '*강조*' },
    { key: 'messages', shape: 'pair_array', required: true, note: '발화자:메시지, 발화자는 q/a 또는 이름, 2~5' },
  ],
}

export function getFieldSchema(templateType: string): FieldSpec[] {
  return CARD_FIELD_SCHEMA[templateType] ?? []
}
