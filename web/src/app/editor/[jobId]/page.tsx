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
import type { CardDataPayload, ApiResponse, FieldStyle, Card } from '@/types/editor'
import { MOCK_EDITOR_DATA } from '@/lib/mockData'
import { renameJob, downloadCard, getStatus } from '@/lib/api'
import AuthGuard from '@/components/auth/AuthGuard'

function EditorPageInner() {
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
  const [localFilename, setLocalFilename] = useState<string | null>(null)
  const [downloadingCardNum, setDownloadingCardNum] = useState<number | null>(null)

  const apiData = isDemo ? MOCK_EDITOR_DATA : (data as ApiResponse | undefined)
  const cardData = localData ?? apiData?.cardData
  const cards = cardData?.cards ?? []
  const filename = localFilename ?? apiData?.filename

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

  const handleFocalUpdate = useCallback((focal: { x: number; y: number }) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return { ...card, focal }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleFitUpdate = useCallback((fit: 'cover' | 'contain') => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return { ...card, image_fit: fit }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleImageModeUpdate = useCallback((mode: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return { ...card, image_mode: mode as Card['image_mode'] }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleVisualKindUpdate = useCallback((kind: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        return { ...card, visual_kind: kind as Card['visual_kind'] }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleReorderCard = useCallback((idx: number, dir: -1 | 1) => {
    const target = idx + dir
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      if (target < 0 || target >= base.cards.length) return prev
      const next = [...base.cards]
      const tmp = next[idx]; next[idx] = next[target]; next[target] = tmp
      const renumbered = next.map((c, i) => ({ ...c, card_num: i + 1 }))
      const updated = { ...base, cards: renumbered }
      debouncedSave(updated)
      return updated
    })
    setActiveCardIdx((cur) => {
      if (target < 0 || target >= cards.length) return cur
      return target
    })
  }, [apiData, debouncedSave, cards.length])

  const handleAccentColorChange = useCallback((hex: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updated = { ...base, accent_color: hex }
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

  const handleFontPairingChange = useCallback((key: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updated = { ...base, font_pairing: key }
      saveNow(updated)
      return updated
    })
  }, [apiData, saveNow])

  const handleTemplateChange = useCallback((key: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updated = { ...base, template_key: key }
      saveNow(updated)
      return updated
    })
  }, [apiData, saveNow])

  const handleFieldStyleChange = useCallback((fieldKey: string, patch: Partial<FieldStyle>) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        const current = card.field_styles?.[fieldKey] ?? {}
        return { ...card, field_styles: { ...card.field_styles, [fieldKey]: { ...current, ...patch } } }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleFieldStyleReset = useCallback((fieldKey: string) => {
    setLocalData((prev) => {
      const base = prev ?? apiData?.cardData
      if (!base) return prev
      const updatedCards = base.cards.map((card, idx) => {
        if (idx !== activeCardIdx) return card
        if (!card.field_styles?.[fieldKey]) return card
        const rest = { ...card.field_styles }
        delete rest[fieldKey]
        return { ...card, field_styles: rest }
      })
      const updated = { ...base, cards: updatedCards }
      debouncedSave(updated)
      return updated
    })
  }, [activeCardIdx, apiData, debouncedSave])

  const handleRename = useCallback((title: string) => {
    setLocalFilename(title)           // 낙관적 반영
    if (isDemo) return
    renameJob(jobId, title).catch(() => setLocalFilename(null))  // 실패 시 서버값 복원
  }, [isDemo, jobId])

  const handleDownloadCard = useCallback(async (cardNum: number) => {
    if (isDemo) return
    setDownloadingCardNum(cardNum)
    try {
      await downloadCard(jobId, cardNum)
    } catch {
      alert('카드 다운로드에 실패했습니다. 잠시 후 다시 시도해 주세요.')
    } finally {
      setDownloadingCardNum(null)
    }
  }, [isDemo, jobId])

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

  if (!isDemo && isError) return <EditorError jobId={jobId} />

  return (
    // h-screen + overflow-hidden → 뷰포트 핏 (DESIGN_3.md §1)
    <div className="flex flex-col h-screen overflow-hidden bg-canvas-subtle" style={{ wordBreak: 'keep-all' }}>

      {/* Topbar: sticky, h-14 (56px) */}
      <Topbar
        filename={filename}
        saveState={saveState}
        onSaveNow={handleSaveNow}
        onExport={isDemo ? undefined : () => openExportModal(jobId)}
        onRename={handleRename}
      />

      {/* 3단 워크플로우 */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        <LeftPanel
          cards={cards}
          activeCardIdx={activeCardIdx}
          onSelectCard={setActiveCardIdx}
          onReorderCard={handleReorderCard}
          theme={cardData?.theme}
          bgColor={cardData?.bg_color}
          accentColor={cardData?.accent_color}
          fontPairing={cardData?.font_pairing}
          templateKey={cardData?.template_key}
        />

        <MidCanvas
          jobId={jobId}
          cards={cards}
          activeCardIdx={activeCardIdx}
          onSelectCard={setActiveCardIdx}
          theme={cardData?.theme}
          bgColor={cardData?.bg_color}
          accentColor={cardData?.accent_color}
          fontPairing={cardData?.font_pairing}
          templateKey={cardData?.template_key}
          isDemo={isDemo}
          focusedField={focusedField}
          onFieldFocus={(field) => setFocusedField(field)}
          onFieldChange={handleFieldChange}
          onImageUploadRequest={() => setImageUploadRequested(true)}
          onFocalChange={handleFocalUpdate}
          onFitChange={handleFitUpdate}
          onDownloadCard={isDemo ? undefined : handleDownloadCard}
          downloadingCardNum={downloadingCardNum}
        />

        <RightPanel
          activeCard={cards[activeCardIdx]}
          onImageUpdate={handleImageUpdate}
          imageUploadRequested={imageUploadRequested}
          onImageUploadHandled={() => setImageUploadRequested(false)}
          currentAccent={cardData?.accent_color}
          recommendedThemeKey={cardData?.recommended_theme_key}
          onAccentColorChange={handleAccentColorChange}
          bgColor={cardData?.bg_color}
          onBgColorChange={handleBgColorChange}
          currentFontPairing={cardData?.font_pairing}
          onFontPairingChange={handleFontPairingChange}
          currentTemplateKey={cardData?.template_key}
          onTemplateChange={handleTemplateChange}
          focusedField={focusedField}
          activeFieldStyle={focusedField ? cards[activeCardIdx]?.field_styles?.[focusedField] : undefined}
          onFieldStyleChange={handleFieldStyleChange}
          onFieldStyleReset={handleFieldStyleReset}
          currentImageMode={cards[activeCardIdx]?.image_mode ?? 'box'}
          onImageModeChange={handleImageModeUpdate}
          currentVisualKind={cards[activeCardIdx]?.visual_kind ?? 'photo'}
          onVisualKindChange={handleVisualKindUpdate}
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

// 카드 로드 실패 화면. job status를 조회해, 파이프라인이 입력 가드레일/에러로
// 조기 종료된 경우(warnings에 ABORT-S1:/ERR- 사유) generic 대신 구체 사유를 표면화.
function EditorError({ jobId }: { jobId: string }) {
  const [reason, setReason] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    getStatus(jobId)
      .then((r) => {
        if (cancelled) return
        const raw = r.data?.warnings
        let list: string[] = []
        try { list = typeof raw === 'string' ? JSON.parse(raw) : (raw ?? []) } catch { list = [] }
        // 사용자용 사유: ABORT-S1(thin input) 우선, 없으면 ERR- 사유.
        const abort = list.find((w) => w.startsWith('ABORT-'))
        const err = list.find((w) => w.startsWith('ERR-'))
        const pick = abort ?? err
        if (pick) setReason(pick.replace(/^(ABORT|ERR)-S?\d*:\s*/, '').replace(/^[A-Z-]+:\s*/, ''))
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [jobId])

  return (
    <div className="flex items-center justify-center h-screen bg-canvas-subtle">
      <div className="text-center max-w-md px-6">
        <p className="text-4xl mb-3">⚠️</p>
        <p className="text-[14px] text-ink-2 font-medium">
          {reason ?? '카드 데이터를 불러올 수 없습니다.'}
        </p>
        {reason && (
          <p className="text-[12px] text-ink-3 mt-2">
            다른 논문 PDF로 다시 시도해 주세요.
          </p>
        )}
      </div>
    </div>
  )
}

export default function EditorPage() {
  return (
    <AuthGuard>
      <EditorPageInner />
    </AuthGuard>
  )
}
