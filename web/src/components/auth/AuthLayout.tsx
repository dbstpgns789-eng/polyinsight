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

          <p className="auth-brand__verify">
            <span className="auth-brand__verify-mark" aria-hidden="true">✓</span>
            모든 수치는 논문 원문에서 검증됩니다
          </p>
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
