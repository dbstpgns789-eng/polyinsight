'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'
import { getCards, patchCards } from '@/lib/api'

export default function useCardData(jobId: string) {
  const qc = useQueryClient()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [previewKey, setPreviewKey] = useState(0)

  const query = useQuery({
    queryKey: ['cards', jobId],
    queryFn: () => getCards(jobId).then((r) => r.data),
    enabled: !!jobId,
    staleTime: 30_000,
  })

  const mutation = useMutation({
    mutationFn: (cardData: unknown) => patchCards(jobId, cardData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cards', jobId] })
      setPreviewKey((k) => k + 1)
    },
  })

  const debouncedSave = useCallback(
    (cardData: unknown) => {
      if (!jobId) return
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        mutation.mutate(cardData)
      }, 1500)
    },
    [jobId, mutation]
  )

  const saveNow = useCallback(
    (cardData: unknown) => {
      if (!jobId) return
      if (timerRef.current) clearTimeout(timerRef.current)
      mutation.mutate(cardData)
    },
    [jobId, mutation]
  )

  return {
    ...query,
    isSaving: mutation.isPending,
    isSaveSuccess: mutation.isSuccess,
    saveError: mutation.error,
    debouncedSave,
    saveNow,
    previewKey,
  }
}
