// 자동저장 스케줄러 — React·DOM 무관(테스트 가능한 순수 코어).
//
// 왜 코어를 분리하나: 이 레포엔 jsdom·testing-library가 없다(기존 테스트는 전부 src/lib 순수 로직).
// 훅 안에 로직을 넣으면 테스트할 방법이 없다 — 디바운스·재시도·차단은 버그가 숨기 좋은 곳이다.

export type AutosaveStatus = 'clean' | 'dirty' | 'saving' | 'error'

export interface AutosaveOptions {
  save: () => Promise<void>
  delayMs?: number             // 편집 후 유휴 시간
  retryDelayMs?: number        // 실패 후 자동 재시도까지
  isBlocked?: () => boolean    // true면 저장하지 않는다(AI 제안 대기·저장 중 등)
  onChange?: (status: AutosaveStatus) => void
}

export interface Autosave {
  markDirty: () => void
  markClean: () => void       // 다른 경로(수동 저장·AI 제안 수락)가 이미 저장했을 때
  flush: () => Promise<void>
  retry: () => Promise<void>
  status: () => AutosaveStatus
  isDirty: () => boolean
  dispose: () => void
}

export function createAutosave({
  save, delayMs = 3000, retryDelayMs = 3000, isBlocked, onChange,
}: AutosaveOptions): Autosave {
  let status: AutosaveStatus = 'clean'
  let dirty = false          // 저장되지 않은 편집이 있나 (status와 별개 — saving 중에도 새 편집이 들어온다)
  let timer: ReturnType<typeof setTimeout> | null = null
  let retried = false        // 이번 실패 사이클에서 자동 재시도를 이미 썼나
  let disposed = false

  const set = (s: AutosaveStatus) => {
    if (status === s) return
    status = s
    onChange?.(s)
  }

  const clearTimer = () => {
    if (timer) { clearTimeout(timer); timer = null }
  }

  const schedule = (ms: number) => {
    clearTimer()
    timer = setTimeout(() => { timer = null; void run() }, ms)
  }

  const run = async (): Promise<void> => {
    if (disposed || !dirty) return
    if (status === 'saving') return
    if (isBlocked?.()) return          // 차단 중 — dirty는 유지한다(편집을 잃지 않는다)

    set('saving')
    dirty = false                      // 이 시점 이후의 편집은 '새 편집'이다
    try {
      await save()
      if (disposed) return
      retried = false
      set(dirty ? 'dirty' : 'clean')   // 저장 중 들어온 편집이 있으면 다시 dirty
      if (dirty) schedule(delayMs)
    } catch {
      if (disposed) return
      dirty = true                     // 실패 — 편집은 아직 저장되지 않았다
      if (!retried) {
        retried = true
        set('dirty')
        schedule(retryDelayMs)         // 자동 재시도 1회
      } else {
        set('error')                   // 사용자 개입 필요
      }
    }
  }

  return {
    markDirty() {
      if (disposed) return
      dirty = true
      retried = false
      if (status !== 'saving') set('dirty')
      schedule(delayMs)
    },
    markClean() {
      // 다른 경로가 이미 저장했다 — 예약된 저장을 취소한다(같은 html을 또 PATCH하면 서버 렌더가 헛돈다).
      if (disposed) return
      dirty = false
      retried = false
      clearTimer()
      if (status !== 'saving') set('clean')
    },
    async flush() {
      clearTimer()
      await run()
    },
    async retry() {
      retried = false
      clearTimer()
      await run()
    },
    status: () => status,
    isDirty: () => dirty,
    dispose() {
      disposed = true
      clearTimer()
    },
  }
}
