'use client'

// AI 도우미 (스펙 §4.2) — 연구원용 주 편집 수단. 요소 선택 → 원클릭/자연어 → AI 제안(미커밋) →
// before/after 확인 → [✓ 적용]/[↻ 다른 안]/[✕]. 적용 후에만 저장·렌더. AI 되돌리기=부모 스냅샷.
// 제안(propose)·적용(commit)은 각각 유료 LLM/렌더이므로 명시적 클릭만(타이핑 자동호출 금지).

import { useState } from 'react'
import type { SelectedInfo } from './DeckEditor'

const TEXT_PRESETS = [
  { label: '한 줄로 짧게', instruction: '이 텍스트를 의미를 유지하며 한 줄로 짧게 줄여줘.' },
  { label: '더 쉬운 말로', instruction: '이 텍스트를 일반 독자가 이해하기 쉬운 말로 바꿔줘. 수치는 원문 근거 안에서만.' },
  { label: '더 크게', instruction: '이 텍스트 요소의 글자 크기를 눈에 띄게 키워줘(비율 유지).' },
]

interface Props {
  selected: SelectedInfo | null
  proposing: boolean          // propose 진행 중(유료)
  pending: boolean            // 미커밋 제안 대기 중
  committing: boolean         // 적용(저장+렌더) 진행 중
  beforeText: string | null
  afterText: string | null
  onPropose: (instruction: string) => void
  onCommit: () => void
  onDiscard: () => void
  canRevert: boolean
  reverting: boolean
  onRevert: () => void
}

export default function DeckAIAssistant({
  selected, proposing, pending, committing, beforeText, afterText,
  onPropose, onCommit, onDiscard, canRevert, reverting, onRevert,
}: Props) {
  const [text, setText] = useState('')
  const [last, setLast] = useState('')

  const busy = proposing || committing || reverting
  const hasTarget = !!selected?.eid

  const propose = (instruction: string) => {
    const t = instruction.trim()
    if (!t || busy) return
    setLast(t)
    onPropose(t)
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-bold text-ink">✦ AI 도우미</span>
        {canRevert && (
          <button
            onClick={onRevert}
            disabled={busy}
            className="ml-auto text-[11px] font-semibold text-ink-2 border border-border rounded-md px-2 py-1 disabled:opacity-40"
          >
            {reverting ? '되돌리는 중…' : '↩ AI 편집 되돌리기'}
          </button>
        )}
      </div>

      {/* 맥락 */}
      <p className="text-[11.5px] text-ink-3 leading-snug">
        {hasTarget
          ? <>선택한 <b className="text-ink-2">{selected?.tag}</b> 요소를 고쳐요: “{(selected?.quotedText || '').slice(0, 40)}{(selected?.quotedText || '').length > 40 ? '…' : ''}”</>
          : '요소를 클릭해 고르면 그 부분만 정확히 고쳐요. 안 고르면 덱 전체에 적용됩니다.'}
      </p>

      {/* 미커밋 제안 미리보기 */}
      {pending ? (
        <div className="rounded-lg border border-forest-green/40 bg-forest-green-wash/40 p-3 flex flex-col gap-2">
          <span className="text-[11px] font-bold text-forest-green-deep">AI 제안 (아직 적용 안 됨)</span>
          {hasTarget && (beforeText !== null || afterText !== null) && (
            <div className="flex flex-col gap-1 text-[11.5px]">
              <span className="text-ink-3 line-through">{beforeText || '(빈 텍스트)'}</span>
              <span className="text-ink font-semibold">→ {afterText || '(빈 텍스트)'}</span>
            </div>
          )}
          {!hasTarget && <span className="text-[11px] text-ink-3">덱 전체에 반영됩니다. 적용하면 카드가 다시 그려져요.</span>}
          <div className="flex gap-2 mt-1">
            <button
              onClick={onCommit}
              disabled={busy}
              className="flex-1 h-8 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40"
            >
              {committing ? '적용 중…' : '✓ 적용'}
            </button>
            <button
              onClick={() => propose(last)}
              disabled={busy || !last}
              title="같은 지시로 다른 제안"
              className="h-8 px-3 rounded-lg border border-border text-ink-2 text-[12px] font-semibold disabled:opacity-40"
            >
              {proposing ? '…' : '↻ 다른 안'}
            </button>
            <button
              onClick={onDiscard}
              disabled={busy}
              aria-label="제안 취소"
              className="h-8 px-3 rounded-lg border border-border text-ink-3 text-[12px] disabled:opacity-40"
            >✕</button>
          </div>
        </div>
      ) : (
        <>
          {/* 원클릭 프리셋(텍스트 선택 시) */}
          {selected?.editable && (
            <div className="flex flex-wrap gap-1.5">
              {TEXT_PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => propose(p.instruction)}
                  disabled={busy}
                  className="text-[11.5px] font-semibold text-forest-green-deep bg-forest-green-wash border border-forest-green/30 rounded-full px-2.5 py-1 disabled:opacity-40"
                >{p.label}</button>
              ))}
            </div>
          )}

          {/* 자유 지시 */}
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={hasTarget ? '예: "이 문장을 질문형으로 바꿔줘"' : '예: "표지 색을 더 차분하게"'}
            rows={2}
            disabled={busy}
            className="w-full rounded-lg border border-border bg-canvas-subtle p-2 text-[12px] text-ink-1 resize-none disabled:opacity-50"
          />
          <button
            onClick={() => { propose(text); setText('') }}
            disabled={busy || !text.trim()}
            className="h-8 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40"
          >
            {proposing ? 'AI가 제안 중…' : 'AI에게 맡기기'}
          </button>
          <p className="text-[10px] text-ink-3 leading-snug">
            AI가 먼저 제안을 보여줘요. 확인하고 <b>적용</b>을 눌러야 반영됩니다. 수치는 원문 근거 안에서만 바뀝니다.
          </p>
        </>
      )}
    </div>
  )
}
