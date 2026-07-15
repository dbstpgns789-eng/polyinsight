'use client'

// 덱 이미지 삽입 패널 (스펙 2026-07-01). S1 = 사용자 업로드(① 소유진실) 드롭존.
// 업로드 → deck_assets 저장 → onInsert(url) → 부모가 editorAgent INSERT_IMAGE로 <img> 삽입.
// 스톡 검색(S2)·데이터도표 체크(S3)는 이 패널에 증분으로 붙는다.

import { useCallback, useRef, useState } from 'react'
import { uploadDeckAsset } from '@/lib/api'

interface Props {
  jobId: string
  onInsert: (p: { url: string; assetId: string; sourceType: string }) => void
}

const ACCEPT = 'image/png,image/jpeg,image/webp,image/gif'

export default function DeckMediaPanel({ jobId, onInsert }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(async (file: File | null | undefined) => {
    if (!file || busy) return
    setError(null)
    setBusy(true)
    try {
      const r = await uploadDeckAsset(jobId, file, 'upload-owned')
      onInsert({ url: r.data.url, assetId: r.data.assetId, sourceType: 'upload-owned' })
    } catch (e) {
      setError(e instanceof Error ? e.message : '업로드에 실패했습니다.')
    } finally {
      setBusy(false)
    }
  }, [jobId, busy, onInsert])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }, [handleFile])

  return (
    <div className="flex flex-col gap-2">
      <label className="text-[12px] font-semibold text-ink-2">이미지 삽입</label>

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        disabled={busy}
        className={`flex flex-col items-center justify-center gap-1 h-24 rounded-lg border-2 border-dashed text-[12px] transition-colors disabled:opacity-50 ${
          dragOver ? 'border-forest-green bg-forest-green/5 text-forest-green' : 'border-border text-ink-3'
        }`}
      >
        {busy ? (
          <span className="text-ink-2">업로드 중…</span>
        ) : (
          <>
            <span className="text-[18px]">⬆</span>
            <span>이미지를 끌어다 놓거나 클릭</span>
            <span className="text-[10px] text-ink-3">PNG · JPEG · WebP · GIF (최대 8MB)</span>
          </>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = '' }}
      />

      {error && <p className="text-[11px] text-red-600 leading-snug">{error}</p>}

      <p className="text-[10px] text-ink-3 leading-snug">
        로고·연구실 사진·실데이터 등 AI가 알 수 없는 소유 이미지를 넣습니다. 삽입 후 자유롭게 이동·크기 조절하세요.
      </p>
    </div>
  )
}
