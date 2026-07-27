'use client'

// 저작 덱 HTML을 iframe에 마운트하고 부모(React)와 postMessage로 잇는 편집 표면 (Phase 3).
// 직렬화는 iframe 내부 editorAgent가 수행 — 부모는 contentDocument를 만지지 않는다(신뢰 경계).
// sandbox=allow-scripts 만으로 충분(폰트 CDN·contentEditable·postMessage 모두 동작).

import {
  forwardRef, useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState,
} from 'react'
import AGENT_BODY from './editorAgent'

export interface ElementRect { x: number; y: number; w: number; h: number }

export interface SelectedInfo {
  tag: string
  editable: boolean
  absolute: boolean
  styles: {
    color: string; fontSize: string; textAlign: string; fontWeight: string; background: string
    letterSpacing: string; lineHeight: string; textShadow: string   // 텍스트 세밀
    borderRadius: string; objectFit: string; opacity: string   // 이미지 트리트먼트
  }
  text: string
  eid?: string                // 선택 요소 앵커(단일 선택 시). 다중=''
  cardIndex?: number          // 선택 요소가 속한 카드 index(단일). 다중=-1
  quotedText?: string         // 요소 전체 텍스트(AI 앵커용, ≤2000자)
  count?: number              // 선택 요소 수(다중선택). 미존재/1=단일
  rect?: ElementRect | null   // 자연 카드좌표(단일=요소, 다중=집합 바운딩박스)
  mixed?: boolean             // 다중선택에서 W/H 혼합 여부
  canDistribute?: boolean     // count>=3
  isImage?: boolean           // 단일 선택이 <img>
  isBackground?: boolean      // 이미지가 배경으로 깔린 상태(data-bg=1)
}

export interface HistoryState { canUndo: boolean; canRedo: boolean }

export interface PageState { index: number; count: number }

export type LayerKind = 'text' | 'image' | 'graphic' | 'shape'
export interface LayerItem { eid: string; kind: LayerKind; label: string }
export interface LayersInfo { items: LayerItem[]; cardIndex: number }

export type AlignAxis = 'left' | 'hcenter' | 'right' | 'top' | 'vcenter' | 'bottom'

export interface DeckEditorHandle {
  getHtml: () => Promise<string>
  applyStyle: (prop: string, value: string) => void
  deleteElement: () => void
  moveElement: (dir: 'up' | 'down') => void
  clearSelection: () => void
  undo: () => void
  redo: () => void
  revertFlow: () => void
  setImageBackground: () => void
  align: (axis: AlignAxis) => void
  distribute: (axis: 'h' | 'v') => void
  setRect: (r: { left?: number; top?: number; width?: number; height?: number }) => void
  setPage: (index: number) => void
  selectEid: (eid: string) => void       // 레이어 패널 목록 클릭 → eid로 선택(클릭 가림 우회)
  hoverEid: (eid: string) => void         // 레이어 행 hover → 캔버스 아웃라인(로케이트). ''=해제
  highlight: (value: string) => void
  clearHighlight: () => void
  zoomBy: (factor: number) => void       // 중앙 기준 확대/축소
  zoomFit: () => void                    // 폭 맞춤
  insertImage: (p: {
    url: string; assetId?: string; sourceType?: string
    provider?: string; credit?: string; creditUrl?: string
  }) => void
}

interface Props {
  html: string
  mode: 'view' | 'edit'
  onSelected?: (info: SelectedInfo) => void
  onDeselected?: () => void
  onDirty?: () => void
  onHistory?: (state: HistoryState) => void
  onPage?: (state: PageState) => void
  onLayers?: (info: LayersInfo) => void
  onHighlighted?: (info: { value: string; found: number }) => void
  onScaleChange?: (effective: number, fit: number) => void
  className?: string                                    // 스크롤 뷰포트 배치(예: absolute inset-0)
  initialPage?: number                                  // 편집 진입 시 열 카드(뷰어서 보던 카드). EDITOR_READY 후 반영
}

const CARD_W = 1080

function buildSrcDoc(html: string): string {
  const tag = `<script data-pi-agent="1">${AGENT_BODY}</script>`
  return html.includes('</body>') ? html.replace('</body>', tag + '</body>') : html + tag
}

const DeckEditor = forwardRef<DeckEditorHandle, Props>(function DeckEditor(
  { html, mode, onSelected, onDeselected, onDirty, onHistory, onPage, onLayers, onHighlighted, onScaleChange, className, initialPage }, ref,
) {
  const frameRef = useRef<HTMLIFrameElement>(null)
  // ★srcDoc은 마운트 시 html로 고정한다. 이후 html prop 변경(자동저장이 deck.html을 갱신)에
  // iframe이 재로드되면 EDITOR_READY가 다시 돌며 진입 카드로 점프한다(편집 중 3초마다 점핑 버그).
  // 편집기는 마운트 후 자기 DOM이 진짜 소스 — 의도적 재로드(AI편집·되돌리기)는 부모가 key로 새 마운트.
  const initialHtmlRef = useRef(html)
  const wrapRef = useRef<HTMLDivElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  const [fitScale, setFitScale] = useState(1)
  const [zoom, setZoom] = useState<number | null>(null)  // null = 폭 맞춤(fit), 숫자 = 절대 배율
  const [contentH, setContentH] = useState(1350)
  const htmlResolvers = useRef<((html: string) => void)[]>([])
  const effScale = zoom ?? fitScale       // zoom 지정 시 절대 배율, 아니면 폭 맞춤
  const viewRef = useRef({ effScale: 1, fitScale: 1, zoom: null as number | null })
  viewRef.current = { effScale, fitScale, zoom }   // 최신 배율을 ref로(VIEWPORT 핸들러가 stale 없이 읽음)

  // 확대/축소 앵커 — 지정 뷰포트 점을 고정한 채 배율 변경(중앙 or 커서). 배율 변경 뒤 스크롤 보정.
  const anchorRef = useRef<{ vx: number; vy: number; rx: number; ry: number } | null>(null)
  const zoomAt = useCallback((next: number | null, vx: number, vy: number) => {
    const box = boxRef.current
    if (box) {
      const br = box.getBoundingClientRect()
      anchorRef.current = {
        vx, vy,
        rx: br.width ? (vx - br.left) / br.width : 0.5,
        ry: br.height ? (vy - br.top) / br.height : 0.5,
      }
    }
    setZoom(next == null ? null : Math.min(3, Math.max(0.2, +next.toFixed(3))))
  }, [])
  const zoomByCenter = useCallback((factor: number) => {
    const wrap = wrapRef.current; if (!wrap) return
    const wr = wrap.getBoundingClientRect()
    zoomAt((zoom ?? fitScale) * factor, wr.left + wr.width / 2, wr.top + wr.height / 2)
  }, [zoom, fitScale, zoomAt])

  const send = useCallback((type: string, payload?: Record<string, unknown>) => {
    frameRef.current?.contentWindow?.postMessage({ source: 'pi-host', type, ...payload }, '*')
  }, [])

  // 부모 → iframe 명령 핸들
  useImperativeHandle(ref, () => ({
    getHtml: () =>
      new Promise<string>((resolve) => {
        htmlResolvers.current.push(resolve)
        send('GET_HTML')
      }),
    applyStyle: (prop, value) => send('APPLY_STYLE', { prop, value }),
    deleteElement: () => send('DELETE_ELEMENT'),
    moveElement: (dir) => send('MOVE_ELEMENT', { dir }),
    clearSelection: () => send('CLEAR_SELECTION'),
    undo: () => send('UNDO'),
    redo: () => send('REDO'),
    revertFlow: () => send('REVERT_FLOW'),
    setImageBackground: () => send('SET_IMAGE_BG'),
    align: (axis) => send('ALIGN', { axis }),
    distribute: (axis) => send('DISTRIBUTE', { axis }),
    setRect: (r) => send('SET_RECT', r),
    setPage: (index) => send('SET_PAGE', { index }),
    selectEid: (eid) => send('SELECT_EID', { eid }),
    hoverEid: (eid) => send('HOVER_EID', { eid }),
    highlight: (value) => send('HIGHLIGHT', { value }),
    clearHighlight: () => send('CLEAR_HIGHLIGHT'),
    zoomBy: (factor) => zoomByCenter(factor),
    zoomFit: () => setZoom(null),
    insertImage: (p) => send('INSERT_IMAGE', p),
  }), [send, zoomByCenter])

  // iframe → 부모 메시지
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      const d = e.data || {}
      if (d.source !== 'pi-deck') return
      switch (d.type) {
        case 'EDITOR_READY':
          send('SET_MODE', { mode })
          if (mode === 'edit' && initialPage) send('SET_PAGE', { index: initialPage })  // 보던 카드로
          break
        case 'HEIGHT': if (typeof d.height === 'number' && d.height > 0) setContentH(d.height); break
        case 'SELECTED': onSelected?.(d as unknown as SelectedInfo); break
        case 'DESELECTED': onDeselected?.(); break
        case 'DIRTY': onDirty?.(); break
        case 'HISTORY_STATE': onHistory?.({ canUndo: !!d.canUndo, canRedo: !!d.canRedo }); break
        case 'PAGE': onPage?.({ index: Number(d.index) || 0, count: Number(d.count) || 0 }); break
        case 'LAYERS': onLayers?.({ items: (d.items as LayerItem[]) || [], cardIndex: Number(d.cardIndex) || 0 }); break
        case 'HIGHLIGHTED': onHighlighted?.({ value: String(d.value), found: Number(d.found) || 0 }); break
        case 'VIEWPORT': {
          const wrap = wrapRef.current; if (!wrap) break
          const v = viewRef.current
          if (d.kind === 'pan') {
            const mult = d.drag ? v.effScale : 1        // 드래그 델타=iframe자연px(×배율), 휠 델타=화면px
            wrap.scrollLeft += (Number(d.dx) || 0) * mult
            wrap.scrollTop += (Number(d.dy) || 0) * mult
          } else if (d.kind === 'zoom') {
            const fr = frameRef.current?.getBoundingClientRect()
            if (fr) {
              const vx = fr.left + (Number(d.cx) || 0) * v.effScale   // iframe자연 좌표 → 화면 좌표
              const vy = fr.top + (Number(d.cy) || 0) * v.effScale
              zoomAt((v.zoom ?? v.fitScale) * Math.exp(-(Number(d.delta) || 0) * 0.0015), vx, vy)
            }
          }
          break
        }
        case 'HTML': {
          const r = htmlResolvers.current.shift()
          r?.(d.html as string)
          break
        }
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [mode, send, onSelected, onDeselected, onDirty, onHistory, onPage, onLayers, onHighlighted, initialPage, zoomAt])

  // 모드 변경을 iframe에 반영
  useEffect(() => { send('SET_MODE', { mode }) }, [mode, send])

  // 뷰포트 폭에 맞춘 fit 배율(패딩 48 제외). 1080 초과 확대는 zoom prop이 담당.
  useLayoutEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const measure = () => setFitScale(Math.min(1, Math.max(0.1, (el.clientWidth - 48) / CARD_W)))
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // 배율 변경 뒤: 앵커 점이 뷰포트에서 같은 자리에 오도록 스크롤 보정(중앙/커서 고정 확대)
  useLayoutEffect(() => {
    const a = anchorRef.current; anchorRef.current = null
    const wrap = wrapRef.current, box = boxRef.current
    if (!a || !wrap || !box) return
    const br = box.getBoundingClientRect()
    wrap.scrollLeft += (br.left + a.rx * br.width) - a.vx
    wrap.scrollTop += (br.top + a.ry * br.height) - a.vy
  }, [effScale])

  // 현재 배율을 부모(줌 컨트롤 % 표시)에 보고. onScaleChange를 ref로 담아 effect 의존성에서 제외 —
  // 인라인 콜백이 매 렌더 새 참조여도 effect가 [effScale, fitScale]에서만 돌게(무한 렌더 루프 방지).
  const onScaleChangeRef = useRef(onScaleChange)
  useEffect(() => { onScaleChangeRef.current = onScaleChange })
  useEffect(() => { onScaleChangeRef.current?.(effScale, fitScale) }, [effScale, fitScale])

  return (
    // wrapRef = 스크롤 뷰포트. 카드가 뷰포트보다 작으면 grid로 중앙정렬, 크면(확대) 스크롤.
    <div ref={wrapRef} className={`overflow-auto ${className ?? 'w-full'}`}>
      <div className="min-w-full min-h-full grid place-items-center p-6">
        <div ref={boxRef} className="flex-none" style={{ width: CARD_W * effScale, height: contentH * effScale }}>
          <iframe
            ref={frameRef}
            title="deck-editor"
            srcDoc={buildSrcDoc(initialHtmlRef.current)}
            sandbox="allow-scripts"
            style={{
              width: CARD_W,
              height: contentH,
              border: 'none',
              transformOrigin: 'top left',
              transform: `scale(${effScale})`,
            }}
          />
        </div>
      </div>
    </div>
  )
})

export default DeckEditor
