import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: '갤러리 - PolyInsight',
  description:
    '논문 PDF에서 만들어진 실제 카드뉴스 산출물 모음. 연구성과 카드뉴스 3편과 AI 논문 20편 시리즈 운영 사례.',
}

export default function GalleryLayout({ children }: { children: React.ReactNode }) {
  return children
}
