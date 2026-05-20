import type { ReactNode } from 'react';
import Link from 'next/link';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="auth-layout">
      <div className="auth-brand" aria-hidden="true">
        <div className="auth-brand__inner">
          <Link href="/" className="auth-brand__logo">
            Poly<span>Insight</span>
          </Link>

          <div className="auth-brand__content">
            <h1 className="auth-brand__headline">
              논문 PDF 하나로,<br />카드뉴스 완성
            </h1>
            <p className="auth-brand__sub">
              원문에서 직접 추출.<br />수치와 출처는 논문 그대로.
            </p>
          </div>

          <div className="auth-brand__proof">
            <div className="auth-proof-card">
              <div className="auth-proof-card__label">
                <span>연구 결과</span>
                <span>4 / 5 — 예시</span>
              </div>
              <p className="auth-proof-card__finding">
                전체 샘플에서{' '}
                <strong className="auth-proof-card__num">73.2%</strong>
                {' '}통계적 유의성 확인
              </p>
              <div className="auth-proof-card__cite">
                <svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true">
                  <rect x="1" y="1" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.1"/>
                  <line x1="3" y1="4" x2="8" y2="4" stroke="currentColor" strokeWidth="0.9" strokeLinecap="round"/>
                  <line x1="3" y1="6" x2="6.5" y2="6" stroke="currentColor" strokeWidth="0.9" strokeLinecap="round"/>
                </svg>
                Table 2, p.8
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-panel__inner">
          <div className="auth-mobile-brand">
            <Link href="/" className="auth-brand__logo" aria-label="PolyInsight 홈으로">
              Poly<span>Insight</span>
            </Link>
            <p className="auth-mobile-brand__desc">논문 PDF에서 카드뉴스를 자동 생성합니다.</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
