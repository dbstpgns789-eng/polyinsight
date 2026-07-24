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
import { getStatus, getDeck, patchDeck, nlProposeDeck, friendlyError } from '@/lib/api'
import DeckEditor, { type DeckEditorHandle, type SelectedInfo, type HistoryState, type PageState, type LayerItem } from '@/components/deck/DeckEditor'
import DeckElementPanel from '@/components/deck/DeckElementPanel'
import DeckLayersPanel from '@/components/deck/DeckLayersPanel'
import DeckMediaPanel from '@/components/deck/DeckMediaPanel'
import DeckAIAssistant from '@/components/deck/DeckAIAssistant'
import { extractEidText } from '@/lib/deckDiff'
import DeckTopBar from '@/components/deck/DeckTopBar'
import DeckViewer from '@/components/deck/DeckViewer'
import DeckOverviewRail from '@/components/deck/DeckOverviewRail'
import DeckRightTabs, { type DeckTab } from '@/components/deck/DeckRightTabs'
import DeckFactPanel from '@/components/deck/DeckFactPanel'
import DeckExportModal from '@/components/deck/DeckExportModal'
import { extractCardLabels } from '@/lib/deckLabels'
import { failureReason } from '@/lib/failureReason'
import DeckFactJumpBar from '@/components/deck/DeckFactJumpBar'
import { reviewQueue, type ReviewItem, type VerifyData } from '@/lib/verifyStatus'
import { useAutosave } from '@/lib/useAutosave'

interface DeckPayload {
  jobId: string; filename?: string; status: string; warnings?: string[]
  html?: string | null; verify?: VerifyData | null; cardCount: number; canReverify?: boolean
}

// 실패 원인 분류는 lib/failureReason — 어떤 실패든 "스캔본 탓"을 하던 버그를 고쳤다(2026-07-14).

// ── 생성 진행 화면 — 진짜 공정 공개 (Mirra식 극장이되 문구=실제 파이프라인 단계) ──
// 가짜 남은시간·가짜 취소버튼 금지. progress(10→40→70→85)는 실측, 사이는 완만히 creep.
const PIPELINE_STEPS = [
  { key: 'S1', emoji: '📖', label: '논문 읽기', msg: '논문을 읽고 있어요. 텍스트와 그림, 수치를 꺼냅니다' },
  { key: 'AUTHOR', emoji: '✍️', label: 'AI 저작', msg: 'AI가 논문의 그림을 보며 스토리와 디자인을 저작하고 있어요' },
  // Best-of-N(AUTHOR_CANDIDATES>1)일 때만 등장 — 여러 시안을 만들어 심사해 최고를 고른다
  { key: 'SELECT', emoji: '⚖️', label: '시안 비교', msg: '여러 시안을 만들어 나란히 놓고 가장 좋은 것을 고르고 있어요' },
  // 비전 자기수정 — 제품의 셀링포인트: AI가 자기 결과물을 '눈으로 보고' 고친다
  { key: 'POLISH', emoji: '👁️', label: '보고 다듬기', msg: 'AI가 완성된 카드를 직접 보면서 겹침·빈칸·어려운 말을 다듬고 있어요' },
  { key: 'VERIFY', emoji: '🔍', label: '수치 검증', msg: '모든 수치를 원문과 대조하고 있어요' },
  { key: 'RENDER', emoji: '🎨', label: '카드 렌더', msg: '카드를 그리고 있어요' },
]
const STAGE_CAP: Record<string, number> = {
  S1: 38, AUTHOR: 55, SELECT: 62, POLISH: 78, VERIFY: 86, RENDER: 97,
}

function GenerationTheater({ stage, progress }: { stage: string; progress: number }) {
  const [elapsed, setElapsed] = useState(0)
  const [creep, setCreep] = useState(0)
  // 모르는 스테이지(백엔드가 새 단계를 추가했는데 프론트가 아직 모를 때)에서 -1이 나오면
  // 진행이 처음으로 되돌아가 보인다. 마지막으로 알던 단계를 유지한다.
  const [lastIdx, setLastIdx] = useState(0)
  const found = PIPELINE_STEPS.findIndex((s) => s.key === stage)
  const stageIdx = found >= 0 ? found : lastIdx
  useEffect(() => { if (found >= 0) setLastIdx(found) }, [found])
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
  // 진행률은 절대 뒤로 가지 않는다 — creep으로 앞선 뒤 다음 단계의 실측 progress가 더 낮아도
  // 후퇴하면 "뭔가 잘못됐나" 싶다(POLISH cap 78 → VERIFY progress 70 구간에서 실제로 발생).
  const [pct, setPct] = useState(5)
  useEffect(() => {
    const target = Math.min(Math.max(progress, 5) + creep, STAGE_CAP[stage] ?? 97)
    setPct((p) => Math.max(p, target))
  }, [progress, creep, stage])

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
          <span>논문에 따라 2~5분</span>
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
  const autosaveRef = useRef<{ markClean: () => void } | null>(null)   // 커밋 경로가 자동저장에 '이미 저장됨'을 알린다

  // 편집 상태
  const [mode, setMode] = useState<'view' | 'edit'>('view')
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<SelectedInfo | null>(null)
  const [layers, setLayers] = useState<LayerItem[]>([])   // 현재 카드 원자 요소 목록(레이어 패널)
  const [ver, setVer] = useState(0)            // PNG 캐시 무력화 버전
  const [pngStale, setPngStale] = useState(false)   // 자동저장으로 html은 바뀌었는데 PNG는 아직 안 받은 상태
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
  const [zoomInfo, setZoomInfo] = useState({ eff: 1, fit: 1 })   // 현재 배율(줌 % 표시). 줌 상태는 DeckEditor 소유
  const [rightTab, setRightTab] = useState<DeckTab>('ai')
  const [showExport, setShowExport] = useState(false)
  const [savedAt, setSavedAt] = useState<string>()  // 마지막 저장 시각 hh:mm
  const stampSaved = useCallback(() => {
    const d = new Date()
    setSavedAt(`${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`)
  }, [])
  const [viewIdx, setViewIdx] = useState(0)         // 뷰 모드 현재 카드(뷰어·개요 레일 동기)
  const [railCollapsed, setRailCollapsed] = useState(false)   // 개요 레일 접기(선호 기억)
  const [showFact, setShowFact] = useState(false)   // 팩트체크 온디맨드 드로어(뷰·편집 공통)
  const [jump, setJump] = useState<{ item: ReviewItem; index: number } | null>(null)  // 팩트 점프 중인 항목
  const [jumpFound, setJumpFound] = useState<boolean | null>(null)                    // 카드 안에서 찾았나
  const closeFactRef = useRef<HTMLButtonElement>(null)
  const restoreFocusRef = useRef<Element | null>(null)
  const editorRef = useRef<DeckEditorHandle>(null)
  const pendingHLRef = useRef<{ value: string; card: number } | null>(null)  // 카드 준비되면 마킹할 수치
  const activeHLRef = useRef<string | null>(null)  // 지금 점프 중인 수치 — 늦게 온 HIGHLIGHTED 응답 무시용

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

  // 저장 코어 — silent=true(자동저장)면 선택을 풀지 않고 PNG ver도 올리지 않는다.
  //   · 선택을 풀면 3초마다 사용자의 선택이 사라진다(편집 불가능해진다)
  //   · 편집 캔버스는 iframe이라 PNG가 필요 없다 — ver를 올리면 서버 렌더 7장이 헛돈다
  const saveCore = useCallback(async (silent: boolean) => {
    if (!editorRef.current) return
    setSaving(true)
    try {
      const html = await editorRef.current.getHtml()
      const r = await patchDeck(jobId, html)
      setDeck((prev) => prev ? {
        ...prev, html, verify: r.data.verify, cardCount: r.data.cardCount,
      } : prev)
      setEditWarnings(r.data.warnings ?? [])
      stampSaved()
      if (silent) {
        setPngStale(true)         // 뷰어로 갈 때 한 번만 PNG를 갱신한다
      } else {
        setVer((x) => x + 1)      // 재렌더된 PNG 다시 받기
        setSelected(null)
      }
    } finally { setSaving(false) }
  }, [jobId, stampSaved])

  const handleSave = useCallback(() => saveCore(false), [saveCore])

  // 자동저장 — 편집 모드에서만. AI 제안(pending)이 떠 있으면 돌지 않는다(사용자가 수락/버림을 결정 중이다).
  const autosave = useAutosave({
    enabled: mode === 'edit',
    save: () => saveCore(true),
    isBlocked: () => pending !== null || saving || proposing || committing || reverting,
  })
  autosaveRef.current = autosave

  // 직접 편집 — 대기 중 AI 제안은 폐기하고(기존 동작), 자동저장을 예약한다
  const handleDirty = useCallback(() => {
    setPending(null)          // 직접 편집은 대기 중 AI 제안을 폐기한다(기존 동작)
    autosave.markDirty()
  }, [autosave])

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
    } catch (e) {
      setEditWarnings([friendlyError(e, 'AI가 응답하지 않았어요. 다시 시도해 주세요.')])
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
      setPngStale(false)
      autosaveRef.current?.markClean()   // 제안 수락이 이미 저장했다 — 같은 html 재저장 방지
      stampSaved()
      setSelected(null)
    } finally { setCommitting(false) }
  }, [jobId, pending, deck, stampSaved])

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

  const toggleMode = useCallback(async () => {
    // 편집 → 뷰: 마지막 편집을 저장하고, 그때 **한 번만** PNG를 새로 받는다.
    if (mode === 'edit') {
      await autosave.flush()
      if (pngStale) {
        setVer((x) => x + 1)
        setPngStale(false)
      }
    }
    setSelected(null)
    setEditWarnings([])
    setPending(null)
    setShowFact(false)
    setJump(null)                     // 모드 전환 시 점프 문맥 바 정리(stale 바 재등장 방지)
    activeHLRef.current = null
    pendingHLRef.current = null
    // 보던 카드 그대로 이어가기(양방향 동기). 편집 진입 카드는 viewIdx → DeckEditor initialPage로 반영
    if (mode === 'view') {
      setMode('edit')                 // viewIdx=보던 카드 → initialPage로 EDITOR_READY 뒤 이동
    } else {
      setViewIdx(page.index)          // 편집→뷰: 편집하던 카드로 뷰어 동기
      setMode('view')
    }
  }, [mode, page.index, autosave, pngStale])

  const enterEditAt = useCallback((index: number) => {
    setViewIdx(index)   // initialPage로 전달돼 EDITOR_READY 뒤 해당 카드로 이동
    setMode('edit')
  }, [])

  // 팩트 패널 수치 클릭 → 그 카드로 데려가 수치에 마커를 씌운다.
  // 뷰 모드면 편집 모드로 전환한다(뷰어는 PNG라 텍스트 좌표를 모른다).
  // 안전: toggleMode의 ver 상승은 pngStale 가드를 타므로, 보기만 하고 나오면 재렌더가 없다.
  const queue = useMemo(() => reviewQueue(deck?.verify), [deck?.verify])

  const jumpTo = useCallback((index: number) => {
    const item = queue[index]
    if (!item || item.card === null) return
    setJump({ item, index })
    setJumpFound(null)
    setShowFact(false)
    activeHLRef.current = item.value
    // 벽시계 지연으로 마킹하지 않는다 — 뷰→편집 전환은 iframe을 새로 마운트해서
    // 리스너가 붙기 전이면 HIGHLIGHT 메시지가 유실된다. 대신 에디터가 그 카드로 페이징을
    // 마치고 PAGE를 쏘는 순간(handlePage)에 마킹한다 = 확실한 준비 신호.
    pendingHLRef.current = { value: item.value, card: item.card }
    if (mode === 'view') {
      enterEditAt(item.card)                 // EDITOR_READY 후 initialPage로 그 카드에 진입 → PAGE 발신
    } else {
      editorRef.current?.setPage(item.card)  // 같은 카드여도 setPage는 PAGE를 다시 쏜다
    }
  }, [queue, mode, enterEditAt])

  // 에디터가 카드로 페이징을 마치고 보낸 PAGE 신호 — 대기 중인 하이라이트가 그 카드면 지금 마킹한다.
  const handlePage = useCallback((pg: PageState) => {
    setPage(pg)
    const p = pendingHLRef.current
    if (p && pg.index === p.card) {
      pendingHLRef.current = null
      editorRef.current?.highlight(p.value)
    }
  }, [])

  const handleJump = useCallback((it: { value: string; card: number }) => {
    const i = queue.findIndex((q) => q.value === it.value && q.card === it.card)
    jumpTo(i < 0 ? 0 : i)
  }, [queue, jumpTo])

  const closeJump = useCallback(() => {
    setJump(null)
    activeHLRef.current = null
    pendingHLRef.current = null
    editorRef.current?.clearHighlight()
  }, [])

  // 뷰 모드는 팩트가 우측 상시 노출 → 배지=상태만. 편집 모드만 드로어 토글.
  const onBadgeClick = useCallback(() => { if (mode === 'edit') setShowFact((v) => !v) }, [mode])

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

  // ── 실패 ── 원인별로 다른 안내. 엉뚱한 탓(스캔본)을 하지 않는다.
  if (status === 'ERROR' || !deck?.html) {
    const fail = failureReason(deck?.warnings)
    return (
      <div className="flex items-center justify-center h-screen bg-canvas-subtle">
        <div className="text-center max-w-md px-6">
          <p className="text-4xl mb-3">{fail.kind === 'credit' ? '⏳' : '⚠️'}</p>
          <p className="text-[14px] text-ink-2 font-medium">{fail.title}</p>
          <p className="text-[12px] text-ink-3 mt-2 leading-relaxed">{fail.hint}</p>
          <div className="flex items-center justify-center gap-3 mt-6">
            {fail.kind !== 'credit' && (
              <Link href="/deck/new" className="btn btn-primary">다시 시도</Link>
            )}
            <Link href="/dashboard" className={`btn ${fail.kind === 'credit' ? 'btn-primary' : 'btn-outline'}`}>
              ← 대시보드
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const v = deck.verify
  const editing = mode === 'edit'

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-deck-canvas" style={{ wordBreak: 'keep-all' }}>
      <DeckTopBar
        filename={deck.filename ?? '덱'}
        editing={editing}
        verified={v?.verified}
        unverified={v?.unverified}
        onBadgeClick={onBadgeClick}
        factOpen={showFact}
        factInline={!editing}
        onToggleMode={toggleMode}
        onExport={() => setShowExport(true)}
        canUndo={history.canUndo}
        canRedo={history.canRedo}
        onUndo={() => editorRef.current?.undo()}
        onRedo={() => editorRef.current?.redo()}
        saveStatus={autosave.status}
        savedAt={savedAt}
        onRetrySave={() => void autosave.retry()}
      />

      {editWarnings.length > 0 && (
        <div className="mx-auto mt-3 w-full max-w-[460px] rounded-lg border border-risk-medium-border bg-risk-medium-faint p-3 shrink-0">
          {editWarnings.map((w, i) => <p key={i} className="text-[11px] text-risk-medium leading-snug">{w}</p>)}
        </div>
      )}

      <div className="relative flex flex-1 min-h-0">
        {/* ◀ 좌측 네비 (뷰·편집 공통) — 덱 개요 스토리보드. 접기 가능 (3패널: 좌 네비) */}
        {!railCollapsed && (
          <DeckOverviewRail
            jobId={jobId}
            cardCount={deck.cardCount || 7}
            ver={ver}
            index={editing ? page.index : viewIdx}
            onSelect={editing ? (i) => editorRef.current?.setPage(i) : setViewIdx}
            title={deck.filename ?? '덱'}
            labels={cardLabels}
          />
        )}
        {/* 패널 여닫기 — Canva식 경계 라운드 범프 핸들(접힘=›펼치기, 펼침=‹접기) */}
        <button onClick={toggleRail}
          title={railCollapsed ? '덱 개요 펼치기' : '덱 개요 접기'} aria-label={railCollapsed ? '덱 개요 펼치기' : '덱 개요 접기'}
          style={{ left: railCollapsed ? 0 : 300 }}
          className="group absolute top-1/2 -translate-y-1/2 z-30 w-5 hover:w-6 h-16 rounded-r-xl bg-surface border border-l-0 border-deck-line shadow-card grid place-items-center text-ink-3 hover:text-ink transition-all">
          <span className="text-[13px] leading-none" aria-hidden="true">{railCollapsed ? '›' : '‹'}</span>
        </button>

        {/* 중앙 */}
        <main className="flex-1 min-w-0 overflow-hidden">
          {editing ? (
            <div className="relative h-full">
              <DeckEditor
                ref={editorRef}
                className="absolute inset-0"
                html={deck.html as string}
                mode={mode}
                initialPage={viewIdx}
                onScaleChange={(eff, fit) => setZoomInfo((z) => (z.eff === eff && z.fit === fit ? z : { eff, fit }))}
                onSelected={setSelected}
                onDeselected={() => setSelected(null)}
                onDirty={handleDirty}
                onHistory={setHistory}
                onPage={handlePage}
                onLayers={(info) => setLayers(info.items)}
                onHighlighted={(info) => { if (info.value === activeHLRef.current) setJumpFound(info.found > 0) }}
              />
              {(proposing || !!pending) && (
                <div className="absolute inset-0 z-10 cursor-not-allowed" aria-hidden="true"
                  title={proposing ? 'AI가 고치는 중…' : 'AI 제안 확인 중. 적용·취소 후 편집하세요'} />
              )}
              {jump && (
                <DeckFactJumpBar
                  item={jump.item}
                  index={jump.index}
                  total={queue.length}
                  found={jumpFound}
                  onNext={() => jumpTo((jump.index + 1) % queue.length)}
                  onClose={closeJump}
                />
              )}
              {/* 릴 좌우 이동 — 덱은 좌우 슬라이드 카드뉴스. 하단 중앙 페이저(‹ 3/7 ›) */}
              {page.count > 1 && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1 rounded-full border border-deck-line bg-surface/95 shadow-card px-1.5 py-1 backdrop-blur">
                  <button onClick={() => editorRef.current?.setPage(page.index - 1)} disabled={page.index <= 0}
                    aria-label="이전 카드" title="이전 카드 (←)"
                    className="w-7 h-7 rounded-full grid place-items-center text-[16px] text-ink-2 hover:bg-bg-subtle disabled:opacity-25 transition-colors">‹</button>
                  <span className="min-w-[48px] text-center text-[12px] font-semibold tabular-nums text-ink-2">{page.index + 1} / {page.count}</span>
                  <button onClick={() => editorRef.current?.setPage(page.index + 1)} disabled={page.index >= page.count - 1}
                    aria-label="다음 카드" title="다음 카드 (→)"
                    className="w-7 h-7 rounded-full grid place-items-center text-[16px] text-ink-2 hover:bg-bg-subtle disabled:opacity-25 transition-colors">›</button>
                </div>
              )}

              {/* 줌 컨트롤 — 인라인 글자 편집이 작을 때 확대. %는 눌러서 폭 맞춤 */}
              <div className="absolute bottom-4 right-4 z-20 flex items-center gap-0.5 rounded-xl border border-deck-line bg-surface/95 shadow-card px-1 py-1 backdrop-blur">
                <button onClick={() => editorRef.current?.zoomBy(0.8)} title="축소" aria-label="축소"
                  className="w-7 h-7 rounded-lg grid place-items-center text-[15px] text-ink-2 hover:bg-bg-subtle transition-colors">−</button>
                <button onClick={() => editorRef.current?.zoomFit()} title="폭 맞춤"
                  className="min-w-[54px] h-7 px-2 rounded-lg text-[12px] font-semibold tabular-nums text-ink-2 hover:bg-bg-subtle transition-colors">
                  {Math.round(zoomInfo.eff * 100)}%
                </button>
                <button onClick={() => editorRef.current?.zoomBy(1.25)} title="확대" aria-label="확대"
                  className="w-7 h-7 rounded-lg grid place-items-center text-[15px] text-ink-2 hover:bg-bg-subtle transition-colors">+</button>
              </div>
            </div>
          ) : (
            <DeckViewer jobId={jobId} cardCount={deck.cardCount || 7} ver={ver} rendering={rendering}
              onEditCard={enterEditAt} index={viewIdx} onIndex={setViewIdx} />
          )}
        </main>

        {/* ▶ 우측 팩트 패널 (뷰 모드) — 해자를 상시 노출 (3패널: 우 팩트). 블랙박스 벤치 반영 */}
        {!editing && (
          <aside className="w-[380px] shrink-0 border-l border-deck-line bg-surface min-h-0 overflow-y-auto p-5">
            <DeckFactPanel verify={v} canReverify={deck.canReverify !== false} onJump={handleJump} />
          </aside>
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
                  <DeckLayersPanel
                    items={layers}
                    selectedEid={selected?.count && selected.count > 1 ? undefined : selected?.eid}
                    onSelect={(eid) => editorRef.current?.selectEid(eid)}
                    onHover={(eid) => editorRef.current?.hoverEid(eid ?? '')}
                  />
                  <div className="h-px bg-border" />
                  <DeckMediaPanel jobId={jobId} onInsert={(p) => { editorRef.current?.insertImage(p); handleDirty() }} />
                  <div className="h-px bg-border" />
                  <DeckElementPanel
                    selected={selected}
                    onStyle={(prop, value) => editorRef.current?.applyStyle(prop, value)}
                    onDelete={() => editorRef.current?.deleteElement()}
                    onMove={(dir) => editorRef.current?.moveElement(dir)}
                    onRevertFlow={() => editorRef.current?.revertFlow()}
                    onSetBackground={() => editorRef.current?.setImageBackground()}
                    onAlign={(axis) => editorRef.current?.align(axis)}
                    onDistribute={(axis) => editorRef.current?.distribute(axis)}
                    onSetRect={(r) => editorRef.current?.setRect(r)}
                  />
                </div>
              }
            />
          </aside>
        )}

        {/* 팩트체크 드로어 — 편집 모드 온디맨드(뷰는 우측 상시 노출) */}
        {editing && showFact && (
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
                <DeckFactPanel verify={v} canReverify={deck.canReverify !== false} onJump={handleJump} />
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
