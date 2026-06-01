'use client'

import { useRef, useEffect } from 'react'
import { getCardImageUrl } from '@/lib/api'
import { IconImage, IconClose } from '@/components/ui/Icons'
import { getSlotMeta, type SlotType } from '@/lib/imageSlots'
import type { Card } from '@/types/editor'

interface Props {
  jobId: string
  activeCard?: Card
  onImageUpdate: (imageUrl: string | null) => void
  imageUploadRequested?: boolean
  onImageUploadHandled?: () => void
}

/* ── 슬롯 위치 다이어그램 ── */
function SlotDiagram({ type }: { type: SlotType }) {
  const base = 'rounded-md bg-surface-subtle'
  const fill = 'rounded-md bg-brand-300/60'

  if (type === 'bg') return (
    <div className={`relative w-full aspect-square ${base} overflow-hidden`}>
      <div className={`absolute inset-0 ${fill} opacity-50`} />
      <div className="absolute inset-3 rounded border border-white/40 flex items-center justify-center">
        <span className="text-[9px] text-white/60 font-bold tracking-widest">TEXT</span>
      </div>
    </div>
  )

  if (type === 'inset_top') return (
    <div className={`w-full aspect-square ${base} flex flex-col overflow-hidden`}>
      <div className={`h-[40%] w-full ${fill}`} />
      <div className="flex-1 flex items-center justify-center">
        <span className="text-[9px] text-ink-muted font-bold">TEXT</span>
      </div>
    </div>
  )

  if (type === 'inset_right') return (
    <div className={`w-full aspect-square ${base} flex flex-row overflow-hidden`}>
      <div className="flex-1 flex items-center justify-center">
        <span className="text-[9px] text-ink-muted font-bold">TEXT</span>
      </div>
      <div className={`w-[38%] h-full ${fill}`} />
    </div>
  )

  if (type === 'inner') return (
    <div className={`w-full aspect-square ${base} flex flex-col p-2 gap-1.5`}>
      <div className="h-2 w-3/4 rounded bg-surface-border" />
      <div className={`flex-1 w-full ${fill} rounded`} />
    </div>
  )

  return null
}

export default function DesignPanel({
  jobId, activeCard, onImageUpdate, imageUploadRequested, onImageUploadHandled,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const slot = getSlotMeta(activeCard?.template_type ?? '')

  // 외부에서 업로드 요청 오면 파일 다이얼로그 열기
  useEffect(() => {
    if (imageUploadRequested && slot.type !== 'none') {
      inputRef.current?.click()
      onImageUploadHandled?.()
    }
  }, [imageUploadRequested, slot.type, onImageUploadHandled])

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => onImageUpdate(reader.result as string)
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (!file || !file.type.startsWith('image/')) return
    const reader = new FileReader()
    reader.onload = () => onImageUpdate(reader.result as string)
    reader.readAsDataURL(file)
  }

  const imageUrl = activeCard?.image_url ||
    (jobId && activeCard ? getCardImageUrl(jobId, activeCard.card_num) : null)

  return (
    <div className="bg-surface border-l border-surface-border flex flex-col" style={{ width: 260 }}>

      {/* 헤더 */}
      <div className="px-4 py-3 border-b border-surface-border shrink-0">
        <p className="text-[10px] font-bold text-ink-muted uppercase tracking-widest">디자인 설정</p>
      </div>

      <div className="p-4 flex flex-col gap-4 flex-1 overflow-y-auto">

        {/* 이미지 슬롯 섹션 */}
        <div>
          <p className="text-[10px] font-bold text-ink-muted uppercase tracking-widest mb-3">이미지 슬롯</p>

          {slot.type === 'none' ? (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <div className="w-10 h-10 rounded-full bg-surface-subtle flex items-center justify-center">
                <IconImage size={18} className="text-ink-disabled" />
              </div>
              <p className="text-[11px] text-ink-muted leading-relaxed">
                이 템플릿은<br />이미지 슬롯이 없습니다
              </p>
            </div>
          ) : (
            <>
              {/* 슬롯 타입 배지 */}
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-brand-50 text-brand-600 text-[11px] font-bold border border-brand-600/20">
                  {slot.label}
                </span>
                <p className="text-[11px] text-ink-muted leading-tight">{slot.description}</p>
              </div>

              {/* 슬롯 다이어그램 */}
              <div className="mb-3">
                <SlotDiagram type={slot.type} />
              </div>

              {/* 이미지 업로드 존 */}
              {imageUrl ? (
                <div className="relative group mb-2">
                  <img
                    src={imageUrl}
                    alt=""
                    className="w-full aspect-square object-cover rounded-xl border border-surface-border"
                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
                  />
                  <button
                    onClick={() => onImageUpdate(null)}
                    aria-label="이미지 제거"
                    className="absolute top-2 right-2 w-6 h-6 bg-ink/60 text-surface rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                  >
                    <IconClose size={10} />
                  </button>
                </div>
              ) : (
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => inputRef.current?.click()}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click() } }}
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  aria-label="이미지 파일 선택 또는 드래그"
                  className="aspect-square border-2 border-dashed border-surface-border rounded-xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-brand-600 hover:bg-brand-50/40 transition-all mb-2 focus-visible:outline-none focus-visible:border-brand-600 focus-visible:bg-brand-50/40"
                >
                  <IconImage size={24} className="text-ink-disabled" />
                  <p className="text-[11px] text-ink-muted text-center font-medium">
                    클릭 또는<br />드래그로 추가
                  </p>
                </div>
              )}

              <button
                onClick={() => inputRef.current?.click()}
                className="w-full text-[12px] font-semibold text-ink-secondary bg-surface-subtle h-8 rounded-lg hover:bg-surface-border transition-colors"
              >
                {imageUrl ? '이미지 교체' : '이미지 선택'}
              </button>

              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFile}
              />

              <p className="text-[10px] text-ink-muted text-center mt-2 leading-relaxed">
                이미지 없이도 내보내기 가능합니다
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
