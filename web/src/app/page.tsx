'use client';

import { useState, useEffect } from 'react';

export default function Home() {
  const [navScrolled, setNavScrolled] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setNavScrolled(window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const els = Array.from(document.querySelectorAll<Element>('.reveal'));
    if (!els.length) return;

    if (!('IntersectionObserver' in window)) {
      els.forEach(el => el.classList.add('is-visible'));
      return;
    }

    // Pre-check which elements are already in viewport (before adding opacity:0)
    const vpH = window.innerHeight;
    const alreadyVisible = new Set(
      els.filter(el => el.getBoundingClientRect().top < vpH - 40)
    );

    // Add has-reveal + is-visible atomically so in-viewport elements never flash invisible
    requestAnimationFrame(() => {
      document.documentElement.classList.add('has-reveal');
      alreadyVisible.forEach(el => el.classList.add('is-visible'));

      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              entry.target.classList.add('is-visible');
              io.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
      );
      els.forEach(el => { if (!alreadyVisible.has(el)) io.observe(el); });
    });
  }, []);

  return (
    <>
      <a href="#main-content" className="skip-link">본문으로 건너뛰기</a>

      {/* Navigation */}
      <header className={`nav${navScrolled ? ' is-scrolled' : ''}`} role="banner">
        <div className="container nav__inner">
          <a href="/" className="nav__logo" aria-label="PolyInsight 홈">
            Poly<span>Insight</span>
          </a>

          <nav className="nav__links" aria-label="주요 메뉴">
            <a href="#how-it-works">작동 방식</a>
            <a href="#features">주요 기능</a>
          </nav>

          <div className="nav__actions">
            <a href="/login" className="btn btn-ghost btn-login">로그인</a>
            <a href="/dashboard" className="btn btn-primary">바로 테스트</a>
          </div>

          <button
            className="nav__toggle"
            aria-label={mobileNavOpen ? '메뉴 닫기' : '메뉴 열기'}
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-nav"
            onClick={() => setMobileNavOpen(v => !v)}
          >
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <line x1="3" y1="6"  x2="19" y2="6"  stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
              <line x1="3" y1="11" x2="19" y2="11" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
              <line x1="3" y1="16" x2="13" y2="16" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <div
          className={`nav__mobile${mobileNavOpen ? ' is-open' : ''}`}
          id="mobile-nav"
          aria-hidden={!mobileNavOpen}
        >
          <nav aria-label="모바일 메뉴">
            <a href="#how-it-works" onClick={() => setMobileNavOpen(false)}>작동 방식</a>
            <a href="#features" onClick={() => setMobileNavOpen(false)}>주요 기능</a>
            <a href="/login" className="mobile-login">로그인</a>
          </nav>
          <a
            href="/signup"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            무료로 시작하기
          </a>
        </div>
      </header>

      <main id="main-content">

        {/* ─── Hero ─── */}
        <section className="hero" aria-labelledby="hero-title">
          <div className="container hero__grid">

            <div className="hero__content">
              <p className="eyebrow">무료 베타 운영 중</p>
              <h1 id="hero-title" className="hero__title">
                논문 PDF 하나로,<br />카드뉴스 완성
              </h1>
              <p className="hero__sub">
                학술 논문을 업로드하면 AI가 원문에서 핵심 내용을 직접 추출해 카드뉴스를 만듭니다.
                수치와 근거는 논문 그대로, 편집 가능한 형태로 제공됩니다.
              </p>
              <div className="hero__actions">
                <a href="/dashboard" className="btn btn-primary btn-lg">
                  무료로 시작하기
                </a>
              </div>
            </div>

            <div className="hero__visual" aria-hidden="true">
              <div className="card-stack">
                <div className="card-mock card-mock--3">
                  <div className="card-mock__header"><span>서론</span><span>1 / 8</span></div>
                </div>
                <div className="card-mock card-mock--2">
                  <div className="card-mock__header"><span>연구 방법</span><span>3 / 8</span></div>
                  <div className="card-mock__body">
                    <div className="mock-line mock-line--title"></div>
                    <div className="mock-line"></div>
                    <div className="mock-line mock-line--short"></div>
                  </div>
                </div>
                <div className="card-mock card-mock--1">
                  <div className="card-mock__header"><span>연구 결과</span><span>4 / 8</span></div>
                  <div className="card-mock__body">
                    <p className="card-mock__stat">73.2%</p>
                    <p className="card-mock__claim">전체 샘플에서 통계적 유의성 확인</p>
                    <div className="card-mock__cite">
                      <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                        <rect x="1" y="1" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.1"/>
                        <line x1="3" y1="4" x2="8" y2="4" stroke="currentColor" strokeWidth="0.9" strokeLinecap="round"/>
                        <line x1="3" y1="6" x2="6.5" y2="6" stroke="currentColor" strokeWidth="0.9" strokeLinecap="round"/>
                      </svg>
                      Table 2, p.8
                    </div>
                  </div>
                </div>
              </div>

              <div className="visual-label visual-label--input">
                <svg width="28" height="36" viewBox="0 0 28 36" fill="none" aria-hidden="true">
                  <rect x="1" y="1" width="26" height="34" rx="3" fill="white" stroke="var(--border)" strokeWidth="1.5"/>
                  <rect x="5" y="8" width="12" height="2" rx="1" fill="var(--border)"/>
                  <rect x="5" y="13" width="18" height="1.5" rx="0.75" fill="var(--border-subtle)"/>
                  <rect x="5" y="17" width="15" height="1.5" rx="0.75" fill="var(--border-subtle)"/>
                  <rect x="5" y="21" width="17" height="1.5" rx="0.75" fill="var(--border-subtle)"/>
                  <path d="M19 1v8h8" fill="none" stroke="var(--border)" strokeWidth="1.5"/>
                </svg>
                <span>논문 PDF</span>
              </div>

              <div className="visual-arrow" aria-hidden="true">
                <svg width="36" height="16" viewBox="0 0 36 16" fill="none">
                  <path d="M2 8h28M24 3l6 5-6 5" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>

              <div className="visual-label visual-label--output">
                <span>카드뉴스 8장</span>
              </div>
            </div>

          </div>
        </section>

        {/* ─── How It Works ─── */}
        <section className="section section--subtle" id="how-it-works" aria-labelledby="hiw-title">
          <div className="container">
            <h2 id="hiw-title" className="section__title reveal">세 단계면 충분합니다</h2>
            <ol className="steps">
              <li className="step reveal reveal-delay-1">
                <div className="step__num" aria-hidden="true">1</div>
                <div className="step__content">
                  <h3 className="step__title">논문 업로드</h3>
                  <p className="step__desc">연구 논문 PDF를 올리고 카드 장 수를 선택하세요. 별도 입력 없이 원문만으로 진행됩니다.</p>
                </div>
              </li>
              <li className="step reveal reveal-delay-2">
                <div className="step__num" aria-hidden="true">2</div>
                <div className="step__content">
                  <h3 className="step__title">AI 자동 분석</h3>
                  <p className="step__desc">AI가 논문의 연구 목적, 방법론, 핵심 수치, 결론을 원문에서 직접 추출합니다. 수치가 포함된 모든 항목에는 출처(섹션명, 페이지)가 자동으로 표기됩니다.</p>
                </div>
              </li>
              <li className="step reveal reveal-delay-3">
                <div className="step__num" aria-hidden="true">3</div>
                <div className="step__content">
                  <h3 className="step__title">편집 후 내보내기</h3>
                  <p className="step__desc">카드 에디터에서 문구와 이미지를 수정하세요. 완료하면 1080×1080 PNG 파일을 한 번에 내보냅니다.</p>
                </div>
              </li>
            </ol>
          </div>
        </section>

        {/* ─── Features ─── */}
        <section className="section section--surface" id="features" aria-labelledby="feat-title">
          <div className="container">
            <h2 id="feat-title" className="section__title reveal">연구 내용을 그대로 전달합니다</h2>
            <div className="features__grid">
              <article className="feature feature--wide reveal">
                <div className="feature__num" aria-hidden="true">01</div>
                <div>
                  <h3 className="feature__title">원문 기반 추출</h3>
                  <p className="feature__desc">모든 수치와 주장은 논문 원문에서만 가져옵니다. AI가 내용을 임의로 추가하거나 바꾸지 않습니다.</p>
                </div>
              </article>
              <article className="feature reveal reveal-delay-1">
                <div className="feature__num" aria-hidden="true">02</div>
                <div>
                  <h3 className="feature__title">신뢰도 표시</h3>
                  <p className="feature__desc">추출된 각 항목에 신뢰도(높음·보통·낮음)와 검토 필요 여부가 표시됩니다. 검토가 필요한 항목이 남아있으면 내보내기 버튼이 잠깁니다.</p>
                </div>
              </article>
              <article className="feature reveal reveal-delay-2">
                <div className="feature__num" aria-hidden="true">03</div>
                <div>
                  <h3 className="feature__title">가변 카드 구조</h3>
                  <p className="feature__desc">논문 분량과 내용에 따라 3장에서 15장까지 자유롭게 구성합니다. 표지, 문제 제기, 연구 방법, 결과, 마무리 등 12가지 슬라이드 유형을 지원합니다.</p>
                </div>
              </article>
              <article className="feature reveal reveal-delay-1">
                <div className="feature__num" aria-hidden="true">04</div>
                <div>
                  <h3 className="feature__title">카드 에디터</h3>
                  <p className="feature__desc">생성된 카드를 브라우저에서 바로 수정할 수 있습니다. 5초 자동저장으로 작업 내용이 유지됩니다.</p>
                </div>
              </article>
              <article className="feature reveal reveal-delay-2">
                <div className="feature__num" aria-hidden="true">05</div>
                <div>
                  <h3 className="feature__title">고해상도 내보내기</h3>
                  <p className="feature__desc">편집 완료 후 1080×1080 PNG를 ZIP으로 일괄 다운로드합니다.</p>
                </div>
              </article>
            </div>
          </div>
        </section>

        {/* ─── Target Users ─── */}
        <section className="section" aria-labelledby="users-title">
          <div className="container">
            <h2 id="users-title" className="section__title reveal">이런 분들을 위해 만들었습니다</h2>
            <ul className="users__list" role="list">
              <li className="user-item reveal reveal-delay-1">
                <span className="user-item__marker" aria-hidden="true">→</span>
                <p>연구 성과를 SNS나 기관 홈페이지에 올려야 하는 <strong>연구원</strong></p>
              </li>
              <li className="user-item reveal reveal-delay-2">
                <span className="user-item__marker" aria-hidden="true">→</span>
                <p>논문 내용을 대중 언어로 바꿔야 하는 <strong>홍보·커뮤니케이션 담당자</strong></p>
              </li>
              <li className="user-item reveal reveal-delay-3">
                <span className="user-item__marker" aria-hidden="true">→</span>
                <p>다수의 논문을 정기적으로 카드뉴스로 제작해야 하는 <strong>연구소·학술기관 팀</strong></p>
              </li>
            </ul>
          </div>
        </section>

        {/* ─── Trust Points ─── */}
        <section className="section section--subtle" aria-labelledby="trust-title">
          <div className="container">
            <h2 id="trust-title" className="section__title reveal">정확성을 설계에 넣었습니다</h2>
            <div className="trust__grid">
              <article className="trust-item reveal reveal-delay-1">
                <h3 className="trust-item__title">수치에 출처 자동 표기</h3>
                <p className="trust-item__desc">모든 숫자에 섹션명과 페이지가 함께 표시됩니다.</p>
              </article>
              <article className="trust-item reveal reveal-delay-2">
                <h3 className="trust-item__title">위험 항목 경고</h3>
                <p className="trust-item__desc">검증이 불확실한 항목은 에디터에서 명확히 표시됩니다.</p>
              </article>
              <article className="trust-item reveal reveal-delay-3">
                <h3 className="trust-item__title">AI 결과 강제 없음</h3>
                <p className="trust-item__desc">생성된 모든 내용은 에디터에서 수정하거나 삭제할 수 있습니다.</p>
              </article>
              <article className="trust-item reveal reveal-delay-4">
                <h3 className="trust-item__title">프로젝트 이력 보존</h3>
                <p className="trust-item__desc">변환한 논문과 작업 내역은 대시보드에서 언제든 다시 확인할 수 있습니다.</p>
              </article>
            </div>
          </div>
        </section>

        {/* ─── CTA ─── */}
        <section className="section section--dark cta-section" aria-labelledby="cta-title">
          <div className="container cta__inner">
            <h2 id="cta-title" className="cta__title reveal">지금 논문을 업로드해 보세요.</h2>
            <p className="cta__sub reveal reveal-delay-1">무료로 시작할 수 있습니다.</p>
            <a href="/dashboard" className="btn btn-white btn-lg reveal reveal-delay-2">바로 테스트하기</a>
          </div>
        </section>

      </main>

      <footer className="footer" role="contentinfo">
        <div className="container footer__inner">
          <p className="footer__logo">PolyInsight</p>
          <div className="footer__links">
            <a href="#">개인정보 처리방침</a>
            <a href="#">이용약관</a>
            <a href="#">문의하기</a>
          </div>
          <p className="footer__copy">&copy; 2026 PolyInsight. All rights reserved.</p>
        </div>
      </footer>

    </>
  );
}
