// BrandMark — POLYINSIGHT 로고 마크(정적, 편집 불가). 우상단 배치.

export default function BrandMark() {
  return (
    <div aria-hidden style={{
      fontFamily: 'var(--set-font)',
      fontSize: 'var(--set-eyebrow)',
      fontWeight: 800,
      letterSpacing: '0.06em',
      color: 'var(--set-ink-faint)',
      whiteSpace: 'nowrap',
    }}>
      POLY<span style={{ color: 'var(--set-accent)' }}>INSIGHT</span>
    </div>
  )
}
