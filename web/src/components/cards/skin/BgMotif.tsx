// BgMotif — 배경 장식(좌상단 동심원 + 우하단 광원). faint, 콘텐츠 뒤.
// 색/투명도는 피부 토큰에서. 뼈대는 이 컴포넌트를 놓기만 한다.

export default function BgMotif() {
  return (
    <div aria-hidden style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      <svg
        width={460} height={460}
        viewBox="0 0 200 200" fill="none"
        stroke="var(--set-ink-strong)" strokeWidth={1.2}
        style={{ position: 'absolute', top: -90, left: -90, opacity: 0.10 }}
      >
        <circle cx={100} cy={100} r={40} />
        <circle cx={100} cy={100} r={62} />
        <circle cx={100} cy={100} r={84} />
      </svg>
      <div style={{
        position: 'absolute', bottom: 120, right: -70,
        width: 280, height: 280, borderRadius: '50%',
        background: 'radial-gradient(circle, var(--set-accent) 0%, transparent 70%)',
        opacity: 0.14,
      }} />
    </div>
  )
}
