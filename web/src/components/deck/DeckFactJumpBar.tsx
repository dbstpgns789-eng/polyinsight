'use client'

// 팩트 점프 문맥 바 — 편집 캔버스 상단. 확인 필요 항목을 순서대로 훑게 한다.
// (편집 모드에선 팩트 패널이 드로어라 닫힌다 → 무엇을 보고 있었는지 여기서 붙든다)
import type { ReviewItem } from '@/lib/verifyStatus'

interface Props {
  item: ReviewItem
  index: number          // 0-기반
  total: number
  found: boolean | null  // null=아직 응답 전, false=카드 안에서 못 찾음
  onNext: () => void
  onClose: () => void
}

export default function DeckFactJumpBar({ item, index, total, found, onNext, onClose }: Props) {
  const reason = item.reason === 'mismatch' ? '계산이 안 맞아요' : '원문에서 확인 안 됨'
  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 rounded-full border border-risk-medium-border bg-risk-medium-faint px-3.5 py-2 shadow-card backdrop-blur">
      <span className="font-mono text-[12px] font-bold text-ink">{item.value}</span>
      <span className="text-[11.5px] text-risk-medium">{reason}</span>
      {found === false && (
        <span className="text-[11px] text-ink-3">이 카드에서 찾지 못했어요 — 이미 고치셨을 수 있어요</span>
      )}
      <span className="font-mono text-[11px] text-ink-3 tabular-nums">{index + 1}/{total}</span>
      {total > 1 && (
        <button type="button" onClick={onNext}
          className="text-[11.5px] font-semibold text-forest-green-deep hover:underline">다음 항목 →</button>
      )}
      <button type="button" onClick={onClose} aria-label="닫기"
        className="w-6 h-6 rounded-full grid place-items-center text-ink-3 hover:text-ink hover:bg-surface transition-colors">✕</button>
    </div>
  )
}
