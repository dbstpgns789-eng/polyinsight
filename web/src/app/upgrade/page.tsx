'use client'

// 요금 (/upgrade) — 1회 이용권 · 프로/맥스 2티어 + 기간 토글(3/6/12 = 선불할인).
// 방향 확정(1회 이용권·기간묶음). 가격은 원가 실측(편당 ~₩1,100~1,650) 기반 베타 —
// 사고(thinking) 원가만 확인하면 최종. 결제(토스, 사업자등록 후)는 준비 중이라 CTA 비활성.
// 주의: 백엔드는 아직 크레딧제로 돌아간다. 이 페이지는 확정된 방향의 미리보기다(결제·이용권 로직은 하류).
import { Suspense, useState } from 'react'
import { useSearchParams } from 'next/navigation'

type Dur = '3' | '6' | '12'

// /월 = 총액 ÷ 개월. 기간 길수록 /월 내려감(선불 할인). 값은 5천·만원 단위.
const PRICING: Record<Dur, { label: string; proT: string; proM: string; maxT: string; maxM: string }> = {
  '3':  { label: '3개월',  proT: '90,000',  proM: '30,000', maxT: '150,000', maxM: '50,000' },
  '6':  { label: '6개월',  proT: '150,000', proM: '25,000', maxT: '270,000', maxM: '45,000' },
  '12': { label: '12개월', proT: '240,000', proM: '20,000', maxT: '480,000', maxM: '40,000' },
}
const DURS: Dur[] = ['3', '6', '12']

function Check({ muted = false }: { muted?: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="mt-px shrink-0">
      <circle cx="12" cy="12" r="12" fill={muted ? '#F0F1EB' : '#EAF3ED'} />
      <path d="m7.4 12.4 3 3 6.2-7" stroke={muted ? '#98A09A' : '#157A5E'} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function UpgradeInner() {
  const from = useSearchParams().get('from')
  const [dur, setDur] = useState<Dur>('6')
  const p = PRICING[dur]
  const headline =
    from === 'export' ? '내보내려면 이용권이 필요해요'
    : from === 'author' ? '무료 체험을 다 쓰셨어요'
    : '요금'

  return (
    <main className="mx-auto max-w-[900px] px-6 pb-24 pt-16">
      <h1 className="text-[clamp(1.7rem,4vw,2.4rem)] font-extrabold tracking-tight text-ink" style={{ textWrap: 'balance' }}>
        {headline}
      </h1>
      <span className="mt-5 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-[12.5px] text-ink-2">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="10" stroke="var(--accent)" strokeWidth="2" />
          <path d="M12 11v6" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" />
          <circle cx="12" cy="7.5" r="1.3" fill="var(--accent)" />
        </svg>
        자동 갱신 없는 1회 이용권 · <b className="font-semibold text-forest-green-deep">베타</b>(출시 시 확정)
      </span>

      {/* 기간 토글 — 카드는 그대로, 가격만 갱신(3·6·12 카드 폭발 방지) */}
      <div className="mt-9 mb-9 flex">
        <div role="group" aria-label="이용 기간" className="inline-flex gap-1 rounded-2xl border border-border bg-bg-subtle p-1.5">
          {DURS.map((d) => (
            <button
              key={d}
              onClick={() => setDur(d)}
              aria-pressed={dur === d}
              className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-[14px] font-bold transition active:translate-y-px ${
                dur === d ? 'bg-surface text-ink shadow-card' : 'text-ink-3 hover:text-ink'
              }`}
            >
              {PRICING[d].label}
              {d === '12' && (
                <span className="rounded-md bg-forest-green/10 px-1.5 py-0.5 text-[11px] font-extrabold text-forest-green-deep">최대 할인</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 티어 카드 */}
      <div className="grid items-start gap-5 sm:grid-cols-2">
        {/* 프로 */}
        <section className="flex flex-col rounded-2xl border border-border bg-surface p-7 shadow-card">
          <div className="text-[20px] font-extrabold text-ink">프로</div>
          <p className="mt-1 min-h-[40px] text-[13.5px] text-ink-2">자기 연구를 꾸준히 알리는 연구자</p>
          <div className="mt-4 flex items-baseline gap-1.5">
            <span className="text-[19px] font-extrabold text-ink">₩</span>
            <span className="text-[35px] font-extrabold tracking-tight text-ink tabular-nums">{p.proT}</span>
          </div>
          <div className="mt-1.5 text-[13.5px] text-ink-2 tabular-nums"><b className="font-extrabold text-ink">{p.proM}</b>원 / 월</div>
          <div className="mt-0.5 text-[12px] text-ink-3">주 2편 · {p.label} 한 번 결제</div>
          <button disabled title="결제 준비 중" className="mt-5 h-[47px] cursor-not-allowed rounded-xl border-[1.5px] border-forest-green bg-surface text-[14.5px] font-extrabold text-forest-green-deep opacity-45">프로로 시작</button>
          <ul className="mt-6 flex flex-col gap-3 text-[14px] text-ink">
            <li className="flex gap-2.5"><Check />카드뉴스 생성 · 내보내기</li>
            <li className="flex gap-2.5"><Check />AI 디자이너</li>
            <li className="flex gap-2.5"><Check />이미지 삽입</li>
          </ul>
        </section>

        {/* 맥스 (featured) */}
        <section className="relative flex flex-col rounded-2xl border-[1.5px] border-forest-green bg-forest-green/[0.04] p-7 shadow-modal">
          <span className="absolute -top-3 left-7 rounded-full bg-forest-green px-3 py-1 text-[11.5px] font-extrabold text-canvas">가장 인기</span>
          <div className="text-[20px] font-extrabold text-ink">맥스</div>
          <p className="mt-1 min-h-[40px] text-[13.5px] text-ink-2">SNS 채널까지 본격적으로 운영하는 분</p>
          <div className="mt-4 flex items-baseline gap-1.5">
            <span className="text-[19px] font-extrabold text-ink">₩</span>
            <span className="text-[35px] font-extrabold tracking-tight text-ink tabular-nums">{p.maxT}</span>
          </div>
          <div className="mt-1.5 text-[13.5px] text-ink-2 tabular-nums"><b className="font-extrabold text-ink">{p.maxM}</b>원 / 월</div>
          <div className="mt-0.5 text-[12px] text-ink-3">주 4편 · {p.label} 한 번 결제</div>
          <button disabled title="결제 준비 중" className="mt-5 h-[47px] cursor-not-allowed rounded-xl bg-forest-green text-[14.5px] font-extrabold text-canvas opacity-50">맥스로 시작</button>
          <ul className="mt-6 flex flex-col gap-3 text-[14px] text-ink">
            <li className="flex gap-2.5"><Check />프로 기능 전부</li>
            <li className="flex gap-2.5"><Check />여러 명이 함께 <span className="ml-1 font-medium text-ink-3">3석</span></li>
            <li className="flex items-center gap-2.5"><Check muted /><span className="text-ink-3">SNS 자동 발행</span><span className="ml-auto rounded-md bg-bg-subtle px-1.5 py-0.5 text-[11px] font-bold text-ink-3">곧</span></li>
          </ul>
        </section>
      </div>

      <p className="mt-9 text-center text-[12.5px] text-ink-3">
        결제는 준비 중이에요. 방향과 가격을 먼저 공개합니다.{' '}
        <a href="/dashboard" className="font-semibold text-forest-green-deep hover:underline">무료로 1편 먼저 만들기 →</a>
      </p>
    </main>
  )
}

export default function UpgradePage() {
  return (
    <Suspense fallback={null}>
      <UpgradeInner />
    </Suspense>
  )
}
