'use client'

// 팩트 체크 패널 (스펙 §4.5) — "충실성 검증·해자" 폐기. 출처 위치·정합 주장 금지(헌법).
interface VerifyClaim { value: string; context: string; verified: boolean }
interface VerifyData { verified: number; unverified: number; claims: VerifyClaim[] }

interface Props {
  verify: VerifyData | null | undefined
  canReverify: boolean
}

export default function DeckFactPanel({ verify, canReverify }: Props) {
  const flagged = verify?.claims.filter((c) => !c.verified) ?? []
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="text-[14px] font-bold text-ink">팩트 체크</h3>
        <p className="text-[11.5px] text-ink-3 mt-1 leading-snug">
          {canReverify
            ? '원문에 없는 수치는 따로 표시해요. 최종 판단은 직접 하세요.'
            : '이 덱은 원문이 없어 편집 시 재검증되지 않습니다. 재생성하면 복원됩니다.'}
        </p>
      </div>

      <div className="flex gap-2.5">
        <div className="flex-1 rounded-xl border border-border p-3 text-center">
          <div className="text-[20px] font-extrabold text-forest-green">{verify?.verified ?? 0}</div>
          <div className="text-[10.5px] text-ink-3 mt-0.5">원문에서 찾음</div>
        </div>
        <div className="flex-1 rounded-xl border border-border p-3 text-center">
          <div className="text-[20px] font-extrabold text-risk-medium">{verify?.unverified ?? 0}</div>
          <div className="text-[10.5px] text-ink-3 mt-0.5">확인 필요</div>
        </div>
      </div>

      {flagged.length > 0 ? (
        <div className="flex flex-col gap-2">
          <p className="text-[11.5px] font-semibold text-ink-2">⚠️ 원문에 없는 수치 — AI가 더한 맥락/예시인지 확인하세요:</p>
          <ul className="flex flex-col gap-2">
            {flagged.map((c, i) => (
              <li key={i} className="rounded-lg border border-risk-medium-border bg-risk-medium-faint p-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] font-bold text-ink">{c.value}</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-canvas text-risk-medium shrink-0">원문에 없음</span>
                </div>
                <p className="text-[10.5px] text-ink-3 mt-1 leading-snug">…{c.context}…</p>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-[12px] text-ink-3">모든 수치가 원문에서 추적됐습니다.</p>
      )}
    </div>
  )
}
