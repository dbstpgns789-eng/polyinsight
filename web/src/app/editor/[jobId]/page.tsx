'use client'

import { useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import useCardData from '@/hooks/useCardData'
import useUiStore from '@/store/uiStore'
import EditorTopBar from '@/components/editor/EditorTopBar'
import ContentPanel from '@/components/editor/ContentPanel'
import CardPreview from '@/components/editor/CardPreview'
import DesignPanel from '@/components/editor/DesignPanel'
import ActionBar from '@/components/editor/ActionBar'
import ExportModal from '@/components/export/ExportModal'
import type { CardDataPayload, ApiResponse } from '@/types/editor'
import { MOCK_EDITOR_DATA } from '@/lib/mockData'

export default function EditorPage() {
  const params = useParams()
  const jobId = params.jobId as string
  const isDemo = jobId === 'demo'

  const { data, isLoading, isError, isSaving, debouncedSave, saveNow, previewKey } = useCardData(
    isDemo ? '' : jobId   // demo일 때는 API 호출 안 함 (enabled: !!jobId → '' → false)
  )
  const exportModalOpen = useUiStore((s) => s.exportModalOpen)

  const [activeCardIdx, setActiveCardIdx] = useState(0)
  const [localData, setLocalData] = useState<CardDataPayload | null>(null)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const [imageUploadRequested, setImageUploadRequested] = useState(false)

  const apiData = isDemo ? MOCK_EDITOR_DATA : (data as ApiResponse | undefined)
  const cardData = localData ?? apiData?.cardData
  const cards = cardData?.cards ?? []
  const filename = apiData?.filename

  const saveState = isDemo ? 'saved' : isSaving ? 'saving' : localData ? 'idle' : 'saved'

  const handleFieldChange = useCallback((fieldKey: string, value: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return {
          ...card,
          fields: {
            ...card.fields,
            [fieldKey]: { ...(card.fields?.[fieldKey] ?? {}), value },
          },
        }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleConfirmRisk = useCallback((fieldKey: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        const field = card.fields?.[fieldKey]
        if (!field) return card
        return {
          ...card,
          fields: { ...card.fields, [fieldKey]: { ...field, risk_level: undefined } },
        }
      })
      return { ...base, cards: updatedCards }
    })
  }, [activeCardIdx, apiData])

  const handleImageUpdate = useCallback((imageUrl: string | null) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return { ...card, image_url: imageUrl ?? undefined }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleSaveNow = () => {
    if (localData) saveNow(localData)
  }

  if (!isDemo && isLoading) return (
    <div className="flex items-center justify-center h-screen bg-surface-subtle">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-[13px] text-ink-muted">카드 데이터 로딩중...</p>
      </div>
    </div>
  )

  if (!isDemo && isError) return (
    <div className="flex items-center justify-center h-screen bg-surface-subtle">
      <div className="text-center">
        <p className="text-4xl mb-3">⚠️</p>
        <p className="text-[14px] text-ink-secondary font-medium">카드 데이터를 불러올 수 없습니다.</p>
      </div>
    </div>
  )

  return (
    <div className="flex flex-col h-screen bg-surface-subtle">
      <EditorTopBar filename={filename} saveState={saveState} onSaveNow={handleSaveNow} />

      <div className="flex flex-1 overflow-hidden" style={{ marginTop: 64, marginBottom: 52 }}>
        <ContentPanel
          cards={cards}
          activeCardIdx={activeCardIdx}
          onSelectCard={setActiveCardIdx}
          onFieldChange={handleFieldChange}
          onConfirmRisk={handleConfirmRisk}
          focusedField={focusedField}
        />

        <CardPreview
          jobId={jobId}
          cards={cards}
          activeCardIdx={activeCardIdx}
          onSelectCard={setActiveCardIdx}
          refreshTrigger={previewKey}
          isDemo={isDemo}
          onFieldFocus={(field) => setFocusedField(field)}
          onImageUploadRequest={() => setImageUploadRequested(true)}
        />

        <DesignPanel
          jobId={jobId}
          activeCard={cards[activeCardIdx]}
          onImageUpdate={handleImageUpdate}
          imageUploadRequested={imageUploadRequested}
          onImageUploadHandled={() => setImageUploadRequested(false)}
        />
      </div>

      <ActionBar jobId={jobId} cards={cards} />

      {exportModalOpen && <ExportModal />}
    </div>
  )
}
