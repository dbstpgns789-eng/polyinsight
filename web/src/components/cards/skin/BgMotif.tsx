// BgMotif — 배경 장식. 미니멀 프리미엄(라이트 에디토리얼): 동심원 대신 소프트 악센트 워시.
// 종이에 스민 듯한 미세 입체감만, 클러터 없이. 색/투명도는 피부 토큰에서.

export default function BgMotif() {
  return (
    <div aria-hidden style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      {/* 우하단 — 소프트 악센트 글로우(미세 입체감) */}
      <div style={{
        position: 'absolute', bottom: -170, right: -130,
        width: 540, height: 540, borderRadius: '50%',
        background: 'radial-gradient(circle, var(--set-accent) 0%, transparent 68%)',
        opacity: 'var(--set-glow-opacity, 0.07)',
      }} />
      {/* 좌상단 — 페인트 워시(종이 질감) */}
      <div style={{
        position: 'absolute', top: -210, left: -190,
        width: 560, height: 560, borderRadius: '50%',
        background: 'radial-gradient(circle, var(--set-accent) 0%, transparent 70%)',
        opacity: 'calc(var(--set-glow-opacity, 0.07) * 0.55)',
      }} />
    </div>
  )
}
