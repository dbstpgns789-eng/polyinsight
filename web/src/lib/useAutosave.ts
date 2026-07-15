'use client'

// 자동저장 훅 — 로직은 createAutosave(순수 코어, 테스트됨)에 있고 여기선 생명주기만 배선한다.
import { useEffect, useRef, useState } from 'react'

import { createAutosave, type Autosave, type AutosaveStatus } from './autosave'

interface Params {
  save: () => Promise<void>
  enabled: boolean            // 편집 모드일 때만 true
  isBlocked: () => boolean    // AI 제안 대기·저장 중 등
  delayMs?: number
}

export function useAutosave({ save, enabled, isBlocked, delayMs = 3000 }: Params) {
  const [status, setStatus] = useState<AutosaveStatus>('clean')
  const ref = useRef<Autosave | null>(null)

  // 최신 콜백을 참조로 유지 — 콜백이 매 렌더 새로 만들어져도 코어를 재생성하지 않는다.
  const saveRef = useRef(save)
  const blockedRef = useRef(isBlocked)
  saveRef.current = save
  blockedRef.current = isBlocked

  useEffect(() => {
    if (!enabled) return
    const a = createAutosave({
      save: () => saveRef.current(),
      isBlocked: () => blockedRef.current(),
      delayMs,
      onChange: setStatus,
    })
    ref.current = a

    const onHide = () => { if (document.visibilityState === 'hidden') void a.flush() }
    document.addEventListener('visibilitychange', onHide)

    return () => {
      document.removeEventListener('visibilitychange', onHide)
      void a.flush()        // 편집 모드를 떠날 때 마지막 편집을 저장한다
      a.dispose()
      ref.current = null
      setStatus('clean')
    }
  }, [enabled, delayMs])

  return {
    status,
    markDirty: () => ref.current?.markDirty(),
    markClean: () => ref.current?.markClean(),
    flush: () => ref.current?.flush() ?? Promise.resolve(),
    retry: () => ref.current?.retry() ?? Promise.resolve(),
  }
}
