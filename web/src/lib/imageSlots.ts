export type SlotType = 'bg' | 'inset_top' | 'inset_right' | 'inner' | 'none'

export interface SlotMeta {
  type: SlotType
  label: string
  description: string
}

/** 백엔드 IMAGE_SLOT_TYPES 미러 */
export const IMAGE_SLOT_TYPES: Record<string, SlotType> = {
  cover:      'bg',
  hook:       'bg',
  problem:    'bg',
  circle3:    'bg',
  compare2:   'bg',
  grid4:      'bg',
  flow:       'bg',
  showcase:   'inset_top',
  definition: 'inset_right',
  closing:    'inner',
  data:       'none',
  brand:      'none',
}

export const SLOT_META: Record<SlotType, SlotMeta> = {
  bg: {
    type:        'bg',
    label:       '배경 사진',
    description: '카드 전체 배경에 흐릿하게 깔립니다',
  },
  inset_top: {
    type:        'inset_top',
    label:       '상단 사진',
    description: '카드 상단 40% 영역에 표시됩니다',
  },
  inset_right: {
    type:        'inset_right',
    label:       '우측 패널 사진',
    description: '오른쪽 영역에 선명하게 표시됩니다',
  },
  inner: {
    type:        'inner',
    label:       '카드 내부 이미지',
    description: '흰 카드 안에 삽입됩니다',
  },
  none: {
    type:        'none',
    label:       '이미지 없음',
    description: '이 템플릿은 이미지 슬롯이 없습니다',
  },
}

export function getSlotType(templateType: string): SlotType {
  return IMAGE_SLOT_TYPES[templateType] ?? 'none'
}

export function getSlotMeta(templateType: string): SlotMeta {
  return SLOT_META[getSlotType(templateType)]
}
