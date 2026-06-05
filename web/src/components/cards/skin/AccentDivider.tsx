// AccentDivider — 강조 구분선. accent 색 짧은 막대.
export default function AccentDivider() {
  return <div aria-hidden style={{ width: 64, height: 6, borderRadius: 3, background: 'var(--set-accent)' }} />
}
