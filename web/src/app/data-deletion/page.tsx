import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = { title: '데이터 삭제 요청 — PolyInsight' };

const S: Record<string, React.CSSProperties> = {
  wrap: { maxWidth: 720, margin: '0 auto', padding: '64px 24px 96px', lineHeight: 1.75 },
  h1: { fontSize: 28, fontWeight: 700, marginBottom: 8 },
  date: { color: 'var(--text-3)', fontSize: 13, marginBottom: 40 },
  h2: { fontSize: 18, fontWeight: 700, marginTop: 36, marginBottom: 10 },
  p: { fontSize: 14.5, color: 'var(--text-2)', marginBottom: 10 },
  li: { fontSize: 14.5, color: 'var(--text-2)', marginBottom: 6 },
};

export default function DataDeletionPage() {
  return (
    <article style={S.wrap}>
      <Link href="/" className="auth-link">← PolyInsight 홈</Link>
      <h1 style={{ ...S.h1, marginTop: 24 }}>데이터 삭제 요청</h1>
      <p style={S.date}>시행일: 2026년 7월 3일</p>

      <h2 style={S.h2}>1. 삭제되는 데이터</h2>
      <ul style={{ paddingLeft: 20 }}>
        <li style={S.li}>계정 정보: 이메일 주소, 비밀번호 해시</li>
        <li style={S.li}>업로드한 논문 PDF와 생성된 카드뉴스</li>
        <li style={S.li}>연동한 소셜 계정 정보(Google 등)</li>
        <li style={S.li}>서비스 이용 기록(로그인·생성·내보내기 이벤트, 접속 로그)</li>
      </ul>

      <h2 style={S.h2}>2. 삭제 요청 방법</h2>
      <p style={S.p}>
        아래 이메일로 가입 시 사용한 이메일 주소와 함께 삭제를 요청해 주세요.
        본인 확인 후 처리합니다.
      </p>
      <ul style={{ paddingLeft: 20 }}>
        <li style={S.li}>이메일: dbstpgns789@gmail.com</li>
        <li style={S.li}>제목: [데이터 삭제 요청]</li>
        <li style={S.li}>내용: 가입 이메일 주소</li>
      </ul>

      <h2 style={S.h2}>3. 처리 기한</h2>
      <p style={S.p}>
        요청 접수 후 30일 이내에 위 데이터를 서버에서 영구 삭제하고, 완료 시 회신드립니다.
        업로드한 논문과 생성물은 이용자가 서비스 내에서 직접 삭제할 수도 있으며,
        내보내기 파일은 생성 후 24시간이 지나면 자동 삭제됩니다.
      </p>

      <h2 style={S.h2}>4. 관련 문서</h2>
      <p style={S.p}>
        데이터 수집·이용·보관에 관한 전체 내용은{' '}
        <Link href="/privacy" className="auth-link">개인정보 처리방침</Link>을 확인해 주세요.
      </p>
    </article>
  );
}
