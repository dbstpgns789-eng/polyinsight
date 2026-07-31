import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '갤러리 - PolyInsight',
  description: '논문 PDF에서 만들어진 카드뉴스 모음.',
}

export default function GalleryLayout({ children }: { children: React.ReactNode }) {
  return children
}
