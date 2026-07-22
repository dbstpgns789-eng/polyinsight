'use client'

// 요금 안내 (/upgrade) — 충전형 크레딧제 4티어 (2026-07-22, BM 확정: 세훈·박사님 합의).
// 진입: 대시보드 미터 CTA·덱 카드 잠금 / deck/new 402(?from=author) / 내보내기 페이월(?from=export).
// ★가격 미확정 — 덱 원가(현재 ~$1)를 먼저 낮춘 뒤 결정한다(루트 CLAUDE.md 무료체험 배관 결정).
// 그래서 유료 금액은 "예시" 칩이고, 충전 CTA는 결제 연동(Creem) 전까지 비활성이다.
// 거짓 숫자를 쓰지 않는다 — 없는 값은 "예시"로 표시하지 지어내지 않는다.
//
// 크레딧제: 1덱 = 1크레딧(유저 대면 고정, 단순). 무거운 작업의 원가 초과분은 초기 적자로 흡수.
// 무게 비례 미터는 유저 불안 때문에 배제(동영상 등 확장 시 재검토). 충전분은 이월(월 리셋 없음)이 구독제 대비 우위.
//
// AuthGuard로 감싸지 않는다: 모든 CTA가 비인증 상태에서도 안전(무료="현재 플랜" 정적,
// 유료=결제 전 비활성, 팀=mailto). 향후 랜딩에서 바로 링크할 수 있도록 공개 라우트로 둔다.

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

const LAB_EMAIL = 'dbstpgns789@hanyang.ac.kr'

type Feat = { t: string; kind?: 'on' | 'off' | 'plus' }
type Tier = {
  name: string
  desc: string
  price: string
  guess: boolean
  credit: string
  creditSub: string
  rollover: string
  rolloverFree?: boolean
  cta: string
  ctaPrimary?: boolean
  ctaDisabled?: boolean
  ctaLabel?: string // 무료 = "현재 플랜"
  featured?: boolean
  feats: Feat[]
}

// 숫자는 예시 — 원가 실측 후 확정 (거짓 확정값 아님)
const TIERS: Tier[] = [
  {
    name: '무료', desc: '우리 실력을 직접 확인하는 체험판',
    price: '0', guess: false,
    credit: '1덱 체험', creditSub: '평생 · 보기·편집 전용',
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
    name: '스타터', desc: '논문 낼 때 몰아 쓰는 개인 연구자',
    price: '10,000', guess: true,
    credit: '10크레딧 = 덱 10개', creditSub: '1덱 = 1크레딧',
    rollover: '안 쓴 크레딧 이월',
    cta: '충전하기', ctaDisabled: true,
    feats: [
      { t: '무료의 모든 것', kind: 'plus' },
      { t: '1080×1350 PNG·ZIP 내보내기' },
      { t: '원문 수치 검증' },
      { t: 'AI 디자이너', kind: 'off' },
    ],
  },
  {
    name: '플러스', desc: '자기 연구를 꾸준히 알리는 연구자',
    price: '30,000', guess: true,
    credit: '30크레딧 = 덱 30개', creditSub: '1덱 = 1크레딧',
    rollover: '안 쓴 크레딧 이월',
    cta: '충전하기', ctaPrimary: true, ctaDisabled: true, featured: true,
    feats: [
      { t: '스타터의 모든 것', kind: 'plus' },
      { t: 'AI 디자이너 (편집 도우미)' },
      { t: '이미지 삽입' },
    ],
  },
  {
    name: '프로', desc: '채널까지 운영하는 헤비 유저',
    price: '50,000', guess: true,
    credit: '50크레딧 = 덱 50개', creditSub: '1덱 = 1크레딧',
    rollover: '안 쓴 크레딧 이월',
    cta: '충전하기', ctaDisabled: true,
    feats: [
      { t: '플러스의 모든 것', kind: 'plus' },
      { t: 'SNS 자동 발행 (추후)' },
    ],
  },
]

const COLS = [
  { name: '무료', price: '' },
  { name: '스타터', price: '₩10,000' },
  { name: '플러스', price: '₩30,000', hl: true },
  { name: '프로', price: '₩50,000' },
]

// vals: 문자열(수치) 또는 boolean(✓/✕)
const ROWS: { label: string; vals: (string | boolean)[] }[] = [
  { label: '덱 생성', vals: ['1개', '10개', '30개', '50개'] },
  { label: '크레딧 이월 (월 리셋 없음)', vals: [false, true, true, true] },
  { label: '원문 수치 검증 (fidelity)', vals: [true, true, true, true] },
  { label: '화면에서 보기·편집', vals: [true, true, true, true] },
  { label: '파일 내보내기 (PNG·ZIP)', vals: [false, true, true, true] },
  { label: 'AI 디자이너 (편집 도우미)', vals: [false, false, true, true] },
  { label: '이미지 삽입', vals: [false, false, true, true] },
  { label: 'SNS 자동 발행 (추후)', vals: [false, false, false, true] },
]

const FAQ: { q: string; a: string; open?: boolean }[] = [
  { q: '크레딧은 어떻게 쓰이나요?', a: '덱(카드뉴스 1편)을 만들 때 1크레딧이 차감돼요. 다시 만들어도 1크레딧이 들어요. 무거운 작업(동영상 등)은 나중에 크레딧을 더 쓰는 방식으로 확장할 수 있어요.', open: true },
  { q: '안 쓴 크레딧은 사라지나요?', a: '아니요. 충전한 크레딧은 이월돼요. 월마다 초기화되는 구독제와 달라요 — 급하게 다 쓸 필요 없어요.' },
  { q: '무료로는 어디까지 되나요?', a: '1덱을 완성해서 화면에서 보고, 편집하고, 원문 수치 검증까지 전부 볼 수 있어요. 파일로 내보내기만 충전 후예요.' },
  { q: 'AI 디자이너는 무엇인가요?', a: '카드를 "이렇게 바꿔줘"라고 말하면 편집안을 만들어주는 도우미예요. 플러스(₩30,000)부터 열려요.' },
  { q: '결제 수단은 무엇인가요?', a: 'Creem(Merchant of Record)을 통해 카드로 결제돼요. 세금·인보이스는 대행 처리돼요. (연동 준비 중)' },
]

function UpgradeInner() {
  const from = useSearchParams().get('from')
  const headline =
    from === 'export'
      ? '내보내려면 업그레이드가 필요해요'
      : from === 'author'
        ? '무료 체험 1덱을 모두 사용했어요'
        : '충전한 만큼, 딱 그만큼'

  return (
    <main className="upgrade">
      <div className="upgrade__wrap">
        <header className="upgrade__head">
          <p className="eyebrow">요금</p>
          <h1>{headline}</h1>
          <p className="upgrade__lede">월 결제 없이 필요할 때 충전해서 씁니다. <strong>안 쓴 크레딧은 사라지지 않아요.</strong></p>
        </header>

        <div className="upgrade__banner">
          <span className="upgrade__banner-ic">i</span>
          <span>
            가격은 <strong>확정 전</strong>이에요 — 아래 숫자는 <strong>예시</strong>입니다. 덱 생성 원가를 먼저 낮춘 뒤 공정하게 정할게요.
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
                  <li
                    key={i}
                    className={
                      f.kind === 'off' ? 'upgrade__feat--off' : f.kind === 'plus' ? 'upgrade__feat--plus' : undefined
                    }
                  >
                    {f.t}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>

        {/* 플랜 비교 */}
        <section className="upgrade__compare">
          <h2 className="upgrade__compare-title">플랜 비교</h2>
          <p className="upgrade__compare-sub">각 플랜에서 열리는 기능을 한눈에</p>
          <div className="upgrade__table-scroll">
            <table className="upgrade__table">
              <thead>
                <tr>
                  <th>기능</th>
                  {COLS.map((c) => (
                    <th key={c.name} className={c.hl ? 'upgrade__th--hl' : undefined}>
                      {c.name}
                      {c.price && <span className="upgrade__th-price">{c.price}</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((r) => (
                  <tr key={r.label}>
                    <td>{r.label}</td>
                    {r.vals.map((v, i) => (
                      <td key={i}>
                        {typeof v === 'string' ? (
                          <span className="upgrade__cell-val">{v}</span>
                        ) : v ? (
                          <span className="upgrade__ck">✓</span>
                        ) : (
                          <span className="upgrade__no">✕</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
