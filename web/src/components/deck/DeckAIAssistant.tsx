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

// 원탭 빠른 수정 — 디자인 편집(색·톤·크기)만. 수치·문구는 건드리지 않아 fidelity 안전.
const QUICK_FIX = [
  { label: '더 밝게', instruction: '전체 톤을 더 밝고 화사하게 조정해줘. 수치와 문구는 그대로 둬.' },
  { label: '더 어둡게', instruction: '전체 톤을 더 어둡고 묵직하게 조정해줘. 수치와 문구는 그대로 둬.' },
  { label: '따뜻한 톤', instruction: '색감을 더 따뜻한 톤(웜)으로 조정해줘. 수치와 문구는 그대로 둬.' },
  { label: '차가운 톤', instruction: '색감을 더 차가운 톤(쿨)으로 조정해줘. 수치와 문구는 그대로 둬.' },
  { label: '폰트 크게', instruction: '가독성을 위해 글자 크기를 키워줘(레이아웃 비율 유지).' },
  { label: '폰트 작게', instruction: '답답하지 않게 글자 크기를 살짝 줄여줘(레이아웃 비율 유지).' },
]

// 빈 상태 예시 프롬프트 — 클릭하면 그대로 지시로 실행.
const SUGGESTIONS = [
  '표지 배경색을 더 차분한 톤으로 바꿔줘',
  '제목을 더 크고 굵게 강조해줘',
  '텍스트에 은은한 그림자를 넣어 가독성을 높여줘',
  '이미지를 왼쪽, 텍스트를 오른쪽으로 배치해줘',
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

      {/* 맥락 — 요소 선택 시에만(미선택 안내는 아래 빈 상태 히어로가 담당) */}
      {hasTarget && !pending && (
        <p className="text-[11.5px] text-ink-3 leading-snug">
          선택한 <b className="text-ink-2">{selected?.tag}</b> 요소를 고쳐요: “{(selected?.quotedText || '').slice(0, 40)}{(selected?.quotedText || '').length > 40 ? '…' : ''}”
        </p>
      )}

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
          {/* 텍스트 선택 시 원클릭 프리셋 */}
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

          {/* 빈 상태 히어로 — 선택·입력 없을 때 무엇을 할 수 있는지 초대 */}
          {!hasTarget && !text.trim() && (
            <div className="flex flex-col items-center text-center gap-2 pt-2 pb-1">
              <span className="w-11 h-11 rounded-full bg-forest-green-wash text-forest-green-deep grid place-items-center text-[19px]" aria-hidden="true">✦</span>
              <p className="text-[14px] font-bold text-ink">무엇을 수정할까요?</p>
              <p className="text-[11.5px] text-ink-3 leading-snug max-w-[250px]">원하는 수정을 자연어로 말해주세요. AI가 제안을 먼저 보여줘요.</p>
            </div>
          )}

          {/* 예시 프롬프트 */}
          {!hasTarget && !text.trim() && (
            <div className="flex flex-col gap-1.5">
              <span className="text-[10.5px] font-semibold text-ink-3 uppercase tracking-wide">이렇게 말해보세요</span>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => propose(s)}
                  disabled={busy}
                  className="text-left text-[11.5px] text-ink-2 border border-deck-line rounded-lg px-2.5 py-2 hover:border-forest-green/50 hover:text-ink disabled:opacity-40 transition-colors"
                >“{s}”</button>
              ))}
            </div>
          )}

          {/* 빠른 수정 — 원탭 디자인 편집(색·톤·크기) */}
          <div className="flex flex-col gap-1.5">
            <span className="text-[10.5px] font-semibold text-ink-3 uppercase tracking-wide">빠른 수정</span>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_FIX.map((q) => (
                <button
                  key={q.label}
                  onClick={() => propose(q.instruction)}
                  disabled={busy}
                  className="text-[11.5px] font-semibold text-ink-2 bg-surface border border-deck-line rounded-full px-2.5 py-1 hover:border-forest-green/50 hover:text-forest-green-deep disabled:opacity-40 transition-colors"
                >{q.label}</button>
              ))}
            </div>
          </div>

          {/* 자유 지시 (Enter 전송 · Shift+Enter 줄바꿈) */}
          <div className="flex flex-col gap-1.5">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); const t = text; setText(''); propose(t) } }}
              placeholder={hasTarget ? '예: "이 문장을 질문형으로 바꿔줘"' : '원하는 수정사항을 입력하세요…'}
              rows={2}
              disabled={busy}
              className="w-full rounded-lg border border-deck-line bg-surface p-2.5 text-[12px] text-ink resize-none disabled:opacity-50 focus:border-forest-green/50 focus:outline-none"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={() => { const t = text; setText(''); propose(t) }}
                disabled={busy || !text.trim()}
                className="flex-1 h-8 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40"
              >
                {proposing ? 'AI가 제안 중…' : '✦ AI에게 맡기기'}
              </button>
              <span className="text-[10px] text-ink-3 shrink-0">Enter 전송</span>
            </div>
          </div>

          <p className="text-[10px] text-ink-3 leading-snug">
            AI가 먼저 제안을 보여줘요. 확인하고 <b>적용</b>을 눌러야 반영됩니다. 수치는 원문 근거 안에서만 바뀝니다.
          </p>
        </>
      )}
    </div>
  )
}
