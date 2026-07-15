'use client'

// 자연어 덱 편집 입력 (Phase 3c). 명시적 전송만 — 타이핑 중 자동 호출 금지(비용 작업).
// 전송 = 유료 LLM 1회. 결과(수정 HTML·verify)는 부모가 받아 에디터를 갱신본으로 재마운트.

import { useState } from 'react'

interface Props {
  onSend: (instruction: string) => Promise<void>
  busy: boolean
}

export default function DeckNLBar({ onSend, busy }: Props) {
  const [text, setText] = useState('')

  const submit = async () => {
    const instruction = text.trim()
    if (!instruction || busy) return
    await onSend(instruction)
    setText('')
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-[12px] font-semibold text-ink-2">자연어로 고치기</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder='예: "표지 색을 더 차분하게", "3번 카드 제목을 한 줄로 줄여줘"'
        rows={3}
        disabled={busy}
        className="w-full rounded-lg border border-border bg-canvas-subtle p-2 text-[12px] text-ink-1 resize-none disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={busy || !text.trim()}
        className="h-8 rounded-lg bg-forest-green text-canvas text-[12px] font-semibold disabled:opacity-40"
      >
        {busy ? 'AI가 고치는 중…' : '전송 (AI 수정)'}
      </button>
      <p className="text-[10px] text-ink-3 leading-snug">
        전송하면 AI가 현재 덱을 최소 변경으로 수정한 뒤 충실성을 다시 검증합니다. 수치는 원문 근거 안에서만 바뀝니다.
      </p>
    </div>
  )
}
