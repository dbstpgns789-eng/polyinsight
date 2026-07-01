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
  styles: { color: string; fontSize: string; textAlign: string; fontWeight: string; background: string }
  text: string
  count?: number              // 선택 요소 수(다중선택). 미존재/1=단일
  rect?: ElementRect | null   // 자연 카드좌표(단일=요소, 다중=집합 바운딩박스)
  mixed?: boolean             // 다중선택에서 W/H 혼합 여부
  canDistribute?: boolean     // count>=3
}

export interface HistoryState { canUndo: boolean; canRedo: boolean }

export interface PageState { index: number; count: number }

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
  align: (axis: AlignAxis) => void
  distribute: (axis: 'h' | 'v') => void
  setRect: (r: { left?: number; top?: number; width?: number; height?: number }) => void
  setPage: (index: number) => void
}

interface Props {
  html: string
  mode: 'view' | 'edit'
  onSelected?: (info: SelectedInfo) => void
  onDeselected?: () => void
  onDirty?: () => void
  onHistory?: (state: HistoryState) => void
  onPage?: (state: PageState) => void
}

const CARD_W = 1080

function buildSrcDoc(html: string): string {
  const tag = `<script data-pi-agent="1">${AGENT_BODY}</script>`
  return html.includes('</body>') ? html.replace('</body>', tag + '</body>') : html + tag
}

const DeckEditor = forwardRef<DeckEditorHandle, Props>(function DeckEditor(
  { html, mode, onSelected, onDeselected, onDirty, onHistory, onPage }, ref,
) {
  const frameRef = useRef<HTMLIFrameElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const [contentH, setContentH] = useState(1350)
  const htmlResolvers = useRef<((html: string) => void)[]>([])

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
    align: (axis) => send('ALIGN', { axis }),
    distribute: (axis) => send('DISTRIBUTE', { axis }),
    setRect: (r) => send('SET_RECT', r),
    setPage: (index) => send('SET_PAGE', { index }),
  }), [send])

  // iframe → 부모 메시지
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      const d = e.data || {}
      if (d.source !== 'pi-deck') return
      switch (d.type) {
        case 'EDITOR_READY': send('SET_MODE', { mode }); break
        case 'HEIGHT': if (typeof d.height === 'number' && d.height > 0) setContentH(d.height); break
        case 'SELECTED': onSelected?.(d as unknown as SelectedInfo); break
        case 'DESELECTED': onDeselected?.(); break
        case 'DIRTY': onDirty?.(); break
        case 'HISTORY_STATE': onHistory?.({ canUndo: !!d.canUndo, canRedo: !!d.canRedo }); break
        case 'PAGE': onPage?.({ index: Number(d.index) || 0, count: Number(d.count) || 0 }); break
        case 'HTML': {
          const r = htmlResolvers.current.shift()
          r?.(d.html as string)
          break
        }
      }
    }
    window.addEventListener('message', onMsg)
    return () => window.removeEventListener('message', onMsg)
  }, [mode, send, onSelected, onDeselected, onDirty, onHistory, onPage])

  // 모드 변경을 iframe에 반영
  useEffect(() => { send('SET_MODE', { mode }) }, [mode, send])

  // 컨테이너 폭에 맞춰 스케일(1080 → 폭)
  useLayoutEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const measure = () => setScale(Math.min(1, el.clientWidth / CARD_W))
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return (
    <div ref={wrapRef} className="w-full" style={{ height: contentH * scale }}>
      <iframe
        ref={frameRef}
        title="deck-editor"
        srcDoc={buildSrcDoc(html)}
        sandbox="allow-scripts"
        style={{
          width: CARD_W,
          height: contentH,
          border: 'none',
          transformOrigin: 'top left',
          transform: `scale(${scale})`,
        }}
      />
    </div>
  )
})

export default DeckEditor
