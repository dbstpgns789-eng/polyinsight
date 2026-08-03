'use client'

// 갤러리 — 순수 커버 전시. 섹션·설명·수치대조 배지 없이 표지만 그리드로 깔고,
// 누르면 라이트박스로 덱 전체를 넘겨본다. 이미지는 web/public/gallery/<slug>/NN.png 정적.
import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'

interface Deck {
  slug: string
  n: number      // 카드 장수
  title: string  // 라이트박스 제목(그리드엔 라벨 없음 — 표지가 스스로 말한다)
}

// 표지가 곧 라벨이라 그리드엔 텍스트를 얹지 않는다. 순수 갤러리.
// 순서: 2026 화제작(분야 다양) 먼저 = 후킹 → AI 클래식 → KITECH 연구성과.
const DECKS: Deck[] = [
  // 2026 화제작 · 분야별
  { slug: 'timecrystal', n: 10, title: '시간에 줄무늬를 새겼다' },
  { slug: 'abot', n: 10, title: '키 하나 누르면, 없던 세계가 그 자리에서 그려진다' },
  { slug: 'crispr', n: 10, title: 'RNA 한 줄로 DNA를 원하는 자리에서 자른다' },
  { slug: 'obesity', n: 10, title: '뱃살이 뇌로 기름을 보내고 있었다' },
  { slug: 'comath', n: 10, title: 'AI가 내놓은 증명은 틀렸다, 그게 결정적이었다' },
  { slug: 'alphafold', n: 10, title: '단백질이 어떻게 접힐지, AI가 맞혔다' },
  // AI 클래식
  { slug: 'gpt3', n: 7, title: "'다음 단어'만 맞히게 했더니, AI가 스스로 배우기 시작했다" },
  { slug: 'clip', n: 8, title: '이름만 알려주면, 처음 보는 것도 알아본다' },
  { slug: 'cot', n: 7, title: "AI에게 답 대신 '풀이 과정'을 쓰게 하자, 추론이 깨어났다" },
  { slug: 'mmlu', n: 7, title: 'AI에게 57과목 시험을 보게 했다' },
  { slug: 'rag', n: 7, title: '외우지 말고, 찾아보게 했다' },
  { slug: 'react', n: 7, title: '말만 하던 AI가, 스스로 움직이기 시작했다' },
  // KITECH 연구성과 (박사님 논문)
  { slug: 'paper_chitosan', n: 7, title: '산성도를 읽는 구슬, 비타민C를 아껴 내보내다' },
  { slug: 'paper_cellulose', n: 7, title: '막을 통과하면 구슬이 된다' },
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
        <section className="section" style={{ paddingBottom: 'var(--s10)' }}>
          <div className="container">
            <p className="text-[13px] font-bold tracking-[0.14em] text-forest-green">GALLERY</p>
            <h1 className="mt-2 text-[clamp(1.8rem,4.4vw,2.7rem)] font-extrabold tracking-tight text-ink" style={{ textWrap: 'balance' }}>
              논문이 카드뉴스가 되기까지
            </h1>
          </div>
        </section>

        {/* ─── 커버 그리드 ─── */}
        <section className="section section--subtle" aria-label="카드뉴스 모음" style={{ paddingTop: 'var(--s8)', paddingBottom: 'var(--s14)' }}>
          <div className="container">
            <div className="grid grid-cols-2 gap-4 sm:gap-5 md:grid-cols-3">
              {DECKS.map((d, i) => (
                <button
                  key={d.slug} onClick={() => setOpen(d)}
                  className="group relative block overflow-hidden rounded-2xl border border-border bg-surface shadow-card transition hover:-translate-y-1 hover:shadow-modal active:translate-y-0"
                  aria-label={`${d.title} 카드뉴스 ${d.n}장 보기`}
                >
                  <img
                    src={cardSrc(d.slug, 0)} alt={`${d.title} 표지`}
                    width={1080} height={1350} loading={i < 4 ? 'eager' : 'lazy'}
                    className="block h-auto w-full"
                  />
                  {/* 호버 시에만 뜨는 딤 + 장수 — 평상시엔 순수 표지 */}
                  <span aria-hidden="true" className="pointer-events-none absolute inset-0 bg-black/0 transition-colors group-hover:bg-black/15" />
                  <span aria-hidden="true"
                    className="pointer-events-none absolute bottom-2.5 right-2.5 rounded-md bg-black/55 px-2 py-0.5 text-[11px] font-semibold tabular-nums text-white/95 opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100">
                    {d.n}장
                  </span>
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
