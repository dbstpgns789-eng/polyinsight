'use client'

// 팩트 체크 패널 (스펙 §4.5) — 무채색 워크스페이스(compC). 검증=의미색 초록만.
// 출처 위치·정합 주장 금지(헌법). 수치→추적가능성 원장(claim ledger)으로 해자 표면화.
import { useState } from 'react'

interface VerifyClaim { value: string; context: string; verified: boolean }
interface VerifyData { verified: number; unverified: number; claims: VerifyClaim[] }

interface Props {
  verify: VerifyData | null | undefined
  canReverify: boolean
}

export default function DeckFactPanel({ verify, canReverify }: Props) {
  const [open, setOpen] = useState(true)       // claim ledger 접기/펼치기
  const claims = verify?.claims ?? []
  const flagged = claims.filter((c) => !c.verified)
  const verified = claims.filter((c) => c.verified)
  const shown = [...flagged, ...verified]      // 미확인 먼저 노출
  const allClear = !!verify && verify.unverified === 0

  return (
    <div className="flex flex-col gap-5">
      {/* head */}
      <div>
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-3">Fidelity · 해자</div>
        <div className="flex items-center gap-1.5 mt-1.5">
          <h3 className="text-[16px] font-extrabold text-ink">팩트 체크</h3>
          {allClear && (
            <span className="w-[18px] h-[18px] rounded-full bg-forest-green text-canvas grid place-items-center text-[10px]" aria-hidden="true">✓</span>
          )}
        </div>
        <p className="text-[11.5px] text-ink-3 mt-2 leading-relaxed">
          {canReverify
            ? '원문에 없는 수치는 따로 표시해요. 최종 판단은 직접 하세요.'
            : '이 덱은 원문이 없어 편집 시 재검증되지 않습니다. 재생성하면 복원됩니다.'}
        </p>
      </div>

      {/* stat — 두 개의 큰 판독값(childish 박스 폐기, 한 프레임 내 분할) */}
      <div className="flex items-stretch rounded-xl border border-deck-line-soft overflow-hidden">
        <div className="flex-1 p-3.5">
          <div className="text-[30px] font-extrabold text-ink leading-none tabular-nums">{verify?.verified ?? 0}</div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-ink-2">
            <span className="w-[7px] h-[7px] rounded-full bg-forest-green" aria-hidden="true" />원문에서 추적됨
          </div>
        </div>
        <div className="w-px bg-deck-line-soft" />
        <div className="flex-1 p-3.5">
          <div className={`text-[30px] font-extrabold leading-none tabular-nums ${(verify?.unverified ?? 0) > 0 ? 'text-risk-medium' : 'text-ink-3'}`}>
            {verify?.unverified ?? 0}
          </div>
          <div className="flex items-center gap-1.5 mt-2 text-[11px] text-ink-2">
            <span className={`w-[7px] h-[7px] rounded-full ${(verify?.unverified ?? 0) > 0 ? 'bg-risk-medium' : 'bg-border'}`} aria-hidden="true" />확인 필요
          </div>
        </div>
      </div>

      {/* claim ledger — 헤더 클릭으로 접기/펼치기 */}
      {shown.length > 0 && (
        <div className="flex flex-col">
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="flex items-center justify-between pb-0.5 w-full text-left group"
          >
            <span className="flex items-center gap-1.5">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"
                strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
                className={`text-ink-3 transition-transform ${open ? 'rotate-90' : ''}`}><path d="m9 18 6-6-6-6" /></svg>
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3 group-hover:text-ink-2 transition-colors">Claim Ledger</span>
            </span>
            <span className="font-mono text-[10.5px] text-ink-3 tabular-nums">{shown.length} / {claims.length}</span>
          </button>
          {open && (
          <ul>
            {shown.map((c, i) => (
              <li key={i} className="flex items-center gap-2.5 py-2.5 border-t border-deck-line-soft first:border-t-0">
                <span className="font-mono text-[12.5px] font-bold text-ink shrink-0 max-w-[128px] truncate" title={c.value}>{c.value}</span>
                <span className="flex-1 text-[11px] text-ink-2 leading-snug line-clamp-2">{c.context.trim()}</span>
                {c.verified ? (
                  <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold text-forest-green-deep bg-forest-green-wash border border-forest-green/25 rounded-md px-1.5 py-1">
                    <span className="w-[11px] h-[11px] rounded-full bg-forest-green text-canvas grid place-items-center text-[7px]" aria-hidden="true">✓</span>원문 확인
                  </span>
                ) : (
                  <span className="shrink-0 text-[9.5px] font-bold px-1.5 py-1 rounded-md bg-risk-medium-faint text-risk-medium border border-risk-medium-border">원문에 없음</span>
                )}
              </li>
            ))}
          </ul>
          )}
        </div>
      )}

      {/* foot */}
      <div className="flex items-center gap-2 text-[11.5px] text-ink-2 border-t border-deck-line-soft mt-1 pt-3">
        {allClear ? (
          <>
            <span className="w-[15px] h-[15px] rounded-full bg-forest-green text-canvas grid place-items-center text-[9px] shrink-0" aria-hidden="true">✓</span>
            <span><b className="text-ink font-bold">모든 수치가 원문에서 추적됐습니다.</b> · 검증 완료 {verify?.verified ?? 0}/{claims.length}</span>
          </>
        ) : (
          <span className="text-ink-3 leading-snug">⚠️ 표시된 수치는 AI가 더한 맥락/예시일 수 있어요 — 원문과 대조해 확인하세요.</span>
        )}
      </div>
    </div>
  )
}
