import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createAutosave } from './autosave'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('createAutosave', () => {
  it('편집 후 유휴 시간이 지나면 1회 저장한다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    expect(a.status()).toBe('dirty')
    expect(save).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(1)
    expect(a.status()).toBe('clean')
  })

  it('연속 편집은 디바운스된다 — 마지막 편집 기준 1회만', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(2000)
    a.markDirty()                          // 타이머 리셋
    await vi.advanceTimersByTimeAsync(2000)
    expect(save).not.toHaveBeenCalled()    // 아직 3초 유휴가 아니다

    await vi.advanceTimersByTimeAsync(1000)
    expect(save).toHaveBeenCalledTimes(1)
  })

  it('차단 중(AI 제안 대기 등)에는 저장하지 않는다 — dirty는 유지', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    let blocked = true
    const a = createAutosave({ save, delayMs: 3000, isBlocked: () => blocked })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(10_000)
    expect(save).not.toHaveBeenCalled()
    expect(a.isDirty()).toBe(true)         // 편집이 사라지면 안 된다

    blocked = false
    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(1)
  })

  it('저장 실패 시 1회 자동 재시도하고, 그래도 실패하면 error가 된다', async () => {
    const save = vi.fn().mockRejectedValue(new Error('offline'))
    const a = createAutosave({ save, delayMs: 3000, retryDelayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(3000)     // 자동 재시도 1회
    expect(save).toHaveBeenCalledTimes(2)
    expect(a.status()).toBe('error')
    expect(a.isDirty()).toBe(true)              // 편집은 아직 저장 안 됐다
  })

  it('retry()는 error 상태에서 즉시 다시 저장한다', async () => {
    const save = vi.fn().mockRejectedValue(new Error('offline'))
    const a = createAutosave({ save, delayMs: 3000, retryDelayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)     // 1차 실패
    await vi.advanceTimersByTimeAsync(3000)     // 자동 재시도도 실패
    expect(a.status()).toBe('error')

    save.mockResolvedValue(undefined)
    await a.retry()
    expect(a.status()).toBe('clean')
  })

  it('flush()는 대기 중인 저장을 즉시 실행한다 (탭 이탈 대비)', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    await a.flush()
    expect(save).toHaveBeenCalledTimes(1)
    expect(a.status()).toBe('clean')
  })

  it('깨끗한 상태에서 flush()는 아무것도 하지 않는다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    await a.flush()
    expect(save).not.toHaveBeenCalled()
  })

  it('저장 중에 들어온 편집은 잃지 않는다 — 저장 후 다시 예약된다', async () => {
    let resolveSave: () => void = () => {}
    const save = vi.fn().mockImplementation(() => new Promise<void>((r) => { resolveSave = r }))
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    await vi.advanceTimersByTimeAsync(3000)
    expect(a.status()).toBe('saving')

    a.markDirty()                 // 저장 중에 또 편집
    resolveSave()                 // 1차 저장 완료
    await vi.advanceTimersByTimeAsync(0)
    expect(a.status()).toBe('dirty')       // 새 편집이 있으니 다시 dirty

    await vi.advanceTimersByTimeAsync(3000)
    expect(save).toHaveBeenCalledTimes(2)  // 2차 저장 시작(아직 대기 중)
    resolveSave()                          // 2차 저장 완료
    await vi.advanceTimersByTimeAsync(0)
    expect(a.status()).toBe('clean')
  })

  it('dispose()는 예약된 저장을 취소한다', async () => {
    const save = vi.fn().mockResolvedValue(undefined)
    const a = createAutosave({ save, delayMs: 3000 })

    a.markDirty()
    a.dispose()
    await vi.advanceTimersByTimeAsync(10_000)
    expect(save).not.toHaveBeenCalled()
  })
})
