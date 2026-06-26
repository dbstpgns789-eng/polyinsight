// TickFrame — LAB_NOTE 템플릿 전용 반복 프레임. 하단 가운데, 짧은 눈금 N개.
// template.frame이 정의된 템플릿만 CardFrame이 렌더한다. 모든 카드에 동일 위치·개수로 반복돼야 "한 덱" 신호가 된다.

interface TickFrameProps {
  count: number
}

export default function TickFrame({ count }: TickFrameProps) {
  return (
    <div style={{
      position: 'absolute', bottom: 44, left: 0, right: 0, zIndex: 3,
      display: 'flex', justifyContent: 'center', gap: 14,
      pointerEvents: 'none',
    }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ width: 2, height: 16, background: 'var(--set-accent)', opacity: 0.5, borderRadius: 1 }} />
      ))}
    </div>
  )
}
