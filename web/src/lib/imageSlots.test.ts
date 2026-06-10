import { describe, it, expect } from 'vitest'
import { getSlotType } from './imageSlots'

describe('getSlotType — P2 신규 존 뼈대', () => {
  it('statement는 zone', () => {
    expect(getSlotType('statement')).toBe('zone')
  })
  it('closing_v2는 zone', () => {
    expect(getSlotType('closing_v2')).toBe('zone')
  })
  it('데이터 4종은 none 유지', () => {
    expect(getSlotType('bigstat_compare')).toBe('none')
    expect(getSlotType('process_v2')).toBe('none')
    expect(getSlotType('reasons')).toBe('none')
    expect(getSlotType('grid_v2')).toBe('none')
  })
  it('기존 cover_v2/feature는 zone 유지', () => {
    expect(getSlotType('cover_v2')).toBe('zone')
    expect(getSlotType('feature')).toBe('zone')
  })
})
