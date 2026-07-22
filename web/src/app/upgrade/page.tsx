'use client'

// 요금 안내 (/upgrade) — 충전형 크레딧제 · B1 크레딧 소모 모델 (2026-07-22).
// BM 확정(세훈·박사님) → 설계 심화: 티어 기능차등(초안)을 폐기하고 B1으로 전환.
//   - 기능 잠금 없음: 충전 팩은 크레딧 양 + 볼륨 보너스만 다르다(기능은 다 열림).
//   - 모든 작업이 크레딧 소모(덱 생성·AI편집·발행). 값 고정 → 미터 불안을 "예측 가능"으로 해소.
//   - 무료 = 1덱 다 체험 → export에서 결제(캔바식 export-gate 그대로). AI 디자이너만 예외
//     (체험 자체가 LLM 원가라 크레딧으로 돌린다 — 백엔드 게이트는 결제 붙일 때 크레딧 로직으로 전환).
//
// ★가격·크레딧 수치 전부 예시 — 편집 실원가 측정 후 확정(거짓 확정값 금지). CTA는 결제(Creem) 전 비활성.
// AuthGuard 없음: 모든 CTA가 비인증에서 안전(무료=정적, 유료=비활성, 팀=mailto). 공개 라우트.

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

const LAB_EMAIL = 'dbstpgns789@hanyang.ac.kr'

type Feat = { t: string; kind?: 'on' | 'off' }
type Tier = {
  name: string
  desc: string
  price: string
  guess: boolean
  credit: string
  creditSub: string
  bonus?: string
  rollover: string
  rolloverFree?: boolean
  cta: string
  ctaPrimary?: boolean
  ctaDisabled?: boolean
  ctaLabel?: string
  featured?: boolean
  feats: Feat[]
}

// 숫자는 예시 — 원가 실측 후 확정
const TIERS: Tier[] = [
  {
    name: '무료', desc: '우리 실력을 직접 확인하는 체험판',
    price: '0', guess: false,
    credit: '1덱 체험', creditSub: '크레딧 없이 · 보기·편집 전용',
    rollover: '충전 없이 바로 시작', rolloverFree: true,
    cta: '', ctaLabel: '현재 플랜', ctaDisabled: true,
    feats: [
      { t: '완성된 카드뉴스' },
      { t: '원문 수치 검증' },
      { t: '화면에서 보기·편집' },
      { t: '파일 내보내기', kind: 'off' },
      { t: '2번째 덱부터', kind: 'off' },
    ],
  },
  {
    name: '1만원 충전', desc: '논문 낼 때 가볍게 시작',
    price: '10,000', guess: true,
    credit: '100 크레딧', creditSub: '덱 약 10개분',
    rollover: '안 쓴 크레딧 이월',
    cta: '충전하기', ctaDisabled: true,
    feats: [
      { t: '모든 기능 사용' },
      { t: 'AI 디자이너 · 이미지 삽입' },
      { t: '파일 내보내기' },
    ],
  },
  {
    name: '3만원 충전', desc: '자기 연구를 꾸준히 알리는 연구자',
    price: '30,000', guess: true,
    credit: '330 크레딧', creditSub: '덱 약 33개분', bonus: '+30 보너스',
    rollover: '안 쓴 크레딧 이월',
    cta: '충전하기', ctaPrimary: true, ctaDisabled: true, featured: true,
    feats: [
      { t: '모든 기능 사용' },
      { t: 'AI 디자이너 · 이미지 삽입' },
      { t: '파일 내보내기' },
    ],
  },
  {
    name: '5만원 충전', desc: '채널까지 운영하는 헤비 유저',
    price: '50,000', guess: true,
    credit: '575 크레딧', creditSub: '덱 약 57개분', bonus: '+75 보너스',
    rollover: '안 쓴 크레딧 이월',
    cta: '충전하기', ctaDisabled: true,
    feats: [
      { t: '모든 기능 사용' },
      { t: 'AI 디자이너 · 이미지 삽입' },
      { t: 'SNS 자동 발행 (추후)' },
    ],
  },
]

const COSTS: { name: string; sub: string; amt: string }[] = [
  { name: '카드뉴스 덱 생성', sub: '논문 1편 → 카드 한 세트', amt: '10' },
  { name: 'AI 디자이너 편집', sub: '"이렇게 바꿔줘" 1회', amt: '2' },
  { name: 'SNS 자동 발행', sub: '덱 1개 발행 (추후)', amt: '1' },
]

const FAQ: { q: string; a: string; open?: boolean }[] = [
  { q: '크레딧은 어떻게 쓰이나요?', a: '작업마다 정해진 크레딧이 차감돼요 — 덱 생성 10, AI 편집 2, 발행 1(예시). 값이 항상 고정이라 "지금 84크레딧 → 덱 만들면 74"처럼 미리 계산돼요. 쓰기 전에 버튼에 크레딧이 표시됩니다.', open: true },
  { q: '안 쓴 크레딧은 사라지나요?', a: '아니요. 충전한 크레딧은 이월돼요. 월마다 초기화되는 구독제와 달라요.' },
  { q: '무료로는 어디까지 되나요?', a: '1덱을 완성해서 화면에서 보고·편집하고 원문 수치 검증까지 전부 볼 수 있어요. 파일로 내보내기만 충전 후예요.' },
  { q: '결제 수단은 무엇인가요?', a: 'Creem(Merchant of Record)을 통해 카드로 결제돼요. 세금·인보이스는 대행 처리돼요. (연동 준비 중)' },
]

function UpgradeInner() {
  const from = useSearchParams().get('from')
  const headline =
    from === 'export'
      ? '내보내려면 충전이 필요해요'
      : from === 'author'
        ? '무료 체험 1덱을 모두 사용했어요'
        : '충전하고, 크레딧으로 쓰세요'

  return (
    <main className="upgrade">
      <div className="upgrade__wrap">
        <header className="upgrade__head">
          <p className="eyebrow">요금</p>
          <h1>{headline}</h1>
          <p className="upgrade__lede">
            덱 생성·편집·발행 모두 <strong>정해진 크레딧</strong>으로 씁니다. 값이 고정이라 미리 계산돼요. <strong>안 쓴 크레딧은 이월</strong>됩니다.
          </p>
        </header>

        <div className="upgrade__banner">
          <span className="upgrade__banner-ic">i</span>
          <span>
            가격·크레딧 수치는 전부 <strong>예시</strong>예요 — 편집 원가를 실측한 뒤 확정합니다.
          </span>
        </div>

        <div className="upgrade__tiers upgrade__tiers--four">
          {TIERS.map((t) => (
            <section key={t.name} className={`upgrade__tier${t.featured ? ' upgrade__tier--featured' : ''}`}>
              {t.featured && <span className="upgrade__ribbon">가장 인기</span>}
              <div className="upgrade__tier-name">{t.name}</div>
              <p className="upgrade__tier-desc">{t.desc}</p>

              <div className="upgrade__price">
                <span className="upgrade__price-won">₩</span>
                <span className="upgrade__price-num">{t.price}</span>
                {t.guess && <span className="upgrade__price-guess">예시</span>}
              </div>

              <div className="upgrade__quota">
                <span className="upgrade__quota-big">{t.credit}</span>
                <span className="upgrade__quota-lab">{t.creditSub}</span>
                {t.bonus && <span className="upgrade__quota-bonus">{t.bonus}</span>}
              </div>

              <div className={`upgrade__rollover${t.rolloverFree ? ' upgrade__rollover--free' : ''}`}>
                {t.rolloverFree ? t.rollover : `↻ ${t.rollover}`}
              </div>

              {t.ctaLabel ? (
                <button className="btn btn-outline upgrade__cta" disabled>{t.ctaLabel}</button>
              ) : (
                <button
                  className={`btn ${t.ctaPrimary ? 'btn-primary' : 'btn-outline'} upgrade__cta`}
                  disabled={t.ctaDisabled}
                >
                  {t.cta}
                </button>
              )}

              <ul className="upgrade__feats">
                {t.feats.map((f, i) => (
                  <li key={i} className={f.kind === 'off' ? 'upgrade__feat--off' : undefined}>
                    {f.t}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        {/* 작업별 크레딧 (고정 단가) */}
        <section className="upgrade__costs">
          <h2 className="upgrade__costs-title">무엇이 크레딧 얼마?</h2>
          <p className="upgrade__costs-sub">값이 고정이라 쓰기 전에 미리 계산됩니다</p>
          {COSTS.map((c) => (
            <div key={c.name} className="upgrade__costrow">
              <div className="upgrade__costrow-name">
                {c.name}
                <span>{c.sub}</span>
              </div>
              <div className="upgrade__costrow-amt">{c.amt} <small>크레딧</small></div>
            </div>
          ))}
          <p className="upgrade__costnote"><strong>안 쓴 크레딧은 이월</strong>돼요 (월 리셋 없음).</p>
        </section>

        {/* FAQ */}
        <section className="upgrade__faq">
          <h2 className="upgrade__faq-title">자주 묻는 질문</h2>
          {FAQ.map((f) => (
            <details key={f.q} open={f.open}>
              <summary>{f.q}</summary>
              <p>{f.a}</p>
            </details>
          ))}
        </section>

        <p className="upgrade__team">
          연구실·팀 단위로 쓰시나요? <a href={`mailto:${LAB_EMAIL}`}>문의하기 →</a>
        </p>

        <p className="upgrade__foot">
          결제는 <span className="upgrade__mono">Creem</span>(Merchant of Record)을 통해 처리될 예정이에요 — 세금·인보이스 대행.
        </p>
      </div>
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
