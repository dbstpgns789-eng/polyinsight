'use client'

// 단일 저작 덱 뷰 + 편집 (헌법 v3.0 WYSIWYG, Phase 3).
// 보기 모드: 발행 PNG 카드 피드 + 충실성 검증 패널(해자).
// 편집 모드: 저작 HTML을 iframe에 마운트(DeckEditor) → 텍스트 직접수정·요소 재스타일.
//   저장 = 직렬화 HTML을 PATCH → 재검증 + PNG 재렌더 → 검증 패널·PNG 갱신.
// 자연어(NL) 편집은 3c(유료) — 별도.

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import AuthGuard from '@/components/auth/AuthGuard'
import { getStatus, getDeck, patchDeck, nlProposeDeck, exportDeck, getDeckCardUrl, getExportDownloadUrl } from '@/lib/api'
import DeckEditor, { type DeckEditorHandle, type SelectedInfo, type HistoryState, type PageState } from '@/components/deck/DeckEditor'
import DeckElementPanel from '@/components/deck/DeckElementPanel'
import DeckMediaPanel from '@/components/deck/DeckMediaPanel'
import DeckAIAssistant from '@/components/deck/DeckAIAssistant'
import { extractEidText } from '@/lib/deckDiff'

interface VerifyClaim { value: string; context: string; verified: boolean }
interface VerifyData { verified: number; unverified: number; claims: VerifyClaim[] }
interface DeckPayload {
  jobId: string; filename?: string; status: string; warnings?: string[]
  html?: string | null; verify?: VerifyData | null; cardCount: number; canReverify?: boolean
}

function abortReason(warnings?: string[]): string | null {
  const w = (warnings ?? []).find((x) => x.startsWith('ABORT-') || x.startsWith('ERR-'))
  return w ? w.replace(/^(ABORT|ERR)-[A-Z0-9]*:\s*/, '') : null
}

// ── 생성 진행 화면 — 진짜 공정 공개 (Mirra식 극장이되 문구=실제 파이프라인 단계) ──
// 가짜 남은시간·가짜 취소버튼 금지. progress(10→40→70→85)는 실측, 사이는 완만히 creep.
const PIPELINE_STEPS = [
  { key: 'S1', emoji: '📖', label: '논문 읽기', msg: '논문을 읽고 있어요 — 텍스트와 수치를 추출합니다' },
  { key: 'AUTHOR', emoji: '✍️', label: 'AI 저작', msg: 'AI가 스토리와 디자인을 저작하고 있어요' },
  { key: 'VERIFY', emoji: '🔍', label: '수치 검증', msg: '모든 수치를 원문과 대조하고 있어요' },
  { key: 'RENDER', emoji: '🎨', label: '카드 렌더', msg: '카드를 그리고 있어요' },
]
const STAGE_CAP: Record<string, number> = { S1: 38, AUTHOR: 68, VERIFY: 83, RENDER: 97 }

function GenerationTheater({ stage, progress }: { stage: string; progress: number }) {
  const [elapsed, setElapsed] = useState(0)
  const [creep, setCreep] = useState(0)
  const stageIdx = Math.max(0, PIPELINE_STEPS.findIndex((s) => s.key === stage))
  const current = PIPELINE_STEPS[stageIdx]

  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000)
    return () => clearInterval(t)
  }, [])

  // 단계 사이 creep — 실측 progress에서 출발해 다음 단계 직전까지만 서서히 (0.15%/s)
  useEffect(() => { setCreep(0) }, [stage])
  useEffect(() => {
    const t = setInterval(() => setCreep((c) => c + 0.15), 1000)
    return () => clearInterval(t)
  }, [stage])
  const pct = Math.min(Math.max(progress, 5) + creep, STAGE_CAP[stage] ?? 97)

  const mm = String(Math.floor(elapsed / 60))
  const ss = String(elapsed % 60).padStart(2, '0')

  return (
    <div className="flex items-center justify-center min-h-screen bg-canvas-subtle px-6">
      <div className="w-full max-w-[420px] text-center deck-fade-up">
        <div className="text-[42px] mb-4" aria-hidden="true">{current.emoji}</div>
        <p className="text-[17px] font-bold text-ink mb-6">{current.msg}</p>

        <div className="h-1.5 rounded-full bg-border overflow-hidden mb-2" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
          <div
            className="h-full rounded-full transition-[width] duration-1000 ease-linear"
            style={{ width: `${pct}%`, background: 'linear-gradient(90deg, var(--accent), var(--accent-bright))' }}
          />
        </div>
        <div className="flex justify-between text-[12.5px] text-ink-3 mb-8">
          <span>{mm}:{ss}</span>
          <span>보통 2~3분</span>
        </div>

        <div className="inline-flex flex-col items-start gap-2 mb-8" aria-label="생성 단계">
          {PIPELINE_STEPS.map((s, i) => (
            <div key={s.key} className={`flex items-center gap-2.5 text-[13.5px] ${i < stageIdx ? 'text-forest-green-deep' : i === stageIdx ? 'text-ink font-bold' : 'text-ink-3'}`}>
              {i < stageIdx ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
              ) : i === stageIdx ? (
                <span className="w-3.5 h-3.5 rounded-full border-2 border-forest-green border-t-transparent animate-spin inline-block" aria-hidden="true" />
              ) : (
                <span className="w-3.5 h-3.5 rounded-full border-2 border-border inline-block" aria-hidden="true" />
              )}
              {s.label}
              {s.key === 'VERIFY' && <span className="text-[11px] font-bold text-forest-green-deep bg-forest-green-wash px-1.5 py-0.5 rounded-md">원문 대조</span>}
            </div>
          ))}
        </div>

        <p className="text-[12.5px] text-ink-3 mb-3">이 화면을 벗어나도 생성은 계속됩니다.</p>
        <Link href="/dashboard" className="text-[13px] font-semibold text-ink-3 hover:text-forest-green-deep transition-colors">← 대시보드</Link>
      </div>
    </div>
  )
}

function DeckPageInner() {
  const { jobId } = useParams() as { jobId: string }
  const [status, setStatus] = useState<string>('PENDING')
  const [stage, setStage] = useState<string>('')
  const [progress, setProgress] = useState(0)
  const [deck, setDeck] = useState<DeckPayload | null>(null)
  const [exporting, setExporting] = useState(false)

  // 편집 상태
  const [mode, setMode] = useState<'view' | 'edit'>('view')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<SelectedInfo | null>(null)
  const [ver, setVer] = useState(0)            // PNG 캐시 무력화 버전
  const [editWarnings, setEditWarnings] = useState<string[]>([])
  const [proposing, setProposing] = useState(false)
  const [committing, setCommitting] = useState(false)
  const [reverting, setReverting] = useState(false)
  const [pending, setPending] = useState<{
    html: string; verify: VerifyData; afterText: string | null
    target?: { eid?: string; cardIndex?: number; quotedText?: string }; beforeText: string | null
  } | null>(null)
  const [snapshots, setSnapshots] = useState<string[]>([])
  const [history, setHistory] = useState<HistoryState>({ canUndo: false, canRedo: false })
  const [page, setPage] = useState<PageState>({ index: 0, count: 0 })
  const editorRef = useRef<DeckEditorHandle>(null)

  // 편집 모드 ←/→ 로 페이지 이동 (입력창·텍스트 편집 중엔 캐럿 우선 → 무시)
  useEffect(() => {
    if (mode !== 'edit') return
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === 'ArrowLeft') editorRef.current?.setPage(page.index - 1)
      else if (e.key === 'ArrowRight') editorRef.current?.setPage(page.index + 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mode, page.index])

  // 상태 폴링 → DONE이면 덱 로드
  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const r = await getStatus(jobId)
        if (cancelled) return
        setStatus(r.data.status)
        setStage(r.data.stage ?? '')
        setProgress(r.data.progress ?? 0)
        if (r.data.status === 'DONE' || r.data.status === 'ERROR') {
          const d = await getDeck(jobId)
          if (!cancelled) setDeck(d.data as DeckPayload)
          return
        }
      } catch { /* 폴링 재시도 */ }
      if (!cancelled) timer = setTimeout(poll, 1500)
    }
    poll()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [jobId])

  const handleExport = useCallback(async () => {
    setExporting(true)
    try {
      const r = await exportDeck(jobId)
      window.location.href = getExportDownloadUrl(r.data.exportId)
    } finally { setExporting(false) }
  }, [jobId])

  const handleSave = useCallback(async () => {
    if (!editorRef.current) return
    setSaving(true)
    try {
      const html = await editorRef.current.getHtml()
      const r = await patchDeck(jobId, html)
      setDeck((prev) => prev ? {
        ...prev, html, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      setEditWarnings(r.data.warnings ?? [])
      setVer((x) => x + 1)        // 재렌더된 PNG 다시 받기
      setDirty(false)
      setSelected(null)
    } finally { setSaving(false) }
  }, [jobId])

  const handlePropose = useCallback(async (instruction: string) => {
    if (!editorRef.current) return
    setProposing(true)
    try {
      const html = await editorRef.current.getHtml()   // 라이브 serialize(미저장 편집+eid 포함)
      // pending이 있으면(=[다른 안]) 제안 시점 타깃을 동결 사용. 없으면(신규 제안) 현재 선택에서.
      const target = pending?.target ?? (selected?.eid
        ? { eid: selected.eid, cardIndex: selected.cardIndex, quotedText: selected.quotedText }
        : undefined)
      const beforeText = pending?.beforeText ?? selected?.quotedText ?? null
      const r = await nlProposeDeck(jobId, instruction, html, target)
      const afterText = target?.eid ? extractEidText(r.data.html, target.eid) : null
      setPending({ html: r.data.html, verify: r.data.verify, afterText, target, beforeText })
    } catch {
      setEditWarnings(['AI 제안을 받지 못했어요. 잠시 후 다시 시도해 주세요.'])
    } finally { setProposing(false) }
  }, [jobId, selected, pending])

  const handleCommit = useCallback(async () => {
    if (!pending) return
    setCommitting(true)
    try {
      const snapshot = deck?.html
      const r = await patchDeck(jobId, pending.html)
      setDeck((prev) => prev ? {
        ...prev, html: pending.html, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      if (snapshot) setSnapshots((s) => [...s, snapshot])   // commit 직전 html 스냅샷
      setEditWarnings(r.data.warnings ?? [])
      setVer((x) => x + 1)
      setPending(null)
      setDirty(false)
      setSelected(null)
    } finally { setCommitting(false) }
  }, [jobId, pending, deck])

  const handleDiscard = useCallback(() => setPending(null), [])

  const handleRevert = useCallback(async () => {
    const snapshot = snapshots[snapshots.length - 1]
    if (!snapshot) return
    setReverting(true)
    try {
      const r = await patchDeck(jobId, snapshot)
      setDeck((prev) => prev ? {
        ...prev, html: snapshot, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      setSnapshots((s) => s.slice(0, -1))
      setEditWarnings(r.data.warnings ?? [])
      setVer((x) => x + 1)
      setPending(null)
      setSelected(null)
    } finally { setReverting(false) }
  }, [jobId, snapshots])

  const toggleMode = useCallback(() => {
    setSelected(null)
    setEditWarnings([])
    setPending(null)
    setMode((m) => (m === 'edit' ? 'view' : 'edit'))
  }, [])

  // ── 진행 중 — 실제 파이프라인 공정 공개 ──
  if (status !== 'DONE' && status !== 'ERROR') {
    return <GenerationTheater stage={stage || 'S1'} progress={progress} />
  }

  // ── 실패 ──
  if (status === 'ERROR' || !deck?.html) {
    const reason = abortReason(deck?.warnings)
    return (
      <div className="flex items-center justify-center h-screen bg-canvas-subtle">
        <div className="text-center max-w-md px-6">
          <p className="text-4xl mb-3">⚠️</p>
          <p className="text-[14px] text-ink-2 font-medium">{reason || '덱을 생성하지 못했습니다.'}</p>
          <p className="text-[12px] text-ink-3 mt-2">스캔본(이미지) PDF는 텍스트를 못 읽어요 — 텍스트가 살아있는 PDF로 다시 시도해 주세요.</p>
          <div className="flex items-center justify-center gap-3 mt-6">
            <Link href="/deck/new" className="btn btn-primary">다시 시도</Link>
            <Link href="/dashboard" className="btn btn-outline">← 대시보드</Link>
          </div>
        </div>
      </div>
    )
  }

  const v = deck.verify
  const flagged = v?.claims.filter((c) => !c.verified) ?? []
  const editing = mode === 'edit'
  const cardNums = Array.from({ length: deck.cardCount || 7 }, (_, i) => i + 1)

  return (
    <div className="flex h-screen overflow-hidden bg-canvas-subtle" style={{ wordBreak: 'keep-all' }}>
      {/* 카드 영역 */}
      <main className="flex-1 overflow-y-auto py-10 flex flex-col items-center gap-8">
        <div className="w-full max-w-[460px] flex items-center justify-between px-1 gap-2">
          <span className="text-[14px] font-semibold text-ink truncate flex-1">{deck.filename}</span>

          <button
            onClick={toggleMode}
            className={`text-[13px] font-semibold px-3 py-2 rounded-lg border ${
              editing ? 'border-forest-green text-forest-green' : 'border-border text-ink-2'
            }`}
          >
            {editing ? '편집 종료' : '편집'}
          </button>

          {editing && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => editorRef.current?.undo()}
                disabled={!history.canUndo}
                title="실행 취소 (Ctrl+Z)"
                className="w-9 h-9 rounded-lg border border-border text-ink-2 disabled:opacity-30"
              >↶</button>
              <button
                onClick={() => editorRef.current?.redo()}
                disabled={!history.canRedo}
                title="다시 실행 (Ctrl+Shift+Z)"
                className="w-9 h-9 rounded-lg border border-border text-ink-2 disabled:opacity-30"
              >↷</button>
            </div>
          )}

          {editing ? (
            <button
              onClick={handleSave}
              disabled={!dirty || saving}
              className="text-[13px] font-semibold px-4 py-2 rounded-lg bg-forest-green text-canvas disabled:opacity-40"
            >
              {saving ? '저장 중…' : dirty ? '저장' : '저장됨'}
            </button>
          ) : (
            <button
              onClick={handleExport}
              disabled={exporting}
              className="text-[13px] font-semibold px-4 py-2 rounded-lg bg-forest-green text-canvas disabled:opacity-50"
            >
              {exporting ? '내보내는 중…' : 'ZIP 내보내기'}
            </button>
          )}
        </div>

        {editWarnings.length > 0 && (
          <div className="w-full max-w-[460px] rounded-lg border border-amber-300 bg-amber-50 p-3">
            {editWarnings.map((w, i) => (
              <p key={i} className="text-[11px] text-amber-700 leading-snug">{w}</p>
            ))}
          </div>
        )}

        {editing ? (
          <div className="w-full max-w-[460px] flex flex-col gap-3">
            {page.count > 1 && (
              <div className="flex items-center justify-center gap-3 select-none">
                <button
                  onClick={() => editorRef.current?.setPage(page.index - 1)}
                  disabled={page.index <= 0}
                  aria-label="이전 카드"
                  className="w-9 h-9 rounded-full border border-border text-ink-2 disabled:opacity-30"
                >‹</button>
                <span className="text-[13px] tabular-nums text-ink-2 min-w-[52px] text-center">
                  {page.index + 1} / {page.count}
                </span>
                <button
                  onClick={() => editorRef.current?.setPage(page.index + 1)}
                  disabled={page.index >= page.count - 1}
                  aria-label="다음 카드"
                  className="w-9 h-9 rounded-full border border-border text-ink-2 disabled:opacity-30"
                >›</button>
              </div>
            )}
            <div className="relative">
              <DeckEditor
                ref={editorRef}
                html={deck.html as string}
                mode={mode}
                onSelected={setSelected}
                onDeselected={() => setSelected(null)}
                onDirty={() => { setDirty(true); setPending(null) }}
                onHistory={setHistory}
                onPage={setPage}
              />
              {/* AI 제안 중/대기 중엔 캔버스 잠금 — in-flight 직접편집·재선택으로 제안이 스테일해지는 것 차단 */}
              {(proposing || !!pending) && (
                <div
                  className="absolute inset-0 z-10 cursor-not-allowed"
                  aria-hidden="true"
                  title={proposing ? 'AI가 제안 중…' : 'AI 제안 확인 중 — 적용/취소 후 편집하세요'}
                />
              )}
            </div>
          </div>
        ) : (
          cardNums.map((n) => (
            <img
              key={n}
              src={getDeckCardUrl(deck.jobId, n, ver || undefined)}
              alt={`card ${n}`}
              className="w-full max-w-[460px] rounded-[10px] shadow-md"
              style={{ aspectRatio: '1080 / 1350', objectFit: 'cover', background: '#11152B' }}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
            />
          ))
        )}
      </main>

      {/* 우측 패널: 편집 시 요소 패널, 항상 충실성 검증(해자) */}
      <aside className="w-[360px] shrink-0 border-l border-border bg-surface overflow-y-auto p-6">
        {editing && (
          <section className="mb-7">
            <h2 className="text-[15px] font-bold text-ink mb-3">요소 편집</h2>
            <DeckMediaPanel
              jobId={jobId}
              onInsert={(p) => { editorRef.current?.insertImage(p); setDirty(true) }}
            />
            <div className="h-px bg-border my-6" />
            <DeckElementPanel
              selected={selected}
              onStyle={(prop, value) => editorRef.current?.applyStyle(prop, value)}
              onDelete={() => editorRef.current?.deleteElement()}
              onMove={(dir) => editorRef.current?.moveElement(dir)}
              onRevertFlow={() => editorRef.current?.revertFlow()}
              onAlign={(axis) => editorRef.current?.align(axis)}
              onDistribute={(axis) => editorRef.current?.distribute(axis)}
              onSetRect={(r) => editorRef.current?.setRect(r)}
            />
            <div className="h-px bg-border my-6" />
            <DeckAIAssistant
              selected={selected}
              proposing={proposing}
              pending={!!pending}
              committing={committing}
              beforeText={pending?.beforeText ?? selected?.quotedText ?? null}
              afterText={pending?.afterText ?? null}
              onPropose={handlePropose}
              onCommit={handleCommit}
              onDiscard={handleDiscard}
              canRevert={snapshots.length > 0}
              reverting={reverting}
              onRevert={handleRevert}
            />
            <div className="h-px bg-border mt-6" />
          </section>
        )}

        <h2 className="text-[15px] font-bold text-ink mb-1">충실성 검증</h2>
        <p className="text-[12px] text-ink-3 mb-5">
          {deck.canReverify === false
            ? '이 덱은 원문이 없어 편집 시 재검증되지 않습니다. 재생성하면 복원됩니다.'
            : '막지 않고, 출처를 분류해 보여줍니다. 최종 판단은 사용자.'}
        </p>

        <div className="flex gap-3 mb-6">
          <div className="flex-1 rounded-xl border border-border p-3 text-center">
            <div className="text-[22px] font-extrabold text-forest-green">{v?.verified ?? 0}</div>
            <div className="text-[11px] text-ink-3 mt-1">논문 근거 확인</div>
          </div>
          <div className="flex-1 rounded-xl border border-border p-3 text-center">
            <div className="text-[22px] font-extrabold text-amber-600">{v?.unverified ?? 0}</div>
            <div className="text-[11px] text-ink-3 mt-1">사용자 판단 필요</div>
          </div>
        </div>

        {flagged.length > 0 ? (
          <div>
            <p className="text-[12px] font-semibold text-ink-2 mb-2">
              ⚠️ 원문에 없는 수치 — AI가 더한 맥락/예시인지 확인하세요:
            </p>
            <ul className="flex flex-col gap-2">
              {flagged.map((c, i) => (
                <li key={i} className="rounded-lg border border-border bg-canvas-subtle p-3">
                  <span className="text-[14px] font-bold text-ink">{c.value}</span>
                  <p className="text-[11px] text-ink-3 mt-1 leading-snug">…{c.context}…</p>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-[13px] text-ink-3">모든 수치가 원문에서 추적됐습니다.</p>
        )}
      </aside>
    </div>
  )
}

export default function DeckPage() {
  return (
    <AuthGuard>
      <DeckPageInner />
    </AuthGuard>
  )
}
