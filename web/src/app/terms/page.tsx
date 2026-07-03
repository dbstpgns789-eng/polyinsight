import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = { title: '이용약관 — PolyInsight' };

const S: Record<string, React.CSSProperties> = {
  wrap: { maxWidth: 720, margin: '0 auto', padding: '64px 24px 96px', lineHeight: 1.75 },
  h1: { fontSize: 28, fontWeight: 700, marginBottom: 8 },
  date: { color: 'var(--text-3)', fontSize: 13, marginBottom: 40 },
  h2: { fontSize: 18, fontWeight: 700, marginTop: 36, marginBottom: 10 },
  p: { fontSize: 14.5, color: 'var(--text-2)', marginBottom: 10 },
};

export default function TermsPage() {
  return (
    <article style={S.wrap}>
      <Link href="/" className="auth-link">← PolyInsight 홈</Link>
      <h1 style={{ ...S.h1, marginTop: 24 }}>이용약관</h1>
      <p style={S.date}>시행일: 2026년 7월 3일</p>

      <h2 style={S.h2}>제1조 (목적)</h2>
      <p style={S.p}>
        이 약관은 PolyInsight(이하 &ldquo;서비스&rdquo;)가 제공하는 학술 논문 기반 카드뉴스 생성
        서비스의 이용 조건과 운영자·이용자의 권리와 의무를 정합니다.
      </p>

      <h2 style={S.h2}>제2조 (서비스 내용)</h2>
      <p style={S.p}>
        서비스는 이용자가 업로드한 논문 PDF를 분석하여 카드뉴스 초안을 자동 생성하고,
        수치 검증·편집·내보내기 기능을 제공합니다. 생성 결과는 AI가 작성한 초안이며,
        게시 전 내용 확인과 최종 판단의 책임은 이용자에게 있습니다.
      </p>

      <h2 style={S.h2}>제3조 (계정)</h2>
      <p style={S.p}>
        이용자는 이메일 또는 소셜 계정으로 가입할 수 있으며, 계정 정보를 정확히 유지하고
        비밀번호를 안전하게 관리할 책임이 있습니다. 계정 도용이 의심되면 즉시 비밀번호를
        변경하고 운영자에게 알려 주세요.
      </p>

      <h2 style={S.h2}>제4조 (콘텐츠와 권리)</h2>
      <p style={S.p}>
        이용자가 업로드한 논문과 생성된 카드뉴스에 대한 권리는 이용자(또는 원저작권자)에게
        있습니다. 이용자는 업로드하는 자료에 대해 적법한 이용 권한을 보유해야 하며,
        타인의 저작권을 침해하는 자료를 업로드해서는 안 됩니다.
      </p>

      <h2 style={S.h2}>제5조 (금지 행위)</h2>
      <p style={S.p}>
        서비스의 정상 운영을 방해하는 행위(자동화된 대량 요청, 취약점 악용 시도 등),
        타인의 계정 무단 사용, 법령에 위반되는 콘텐츠 생성·유포를 금지합니다.
      </p>

      <h2 style={S.h2}>제6조 (서비스 변경·중단)</h2>
      <p style={S.p}>
        운영자는 서비스 개선을 위해 기능을 변경할 수 있으며, 불가피한 사유로 서비스가
        일시 중단될 수 있습니다. 중대한 변경은 사전에 공지합니다.
      </p>

      <h2 style={S.h2}>제7조 (책임의 한계)</h2>
      <p style={S.p}>
        AI가 생성한 콘텐츠의 정확성은 보장되지 않으며, 서비스는 수치 검증 결과를 참고
        정보로 제공합니다. 생성물을 외부에 게시·배포하여 발생하는 결과에 대한 책임은
        이용자에게 있습니다.
      </p>

      <h2 style={S.h2}>제8조 (문의)</h2>
      <p style={S.p}>
        약관에 대한 문의는 dbstpgns789@gmail.com 으로 연락해 주세요.
      </p>
    </article>
  );
}
