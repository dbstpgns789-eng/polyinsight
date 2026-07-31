import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = { title: '개인정보 처리방침 — PaperSweep' };

const S: Record<string, React.CSSProperties> = {
  wrap: { maxWidth: 720, margin: '0 auto', padding: '64px 24px 96px', lineHeight: 1.75 },
  h1: { fontSize: 28, fontWeight: 700, marginBottom: 8 },
  date: { color: 'var(--text-3)', fontSize: 13, marginBottom: 40 },
  h2: { fontSize: 18, fontWeight: 700, marginTop: 36, marginBottom: 10 },
  p: { fontSize: 14.5, color: 'var(--text-2)', marginBottom: 10 },
  li: { fontSize: 14.5, color: 'var(--text-2)', marginBottom: 6 },
};

export default function PrivacyPage() {
  return (
    <article style={S.wrap}>
      <Link href="/" className="auth-link">← PaperSweep 홈</Link>
      <h1 style={{ ...S.h1, marginTop: 24 }}>개인정보 처리방침</h1>
      <p style={S.date}>시행일: 2026년 7월 3일</p>

      <h2 style={S.h2}>1. 수집하는 정보</h2>
      <ul style={{ paddingLeft: 20 }}>
        <li style={S.li}>계정 정보: 이메일 주소, 비밀번호(암호화 해시로만 저장, 원문 미보관)</li>
        <li style={S.li}>소셜 로그인 시: 제공자(Google)가 전달하는 이메일 주소</li>
        <li style={S.li}>이용자가 업로드한 논문 PDF와 생성된 카드뉴스</li>
        <li style={S.li}>서비스 이용 기록(로그인·생성·내보내기 이벤트, 접속 로그)</li>
      </ul>

      <h2 style={S.h2}>2. 이용 목적</h2>
      <p style={S.p}>
        회원 관리(가입·로그인·비밀번호 재설정), 카드뉴스 생성 서비스 제공,
        서비스 안정성 확보(부정 이용 방지)를 위해서만 사용합니다.
      </p>

      <h2 style={S.h2}>3. 처리 위탁 및 제3자 제공</h2>
      <ul style={{ paddingLeft: 20 }}>
        <li style={S.li}>이메일 발송: Resend (가입 인증·비밀번호 재설정 메일)</li>
        <li style={S.li}>AI 처리: 업로드한 논문의 텍스트가 카드뉴스 생성을 위해 Anthropic API로 전송됩니다. 학습 목적으로 사용되지 않습니다.</li>
        <li style={S.li}>소셜 로그인: Google (이용자가 선택한 경우에만)</li>
      </ul>
      <p style={S.p}>이 외에 개인정보를 제3자에게 판매하거나 제공하지 않습니다.</p>

      <h2 style={S.h2}>4. 보관 및 파기</h2>
      <p style={S.p}>
        개인정보는 회원 탈퇴 시 지체 없이 파기합니다. 업로드한 논문과 생성물은
        이용자가 직접 삭제할 수 있으며, 삭제 시 서버에서 제거됩니다.
        내보내기 파일은 생성 후 24시간이 지나면 자동 삭제됩니다.
      </p>

      <h2 style={S.h2}>5. 이용자의 권리</h2>
      <p style={S.p}>
        이용자는 언제든지 자신의 개인정보 열람·정정·삭제를 요청할 수 있습니다.
        아래 연락처로 요청해 주세요.
      </p>

      <h2 style={S.h2}>6. 보호 조치</h2>
      <p style={S.p}>
        비밀번호는 argon2 해시로만 저장하고, 세션 토큰은 해시 처리하여 보관합니다.
        전송 구간은 HTTPS로 암호화합니다.
      </p>

      <h2 style={S.h2}>7. 문의</h2>
      <p style={S.p}>
        개인정보 관련 문의: dbstpgns789@gmail.com
      </p>
    </article>
  );
}
