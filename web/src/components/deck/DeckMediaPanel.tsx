'use client'

// 덱 이미지 삽입 패널 (스펙 2026-07-01). ① 사용자 업로드(소유진실) 드롭존
//   + ② 무료 스톡 검색(Pexels/Unsplash). 선택 → 서버가 deck_asset으로 임포트(렌더 인라인).
// 업로드/스톡 모두 onInsert(url) → 부모가 editorAgent INSERT_IMAGE로 <img> 삽입.

import { useCallback, useRef, useState } from 'react'
import { uploadDeckAsset, searchStockImages, importStockAsset } from '@/lib/api'
import type { StockImageResult } from '@/types/editor'

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

  // 스톡 검색
  const [q, setQ] = useState('')
  const [results, setResults] = useState<StockImageResult[]>([])
  const [searching, setSearching] = useState(false)
  const [stockErr, setStockErr] = useState<string | null>(null)
  const [importingId, setImportingId] = useState<string | null>(null)

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

  const runSearch = useCallback(async () => {
    const term = q.trim()
    if (!term || searching) return
    setSearching(true)
    setStockErr(null)
    try {
      const r = await searchStockImages(term)
      setResults(r)
      if (r.length === 0) setStockErr('검색 결과가 없어요. 다른 검색어(영어)를 시도해 보세요.')
    } catch {
      setStockErr('검색에 실패했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSearching(false)
    }
  }, [q, searching])

  const pick = useCallback(async (r: StockImageResult) => {
    if (importingId) return
    setImportingId(r.id)
    setStockErr(null)
    try {
      const st = r.provider === 'unsplash' ? 'stock-unsplash' : 'stock-pexels'
      const res = await importStockAsset(jobId, r.url, st)
      onInsert({ url: res.data.url, assetId: res.data.assetId, sourceType: st })
    } catch {
      setStockErr('이미지를 가져오지 못했어요. 다른 이미지를 골라 보세요.')
    } finally {
      setImportingId(null)
    }
  }, [jobId, importingId, onInsert])

  return (
    <div className="flex flex-col gap-3">
      <label className="text-[12px] font-semibold text-ink-2">이미지 삽입</label>

      {/* ① 업로드 */}
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        disabled={busy}
        className={`flex flex-col items-center justify-center gap-1 h-20 rounded-lg border-2 border-dashed text-[12px] transition-colors disabled:opacity-50 ${
          dragOver ? 'border-forest-green bg-forest-green/5 text-forest-green' : 'border-border text-ink-3'
        }`}
      >
        {busy ? (
          <span className="text-ink-2">업로드 중…</span>
        ) : (
          <>
            <span className="text-[16px]">⬆</span>
            <span>내 이미지 끌어다 놓거나 클릭</span>
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

      {/* ② 무료 스톡 검색 */}
      <div className="pt-1">
        <p className="text-[11px] font-semibold text-ink-2 mb-2">무료 스톡 이미지 검색</p>
        <form
          onSubmit={(e) => { e.preventDefault(); void runSearch() }}
          className="flex gap-1.5"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="검색어 (예: laboratory, microscope)"
            className="flex-1 min-w-0 h-8 rounded-lg border border-border bg-surface px-2.5 text-[12px] text-ink focus:outline-none focus:border-forest-green"
          />
          <button
            type="submit"
            disabled={searching || !q.trim()}
            className="h-8 px-3 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40 shrink-0"
          >
            {searching ? '검색 중' : '검색'}
          </button>
        </form>

        {stockErr && <p className="text-[11px] text-ink-3 mt-2 leading-snug">{stockErr}</p>}

        {results.length > 0 && (
          <div className="grid grid-cols-2 gap-1.5 mt-2.5">
            {results.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => pick(r)}
                disabled={importingId !== null}
                title={r.credit ? `© ${r.credit} (${r.provider})` : r.provider}
                className="relative aspect-[4/3] rounded-lg overflow-hidden border border-border group disabled:opacity-60"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={r.thumb} alt={r.alt} loading="lazy" className="w-full h-full object-cover" />
                {importingId === r.id ? (
                  <span className="absolute inset-0 grid place-items-center bg-black/45 text-canvas text-[11px] font-semibold">가져오는 중…</span>
                ) : (
                  <span className="absolute inset-0 grid place-items-center bg-black/0 group-hover:bg-black/35 text-canvas text-[11px] font-semibold opacity-0 group-hover:opacity-100 transition-all">+ 삽입</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      <p className="text-[10px] text-ink-3 leading-snug">
        로고·연구실 사진·실데이터는 <b>업로드</b>로, 배경·연출 이미지는 <b>스톡</b>으로. 삽입 후 자유롭게 이동·크기 조절하세요.
      </p>
    </div>
  )
}
