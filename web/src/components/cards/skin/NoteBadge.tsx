// NoteBadge — LAB_NOTE 템플릿 전용 식별 배지. 우상단, 점선 라벨 + 모노스페이스 카드번호.
// template.badge가 정의된 템플릿만 CardFrame이 렌더한다.

interface NoteBadgeProps {
  cardNum: number
  labelPrefix: string
}

export default function NoteBadge({ cardNum, labelPrefix }: NoteBadgeProps) {
  return (
    <div style={{
      // top: 14 — 모든 스켈레톤이 BrandMark를 CardSurface 패딩(--set-pad, 88px) 안쪽에
      // 우상단으로 렌더한다. top:48 이상이면 회전된 배지 하단이 그 줄과 겹친다.
      position: 'absolute', top: 14, right: 56, zIndex: 3,
      padding: '8px 18px', borderRadius: 10,
      border: '1.5px dashed var(--set-accent)',
      background: 'var(--set-surface)',
      transform: 'rotate(-2.5deg)',
      pointerEvents: 'none',
    }}>
      <span style={{
        fontFamily: 'var(--set-mono, monospace)', fontSize: 22, fontWeight: 600,
        color: 'var(--set-accent)', letterSpacing: '0.02em',
      }}>
        {labelPrefix} {String(cardNum).padStart(2, '0')}
      </span>
    </div>
  )
}
