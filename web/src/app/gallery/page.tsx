'use client'

// 갤러리 — 실제 산출물 전시. 방문자(연구자·홍보 담당)가 "내 논문도 이렇게 나오겠구나"를
// 확인하는 페이지. 재료: ① paper_* = 파이프라인 산출 3덱(디자이너 마감) ② EPxx = AI 논문
// 20편을 한 시리즈로 운영한 사례. 이미지는 web/public/gallery/<slug>/NN.png 정적 서빙.
import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'

interface Deck {
  slug: string
  n: number          // 카드 장수
  title: string      // 카드뉴스 헤드라인
  sub: string        // 원문(논문) 표시
  venue: string
}

// ── 연구성과 카드뉴스: 논문 PDF → 카드 7장 ──────────────────────────────
const PAPER_DECKS: Deck[] = [
  {
    slug: 'paper_chitosan', n: 7,
    title: '산성도를 읽는 구슬, 비타민C를 아껴 내보내다',
    sub: 'pH 감응 키토산 코팅 셀룰로오스 마이크로비드',
    venue: 'Carbohydrate Polymers · 2026 · 한국생산기술연구원',
  },
  {
    slug: 'paper_cellulose', n: 7,
    title: '막을 통과하면 구슬이 된다',
    sub: '아세트산셀룰로오스 막유화 미세 구슬',
    venue: 'Carbohydrate Polymer Tech. & Applications · 2024 · 한국생산기술연구원',
  },
  {
    slug: 'paper_rag', n: 7,
    title: '외우지 않고, 찾아본 뒤 말한다',
    sub: 'Retrieval-Augmented Generation for Knowledge-Intensive NLP',
    venue: 'NeurIPS 2020 · Facebook AI Research',
  },
]

// ── 시리즈 운영 사례: AI 대표 논문 20편 매거진 ──────────────────────────
const MAGAZINE: Deck[] = [
  { slug: 'EP01_transformer', n: 9, title: 'Transformer', sub: 'Attention Is All You Need', venue: '2017' },
  { slug: 'EP02_gpt3', n: 9, title: 'GPT-3', sub: 'Language Models are Few-Shot Learners', venue: '2020' },
  { slug: 'EP03_scaling_kaplan', n: 9, title: 'Scaling Laws', sub: 'Scaling Laws for Neural LMs', venue: '2020' },
  { slug: 'EP04_chinchilla', n: 9, title: 'Chinchilla', sub: 'Training Compute-Optimal LLMs', venue: '2022' },
  { slug: 'EP05_emergence', n: 9, title: 'Emergent Abilities', sub: 'Emergent Abilities of LLMs', venue: '2022' },
  { slug: 'EP06_instructgpt', n: 9, title: 'InstructGPT', sub: 'Training LMs to Follow Instructions', venue: '2022' },
  { slug: 'EP07_cot', n: 9, title: 'Chain-of-Thought', sub: 'CoT Prompting Elicits Reasoning', venue: '2022' },
  { slug: 'EP08_mmlu', n: 9, title: 'MMLU', sub: 'Measuring Massive Multitask LU', venue: '2020' },
  { slug: 'EP09_rag', n: 9, title: 'RAG', sub: 'Retrieval-Augmented Generation', venue: '2020' },
  { slug: 'EP10_clip', n: 9, title: 'CLIP', sub: 'Learning Transferable Visual Models', venue: '2021' },
  { slug: 'EP11_react', n: 9, title: 'ReAct', sub: 'Synergizing Reasoning and Acting', venue: '2022' },
  { slug: 'EP12_gpt4', n: 9, title: 'GPT-4', sub: 'GPT-4 Technical Report', venue: '2023' },
  { slug: 'EP13_llama1', n: 9, title: 'LLaMA', sub: 'Open and Efficient Foundation LMs', venue: '2023' },
  { slug: 'EP14_llama2', n: 9, title: 'Llama 2', sub: 'Open Foundation and Fine-Tuned Chat', venue: '2023' },
  { slug: 'EP15_mistral7b', n: 9, title: 'Mistral 7B', sub: 'Mistral 7B', venue: '2023' },
  { slug: 'EP16_mixtral', n: 9, title: 'Mixtral', sub: 'Mixtral of Experts', venue: '2024' },
  { slug: 'EP17_llama3', n: 9, title: 'Llama 3', sub: 'The Llama 3 Herd of Models', venue: '2024' },
  { slug: 'EP18_deepseekv2', n: 9, title: 'DeepSeek-V2', sub: 'A Strong, Economical MoE LM', venue: '2024' },
  { slug: 'EP19_verify_step', n: 9, title: "Let's Verify", sub: "Let's Verify Step by Step", venue: '2023' },
  { slug: 'EP20_s1', n: 9, title: 's1', sub: 's1: Simple Test-Time Scaling', venue: '2025' },
]

const cardSrc = (slug: string, i: number) => `/gallery/${slug}/${String(i + 1).padStart(2, '0')}.png`

// ── 덱 라이트박스: 카드 1장씩 좌우 스와이프 ─────────────────────────────
function DeckLightbox({ deck, onClose }: { deck: Deck; onClose: () => void }) {
  const [idx, setIdx] = useState(0)
  const railRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowRight') go(1)
      if (e.key === 'ArrowLeft') go(-1)
    }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const go = (d: number) => {
    const rail = railRef.current
    if (!rail) return
    const w = rail.clientWidth
    rail.scrollTo({ left: Math.max(0, Math.min(deck.n - 1, Math.round(rail.scrollLeft / w) + d)) * w, behavior: 'smooth' })
  }

  const onScroll = useCallback(() => {
    const rail = railRef.current
    if (!rail) return
    setIdx(Math.round(rail.scrollLeft / rail.clientWidth))
  }, [])

  return (
    <div
      role="dialog" aria-modal="true" aria-label={`${deck.title} 카드뉴스 보기`}
      className="fixed inset-0 z-[200] flex flex-col bg-black/90 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* 상단 바: 제목 · 카운터 · 닫기 */}
      <div className="flex items-center gap-3 px-4 sm:px-6 h-14 shrink-0 text-white/90" onClick={(e) => e.stopPropagation()}>
        <p className="min-w-0 flex-1 truncate text-[14px] font-semibold">{deck.title}</p>
        <span className="text-[13px] tabular-nums text-white/60">{idx + 1} / {deck.n}</span>
        <button
          onClick={onClose} aria-label="닫기"
          className="grid h-9 w-9 place-items-center rounded-lg hover:bg-white/10 active:scale-95 transition"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {/* 카드 레일 */}
      <div className="relative min-h-0 flex-1" onClick={(e) => e.stopPropagation()}>
        <div
          ref={railRef} onScroll={onScroll}
          className="flex h-full snap-x snap-mandatory overflow-x-auto overscroll-contain [scrollbar-width:none]"
        >
          {/* 슬라이드는 flex+h-full — grid 암시 트랙(auto)에선 img의 %max-height가 무효라 세로 제약이 안 걸린다 */}
          {Array.from({ length: deck.n }, (_, i) => (
            <div key={i} className="flex h-full w-full shrink-0 snap-center items-center justify-center px-3 pb-4">
              <img
                src={cardSrc(deck.slug, i)}
                alt={`${deck.title} 카드 ${i + 1}`}
                className="h-full w-auto max-w-full rounded-lg object-contain shadow-2xl"
                loading={i < 2 ? 'eager' : 'lazy'}
              />
            </div>
          ))}
        </div>

        {/* 좌우 화살표 */}
        {idx > 0 && (
          <button
            onClick={() => go(-1)} aria-label="이전 카드"
            className="absolute left-3 top-1/2 -translate-y-1/2 grid h-11 w-11 place-items-center rounded-full bg-white/12 text-white hover:bg-white/25 active:scale-95 transition"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m14 6-6 6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        )}
        {idx < deck.n - 1 && (
          <button
            onClick={() => go(1)} aria-label="다음 카드"
            className="absolute right-3 top-1/2 -translate-y-1/2 grid h-11 w-11 place-items-center rounded-full bg-white/12 text-white hover:bg-white/25 active:scale-95 transition"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m10 6 6 6-6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </button>
        )}
      </div>

      {/* 진행 도트 */}
      <div className="flex h-10 shrink-0 items-center justify-center gap-1.5" onClick={(e) => e.stopPropagation()}>
        {Array.from({ length: deck.n }, (_, i) => (
          <span key={i} aria-hidden="true"
            className={`h-1.5 rounded-full transition-all ${i === idx ? 'w-5 bg-white/90' : 'w-1.5 bg-white/30'}`} />
        ))}
      </div>
    </div>
  )
}

export default function GalleryPage() {
  const [open, setOpen] = useState<Deck | null>(null)

  return (
    <>
      <a href="#main-content" className="skip-link">본문으로 건너뛰기</a>

      {/* 헤더 — 랜딩과 동일 크롬 */}
      <header className="nav is-scrolled" role="banner">
        <div className="container nav__inner">
          <a href="/" className="nav__logo" aria-label="PolyInsight 홈">Poly<span>Insight</span></a>
          <nav className="nav__links" aria-label="주요 메뉴">
            <a href="/#how-it-works">작동 방식</a>
            <a href="/#features">주요 기능</a>
            <a href="/gallery" aria-current="page" style={{ color: 'var(--text-1)', fontWeight: 600 }}>갤러리</a>
          </nav>
          <div className="nav__actions">
            <a href="/login" className="btn btn-ghost btn-login">로그인</a>
            <a href="/dashboard" className="btn btn-primary">카드뉴스 만들기</a>
          </div>
        </div>
      </header>

      <main id="main-content">
        {/* ─── 인트로 ─── */}
        <section className="section" style={{ paddingBottom: 'var(--s8)' }}>
          <div className="container">
            <p className="text-[13px] font-bold tracking-[0.12em] text-forest-green">GALLERY</p>
            <h1 className="mt-2 text-[clamp(1.7rem,4vw,2.5rem)] font-extrabold tracking-tight text-ink" style={{ textWrap: 'balance' }}>
              논문이 카드뉴스가 되기까지
            </h1>
            <p className="mt-3 max-w-[52ch] text-[15px] leading-relaxed text-ink-2">
              실제 논문 PDF에서 만들어진 결과물을 그대로 모았습니다.
              카드에 쓰인 수치는 논문 원문과 대조를 거칩니다.
            </p>
            <p className="mt-4 text-[13px] text-ink-3 tabular-nums">카드뉴스 23편 · 카드 201장</p>
          </div>
        </section>

        {/* ─── 연구성과 카드뉴스 (논문 → 카드) ─── */}
        <section className="section section--subtle" aria-labelledby="paper-title" style={{ paddingBlock: 'var(--s12)' }}>
          <div className="container">
            <h2 id="paper-title" className="text-[22px] font-extrabold tracking-tight text-ink">연구성과 카드뉴스</h2>
            <p className="mt-1.5 text-[14px] text-ink-3">논문 PDF 한 편이 카드 한 세트가 됩니다. 좌우로 넘겨 전체를 보세요.</p>

            <div className="mt-8 flex flex-col gap-12">
              {PAPER_DECKS.map((d) => (
                <article key={d.slug} className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)] lg:gap-8">
                  {/* 메타 */}
                  <div className="min-w-0">
                    <p className="text-[12px] font-semibold tracking-wide text-ink-3">원문 논문</p>
                    <h3 className="mt-1 text-[17px] font-bold leading-snug text-ink" style={{ textWrap: 'balance' }}>{d.sub}</h3>
                    <p className="mt-1 text-[13px] leading-relaxed text-ink-3">{d.venue}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-[12px] font-semibold text-ink-2 tabular-nums">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg>
                        카드 {d.n}장
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-[12px] font-semibold text-forest-green-deep">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m4.5 12.5 5 5 10-11" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
                        수치 원문 대조
                      </span>
                    </div>
                    <button
                      onClick={() => setOpen(d)}
                      className="mt-5 inline-flex items-center gap-1.5 text-[13.5px] font-bold text-forest-green hover:underline active:translate-y-px"
                    >
                      크게 보기
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m10 6 6 6-6 6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </button>
                  </div>

                  {/* 카드 스트립 */}
                  <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 [scrollbar-width:thin]">
                    {Array.from({ length: d.n }, (_, i) => (
                      <button
                        key={i} onClick={() => setOpen(d)}
                        className="w-[228px] shrink-0 snap-start overflow-hidden rounded-xl border border-border bg-surface shadow-card transition hover:-translate-y-0.5 hover:shadow-modal active:translate-y-0"
                        aria-label={`${d.title} 카드 ${i + 1} 크게 보기`}
                      >
                        <img
                          src={cardSrc(d.slug, i)} alt={`${d.title} 카드 ${i + 1}`}
                          width={1080} height={1350} loading="lazy"
                          className="block h-auto w-full"
                        />
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ─── 시리즈 운영 사례 ─── */}
        <section className="section section--surface" aria-labelledby="mag-title" style={{ paddingBlock: 'var(--s12)' }}>
          <div className="container">
            <h2 id="mag-title" className="text-[22px] font-extrabold tracking-tight text-ink">시리즈 운영 사례 · AI 테크 매거진</h2>
            <p className="mt-1.5 max-w-[60ch] text-[14px] leading-relaxed text-ink-3">
              AI 대표 논문 20편을 하나의 브랜드 톤으로 만든 연재 사례입니다. 표지를 누르면 9장 전체를 볼 수 있습니다.
            </p>

            <div className="mt-8 grid grid-cols-2 gap-x-4 gap-y-7 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
              {MAGAZINE.map((d, i) => (
                <button
                  key={d.slug} onClick={() => setOpen(d)}
                  className="group text-left"
                  aria-label={`${d.title} 카드뉴스 ${d.n}장 보기`}
                >
                  <span className="block overflow-hidden rounded-xl border border-border shadow-card transition group-hover:-translate-y-1 group-hover:shadow-modal group-active:translate-y-0">
                    <img
                      src={cardSrc(d.slug, 0)} alt={`${d.title} 카드뉴스 표지`}
                      width={1080} height={1350} loading={i < 5 ? 'eager' : 'lazy'}
                      className="block h-auto w-full"
                    />
                  </span>
                  <span className="mt-2.5 flex items-baseline justify-between gap-2">
                    <span className="min-w-0 truncate text-[13.5px] font-bold text-ink">{d.title}</span>
                    <span className="shrink-0 text-[11.5px] text-ink-3 tabular-nums">{d.venue}</span>
                  </span>
                  <span className="block truncate text-[12px] text-ink-3">{d.sub}</span>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* ─── CTA ─── */}
        <section className="section section--dark cta-section" aria-labelledby="gcta-title">
          <div className="container cta__inner">
            <h2 id="gcta-title" className="cta__title">다음 카드뉴스는 당신의 논문입니다.</h2>
            <p className="cta__sub">PDF 하나를 올리면 초안이 나옵니다. 첫 1편은 무료입니다.</p>
            <a href="/dashboard" className="btn btn-white btn-lg">내 논문으로 만들어 보기</a>
          </div>
        </section>
      </main>

      <footer className="footer" role="contentinfo">
        <div className="container footer__inner">
          <p className="footer__logo">PolyInsight</p>
          <div className="footer__links">
            <Link href="/privacy">개인정보 처리방침</Link>
            <Link href="/terms">이용약관</Link>
            <a href="mailto:dbstpgns789@gmail.com">문의하기</a>
          </div>
          <p className="footer__copy">&copy; 2026 PolyInsight. All rights reserved.</p>
        </div>
      </footer>

      {open && <DeckLightbox deck={open} onClose={() => setOpen(null)} />}
    </>
  )
}
