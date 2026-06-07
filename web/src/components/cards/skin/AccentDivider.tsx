// AccentDivider — 강조 구분선. accent 색 짧은 막대(에디토리얼 룰, 슬림).
export default function AccentDivider() {
  return <div aria-hidden style={{ width: 52, height: 5, borderRadius: 100, background: 'var(--set-accent)' }} />
}
