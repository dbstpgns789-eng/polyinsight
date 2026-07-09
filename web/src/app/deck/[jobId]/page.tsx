'use client'

// 단일 저작 덱 뷰 + 편집 (헌법 v3.0 WYSIWYG, Phase 3).
// 보기 모드: 발행 PNG 카드 피드 + 충실성 검증 패널(해자).
// 편집 모드: 저작 HTML을 iframe에 마운트(DeckEditor) → 텍스트 직접수정·요소 재스타일.
//   저장 = 직렬화 HTML을 PATCH → 재검증 + PNG 재렌더 → 검증 패널·PNG 갱신.
// 자연어(NL) 편집은 3c(유료) — 별도.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import AuthGuard from '@/components/auth/AuthGuard'
import { getStatus, getDeck, patchDeck, nlProposeDeck } from '@/lib/api'
import DeckEditor, { type DeckEditorHandle, type SelectedInfo, type HistoryState, type PageState } from '@/components/deck/DeckEditor'
import DeckElementPanel from '@/components/deck/DeckElementPanel'
import DeckMediaPanel from '@/components/deck/DeckMediaPanel'
import DeckAIAssistant from '@/components/deck/DeckAIAssistant'
import { extractEidText } from '@/lib/deckDiff'
import DeckTopBar from '@/components/deck/DeckTopBar'
import DeckViewer from '@/components/deck/DeckViewer'
import DeckOverviewRail from '@/components/deck/DeckOverviewRail'
import DeckRightTabs, { type DeckTab } from '@/components/deck/DeckRightTabs'
import DeckFactPanel from '@/components/deck/DeckFactPanel'
import DeckExportModal from '@/components/deck/DeckExportModal'
import { factBadgeState } from '@/lib/factBadge'
import { extractCardLabels } from '@/lib/deckLabels'

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
  const [rendering, setRendering] = useState(false)
  const deckLoadedRef = useRef(false)

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
  const [rightTab, setRightTab] = useState<DeckTab>('ai')
  const [showExport, setShowExport] = useState(false)
  const [viewIdx, setViewIdx] = useState(0)         // 뷰 모드 현재 카드(뷰어·개요 레일 동기)
  const [railCollapsed, setRailCollapsed] = useState(false)   // 개요 레일 접기(선호 기억)
  const [showFact, setShowFact] = useState(false)   // 팩트체크 온디맨드 드로어(뷰·편집 공통)
  const closeFactRef = useRef<HTMLButtonElement>(null)
  const restoreFocusRef = useRef<Element | null>(null)
  const autoRevealedRef = useRef(false)             // warn 시 뷰 진입 1회 자동노출 가드
  const editorRef = useRef<DeckEditorHandle>(null)

  // 편집 모드 ←/→ 로 페이지 이동 (입력창·텍스트 편집 중엔 캐럿 우선, 팩트 드로어 열림 중엔 무시)
  useEffect(() => {
    if (mode !== 'edit' || showFact) return
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === 'ArrowLeft') editorRef.current?.setPage(page.index - 1)
      else if (e.key === 'ArrowRight') editorRef.current?.setPage(page.index + 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [mode, page.index, showFact])

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
          if (!cancelled) { setDeck(d.data as DeckPayload); setRendering(false) }
          return
        }
        // 콘텐츠 준비됨(RENDER 단계) → 조기 입장(카드는 렌더되는 대로 채워짐)
        if (r.data.stage === 'RENDER' && !deckLoadedRef.current) {
          try {
            const d = await getDeck(jobId)
            if ((d.data as DeckPayload)?.html && !cancelled) {
              setDeck(d.data as DeckPayload); setRendering(true); deckLoadedRef.current = true
            }
          } catch { /* 아직 → 다음 폴링 */ }
        }
      } catch { /* 폴링 재시도 */ }
      if (!cancelled) timer = setTimeout(poll, 1500)
    }
    poll()
    return () => { cancelled = true; clearTimeout(timer) }
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
    setShowFact(false)
    setMode((m) => (m === 'edit' ? 'view' : 'edit'))
  }, [])

  const enterEditAt = useCallback((index: number) => {
    setMode('edit')
    // 마운트 후 해당 카드로 이동(EDITOR_READY 뒤 setPage 반영 위해 다음 틱)
    setTimeout(() => editorRef.current?.setPage(index), 0)
  }, [])

  const onBadgeClick = useCallback(() => setShowFact((v) => !v), [])   // 두 모드 공통 온디맨드

  // 팩트체크 드로어: Esc 닫기 + 포커스 이동(열 때 닫기버튼)/복귀(닫을 때 트리거)
  useEffect(() => {
    if (!showFact) return
    restoreFocusRef.current = document.activeElement
    const t = setTimeout(() => closeFactRef.current?.focus(), 0)
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setShowFact(false) }
    window.addEventListener('keydown', onKey)
    return () => {
      clearTimeout(t)
      window.removeEventListener('keydown', onKey)
      ;(restoreFocusRef.current as HTMLElement | null)?.focus?.()
    }
  }, [showFact])

  // 미확인 수치(warn)가 있는 덱을 뷰로 처음 열면 팩트체크를 1회 자동 노출 — 해자 증거를 필요한 순간 표면화.
  // all-clear(미확인 0)면 녹색 배지만으로 충분해 자동노출 안 함(카드 감상 방해 금지).
  useEffect(() => {
    if (autoRevealedRef.current || mode !== 'view') return
    if (deck?.html && (deck.verify?.unverified ?? 0) > 0) {
      autoRevealedRef.current = true
      setShowFact(true)
    }
  }, [deck?.html, deck?.verify?.unverified, mode])

  // 개요 레일 스토리보드용 카드 역할 라벨(저작 HTML서 best-effort 추출)
  const cardLabels = useMemo(() => extractCardLabels(deck?.html), [deck?.html])

  // 개요 레일 접기 선호 복원/저장(localStorage)
  useEffect(() => {
    try { setRailCollapsed(localStorage.getItem('deck.railCollapsed') === '1') } catch { /* no-op */ }
  }, [])
  const toggleRail = useCallback(() => setRailCollapsed((v) => {
    const nv = !v
    try { localStorage.setItem('deck.railCollapsed', nv ? '1' : '0') } catch { /* no-op */ }
    return nv
  }), [])

  // 진행 중이라도 콘텐츠(html)가 준비되면(RENDER 조기입장) 뷰로. 아니면 진행화면.
  if ((status !== 'DONE' && status !== 'ERROR') && !deck?.html) {
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
  const editing = mode === 'edit'
  const badge = factBadgeState(v, deck.canReverify !== false)
  const saveLabel = saving ? '저장 중…' : dirty ? '저장' : '저장됨'

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-deck-canvas" style={{ wordBreak: 'keep-all' }}>
      <DeckTopBar
        filename={deck.filename ?? '덱'}
        editing={editing}
        badge={badge}
        dirty={dirty}
        onBadgeClick={onBadgeClick}
        factOpen={showFact}
        onToggleMode={toggleMode}
        onExport={() => setShowExport(true)}
        canUndo={history.canUndo}
        canRedo={history.canRedo}
        onUndo={() => editorRef.current?.undo()}
        onRedo={() => editorRef.current?.redo()}
        saveLabel={saveLabel}
        onSave={handleSave}
        saveDisabled={!dirty || saving}
      />

      {editWarnings.length > 0 && (
        <div className="mx-auto mt-3 w-full max-w-[460px] rounded-lg border border-risk-medium-border bg-risk-medium-faint p-3 shrink-0">
          {editWarnings.map((w, i) => <p key={i} className="text-[11px] text-risk-medium leading-snug">{w}</p>)}
        </div>
      )}

      <div className="relative flex flex-1 min-h-0">
        {/* 중앙 */}
        <main className="flex-1 min-w-0 overflow-hidden">
          {editing ? (
            <div className="h-full overflow-y-auto flex flex-col items-center py-6 gap-3">
              {page.count > 1 && (
                <div className="flex items-center justify-center gap-3 select-none">
                  <button onClick={() => editorRef.current?.setPage(page.index - 1)} disabled={page.index <= 0}
                    aria-label="이전 카드" className="w-9 h-9 rounded-full border border-border text-ink-2 disabled:opacity-30">‹</button>
                  <span className="text-[13px] tabular-nums text-ink-2 min-w-[52px] text-center">{page.index + 1} / {page.count}</span>
                  <button onClick={() => editorRef.current?.setPage(page.index + 1)} disabled={page.index >= page.count - 1}
                    aria-label="다음 카드" className="w-9 h-9 rounded-full border border-border text-ink-2 disabled:opacity-30">›</button>
                </div>
              )}
              <div className="relative w-full max-w-[460px]">
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
                {(proposing || !!pending) && (
                  <div className="absolute inset-0 z-10 cursor-not-allowed" aria-hidden="true"
                    title={proposing ? 'AI가 제안 중…' : 'AI 제안 확인 중 — 적용/취소 후 편집하세요'} />
                )}
              </div>
            </div>
          ) : (
            <DeckViewer jobId={jobId} cardCount={deck.cardCount || 7} ver={ver} rendering={rendering}
              onEditCard={enterEditAt} index={viewIdx} onIndex={setViewIdx} />
          )}
        </main>

        {/* 뷰 모드 우측 '덱 개요' 레일 — 편집 모드 도구 레일과 구조 대칭(휑함 해소). 접기 가능. */}
        {!editing && !railCollapsed && (
          <DeckOverviewRail
            jobId={jobId}
            cardCount={deck.cardCount || 7}
            ver={ver}
            index={viewIdx}
            onSelect={setViewIdx}
            title={deck.filename ?? '덱'}
            verify={v}
            onOpenFact={() => setShowFact(true)}
            labels={cardLabels}
            onCollapse={toggleRail}
          />
        )}
        {/* 접힘 상태 — 우측 가장자리 펼치기 탭 */}
        {!editing && railCollapsed && (
          <button onClick={toggleRail} title="덱 개요 펼치기" aria-label="덱 개요 펼치기"
            className="absolute top-1/2 -translate-y-1/2 right-0 z-20 h-16 w-6 rounded-l-lg bg-surface border border-r-0 border-deck-line shadow-card grid place-items-center text-ink-3 hover:text-ink transition-colors">‹</button>
        )}

        {/* 우측 도구 패널 — 편집 모드에만 */}
        {editing && (
          <aside className="w-[372px] shrink-0 border-l border-deck-line bg-surface min-h-0">
            <DeckRightTabs
              active={rightTab}
              onTab={setRightTab}
              ai={
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
              }
              inspector={
                <div className="flex flex-col gap-5">
                  <DeckMediaPanel jobId={jobId} onInsert={(p) => { editorRef.current?.insertImage(p); setDirty(true) }} />
                  <div className="h-px bg-border" />
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
                </div>
              }
            />
          </aside>
        )}

        {/* 팩트체크 = 뷰·편집 공통 온디맨드 드로어(상단 배지 토글). 일관된 위치 */}
        {showFact && (
          <>
            <div className="absolute inset-0 z-30 bg-black/10" aria-hidden="true" onClick={() => setShowFact(false)} />
            <aside id="fact-drawer" role="dialog" aria-modal="true" aria-label="팩트 체크"
              className="absolute top-0 right-0 z-40 h-full w-[400px] max-w-[88%] bg-surface border-l border-deck-line shadow-modal flex flex-col">
              {/* 제목은 아래 DeckFactPanel이 소유(중복 방지) — 헤더 바엔 닫기만 */}
              <div className="flex items-center justify-end px-3 h-11 shrink-0">
                <button ref={closeFactRef} onClick={() => setShowFact(false)} aria-label="팩트 체크 닫기"
                  className="w-7 h-7 rounded-lg grid place-items-center text-ink-3 hover:text-ink hover:bg-bg-subtle transition-colors">✕</button>
              </div>
              <div className="flex-1 overflow-y-auto px-5 pb-5">
                <DeckFactPanel verify={v} canReverify={deck.canReverify !== false} />
              </div>
            </aside>
          </>
        )}
      </div>

      {showExport && (
        <DeckExportModal
          jobId={jobId}
          filename={deck.filename ?? '덱'}
          cardCount={deck.cardCount || 7}
          unverified={v?.unverified ?? 0}
          onClose={() => setShowExport(false)}
        />
      )}
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
