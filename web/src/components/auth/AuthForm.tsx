'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

type Mode = 'login' | 'signup';

interface Errors {
  email?: string;
  password?: string;
  confirm?: string;
  form?: string;
}

export default function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm]   = useState('');
  const [errors, setErrors]   = useState<Errors>({});
  const [loading, setLoading] = useState(false);

  const isLogin = mode === 'login';

  function clearFieldError(field: keyof Errors) {
    if (errors[field]) setErrors(prev => { const next = { ...prev }; delete next[field]; return next; });
  }

  function validate(): Errors {
    const e: Errors = {};
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      e.email = '유효한 이메일 주소를 입력해 주세요.';
    }
    if (!password || password.length < 8) {
      e.password = '비밀번호는 8자 이상이어야 합니다.';
    }
    if (!isLogin && password !== confirm) {
      e.confirm = '비밀번호가 일치하지 않습니다.';
    }
    return e;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setLoading(true);
    setTimeout(() => {
      localStorage.setItem('isLoggedIn', 'true');
      router.push('/dashboard');
    }, 600);
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate aria-label={isLogin ? '로그인' : '회원가입'}>
      <div className="auth-form__head">
        {!isLogin && <p className="auth-form__sub">연구 성과를 카드뉴스로.</p>}
        <h1 className="auth-form__title">{isLogin ? '로그인' : '회원가입'}</h1>
      </div>

      {errors.form && (
        <div className="auth-error-banner" role="alert">{errors.form}</div>
      )}

      <div className="auth-fields">
        <div className="auth-field">
          <label htmlFor="auth-email" className="auth-field__label">이메일</label>
          <input
            id="auth-email"
            type="email"
            className="auth-input"
            placeholder="이메일 주소"
            value={email}
            onChange={e => { setEmail(e.target.value); clearFieldError('email'); }}
            autoComplete="email"
            aria-invalid={!!errors.email || undefined}
            aria-describedby={errors.email ? 'err-email' : undefined}
          />
          {errors.email && (
            <p className="auth-field__error" id="err-email" role="alert">{errors.email}</p>
          )}
        </div>

        <div className="auth-field">
          <label htmlFor="auth-password" className="auth-field__label">비밀번호</label>
          <input
            id="auth-password"
            type="password"
            className="auth-input"
            placeholder={isLogin ? '비밀번호' : '8자 이상'}
            value={password}
            onChange={e => { setPassword(e.target.value); clearFieldError('password'); }}
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            aria-invalid={!!errors.password || undefined}
            aria-describedby={errors.password ? 'err-password' : undefined}
          />
          {errors.password && (
            <p className="auth-field__error" id="err-password" role="alert">{errors.password}</p>
          )}
        </div>

        {!isLogin && (
          <div className="auth-field">
            <label htmlFor="auth-confirm" className="auth-field__label">비밀번호 확인</label>
            <input
              id="auth-confirm"
              type="password"
              className="auth-input"
              placeholder="비밀번호를 다시 입력하세요"
              value={confirm}
              onChange={e => { setConfirm(e.target.value); clearFieldError('confirm'); }}
              autoComplete="new-password"
              aria-invalid={!!errors.confirm || undefined}
              aria-describedby={errors.confirm ? 'err-confirm' : undefined}
            />
            {errors.confirm && (
              <p className="auth-field__error" id="err-confirm" role="alert">{errors.confirm}</p>
            )}
          </div>
        )}

      </div>

      <button
        type="submit"
        className="btn btn-primary btn-lg auth-submit"
        disabled={loading}
      >
        {loading ? (
          <>
            <svg className="auth-spinner" width="15" height="15" viewBox="0 0 16 16" aria-hidden="true">
              <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="25 13" strokeLinecap="round"/>
            </svg>
            {isLogin ? '로그인 중...' : '가입 중...'}
          </>
        ) : (isLogin ? '로그인' : '회원가입')}
      </button>

      <div className="auth-divider" aria-hidden="true"><span>또는</span></div>

      <button type="button" className="btn btn-outline btn-lg auth-social">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
          <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908C16.658 14.38 17.64 12.07 17.64 9.205Z" fill="#4285F4"/>
          <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
          <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
          <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
        </svg>
        Google로 계속하기
      </button>

      {!isLogin && (
        <p className="auth-terms">
          회원가입 시{' '}
          <a href="#" className="auth-link">이용약관</a>과{' '}
          <a href="#" className="auth-link">개인정보 처리방침</a>에 동의합니다.
        </p>
      )}

      <p className="auth-switch">
        {isLogin
          ? <>계정이 없으신가요? <Link href="/signup" className="auth-link auth-link--strong">회원가입</Link></>
          : <>이미 계정이 있으신가요? <Link href="/login" className="auth-link auth-link--strong">로그인</Link></>
        }
      </p>
    </form>
  );
}
