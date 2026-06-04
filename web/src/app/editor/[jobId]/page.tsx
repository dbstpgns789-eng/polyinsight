'use client'

import { useState, useCallback, useEffect } from 'react'
import { useParams } from 'next/navigation'
import useCardData from '@/hooks/useCardData'
import useUiStore from '@/store/uiStore'
import Topbar from '@/components/editor/Topbar'
import LeftPanel from '@/components/editor/LeftPanel'
import MidCanvas from '@/components/editor/MidCanvas'
import RightPanel from '@/components/editor/RightPanel'
import FactDrawer from '@/components/editor/FactDrawer'
import ExportModal from '@/components/export/ExportModal'
import type { CardDataPayload, ApiResponse, CardTheme } from '@/types/editor'
import { MOCK_EDITOR_DATA } from '@/lib/mockData'

export default function EditorPage() {
  const params = useParams()
  const jobId = params.jobId as string
  const isDemo = jobId === 'demo'

  const { data, isLoading, isError, isSaving, isSaveSuccess, debouncedSave, saveNow } = useCardData(
    isDemo ? '' : jobId
  )
  const exportModalOpen = useUiStore((s) => s.exportModalOpen)
  const openExportModal = useUiStore((s) => s.openExportModal)

  const [activeCardIdx, setActiveCardIdx] = useState(0)
  const [localData, setLocalData] = useState<CardDataPayload | null>(null)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const [imageUploadRequested, setImageUploadRequested] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const apiData = isDemo ? MOCK_EDITOR_DATA : (data as ApiResponse | undefined)
  const cardData = localData ?? apiData?.cardData
  const cards = cardData?.cards ?? []
  const filename = apiData?.filename

  useEffect(() => {
    if (isSaveSuccess) setLocalData(null)
  }, [isSaveSuccess])

  const saveState = isDemo ? 'saved' : isSaving ? 'saving' : localData ? 'idle' : 'saved'

  const handleFieldChange = useCallback((fieldKey: string, value: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return {
          ...card,
          fields: { ...card.fields, [fieldKey]: { ...(card.fields?.[fieldKey] ?? {}), value } },
        }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleConfirmRiskAt = useCallback((cardIdx: number, fieldKey: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== cardIdx) return card
        const field = card.fields?.[fieldKey]
        if (!field) return card
        return { ...card, fields: { ...card.fields, [fieldKey]: { ...field, risk_level: undefined } } }
      })
      return { ...base, cards: updatedCards }
    })
  }, [apiData])

  // LeftPanel은 activeCardIdx 기준으로 confirm 호출 (기존 시그니처 유지)
  const handleConfirmRisk = useCallback((fieldKey: string) => {
    handleConfirmRiskAt(activeCardIdx, fieldKey)
  }, [activeCardIdx, handleConfirmRiskAt])

  const handleDrawerItemClick = useCallback((cardIdx: number, fieldKey: string) => {
    setActiveCardIdx(cardIdx)
    setFocusedField(fieldKey)
    setDrawerOpen(false)
  }, [])

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

  const handleThemeChange = useCallback((theme: CardTheme) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updated = { ...base, theme }
      saveNow(updated)
      return updated
    })
  }, [apiData, saveNow])

  const handleBgColorChange = useCallback((bgColor: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updated = { ...base, bg_color: bgColor }
      saveNow(updated)
      return updated
    })
  }, [apiData, saveNow])

  const handleSaveNow = () => {
    if (localData) saveNow(localData)
  }

  if (!isDemo && isLoading) return (
    <div className="flex items-center justify-center h-screen bg-canvas-subtle">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-forest-green border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-[13px] text-ink-3">카드 데이터 로딩중...</p>
      </div>
    </div>
  )

  if (!isDemo && isError) return (
    <div className="flex items-center justify-center h-screen bg-canvas-subtle">
      <div className="text-center">
        <p className="text-4xl mb-3">⚠️</p>
        <p className="text-[14px] text-ink-2 font-medium">카드 데이터를 불러올 수 없습니다.</p>
      </div>
    </div>
  )

  return (
    // h-screen + overflow-hidden → 뷰포트 핏 (DESIGN_3.md §1)
    <div className="flex flex-col h-screen overflow-hidden bg-canvas-subtle" style={{ wordBreak: 'keep-all' }}>

      {/* Topbar: sticky, h-14 (56px) */}
      <Topbar
        filename={filename}
        saveState={saveState}
        onSaveNow={handleSaveNow}
        onExport={isDemo ? undefined : () => openExportModal(jobId)}
      />

      {/* 3단 워크플로우 */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        <LeftPanel
          cards={cards}
          activeCardIdx={activeCardIdx}
          onSelectCard={setActiveCardIdx}
          theme={cardData?.theme}
        />

        <MidCanvas
          jobId={jobId}
          cards={cards}
          activeCardIdx={activeCardIdx}
          onSelectCard={setActiveCardIdx}
          theme={cardData?.theme}
          bgColor={cardData?.bg_color ?? '#111111'}
          isDemo={isDemo}
          focusedField={focusedField}
          onFieldFocus={(field) => setFocusedField(field)}
          onFieldChange={handleFieldChange}
          onImageUploadRequest={() => setImageUploadRequested(true)}
        />

        <RightPanel
          jobId={jobId}
          activeCard={cards[activeCardIdx]}
          onImageUpdate={handleImageUpdate}
          imageUploadRequested={imageUploadRequested}
          onImageUploadHandled={() => setImageUploadRequested(false)}
          currentThemePrimary={cardData?.theme?.primary}
          recommendedThemeKey={cardData?.recommended_theme_key}
          onThemeChange={handleThemeChange}
          bgColor={cardData?.bg_color ?? '#111111'}
          onBgColorChange={handleBgColorChange}
        />
      </div>

      <FactDrawer
        cards={cards}
        open={drawerOpen}
        onToggle={() => setDrawerOpen((v) => !v)}
        onItemClick={handleDrawerItemClick}
        onConfirm={handleConfirmRiskAt}
      />

      {exportModalOpen && <ExportModal />}
    </div>
  )
}
