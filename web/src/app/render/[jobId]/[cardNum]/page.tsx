'use client'

// /render/[jobId]/[cardNum] — PNG 출력 전용 라우트.
//
// 백엔드 S7(Playwright)이 이 페이지를 goto해서 1080×1080 스크린샷을 찍는다.
// 에디터와 같은 React CardRenderer를 mode="render" scale=1로 호스트 → 단일 소스.
//
// 핵심 계약:
//  - 정확히 1080×1080, 좌상단 정렬, 패딩 0
//  - 데이터 + 폰트 로딩 완료 시 <body data-render-ready="1"> 신호
//    → 백엔드가 wait_for_selector("[data-render-ready]")로 대기 (폰트 race 방지)

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import CardRenderer from '@/components/cards/CardRenderer'
import { MOCK_EDITOR_DATA } from '@/lib/mockData'
import { getCards } from '@/lib/api'
import type { CardDataPayload, CardTheme } from '@/types/editor'

const DEFAULT_THEME: CardTheme = { primary: '#16A34A', dark: '#166534' }

export default function RenderPage() {
  const params = useParams()
  const jobId = params.jobId as string
  const cardNum = Number(params.cardNum)
  const isDemo = jobId === 'demo'

  const [cardData, setCardData] = useState<CardDataPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 데이터 로드
  useEffect(() => {
    let cancelled = false
    if (isDemo) {
      setCardData(MOCK_EDITOR_DATA.cardData ?? null)
      return
    }
    getCards(jobId)
      .then((r) => { if (!cancelled) setCardData(r.data.cardData) })
      .catch((e) => { if (!cancelled) setError(e.message ?? '데이터 로드 실패') })
    return () => { cancelled = true }
  }, [jobId, isDemo])

  const card = cardData?.cards.find((c) => c.card_num === cardNum)
  const theme = cardData?.theme ?? DEFAULT_THEME

  // 데이터 + 폰트 로딩 완료 신호 → 백엔드 스크린샷 트리거
  useEffect(() => {
    if (!card) return
    let cancelled = false
    document.fonts.ready.then(() => {
      // 폰트 적용 후 한 프레임 양보해서 페인트 완료 보장
      requestAnimationFrame(() => {
        if (!cancelled) document.body.setAttribute('data-render-ready', '1')
      })
    })
    return () => { cancelled = true }
  }, [card])

  if (error) {
    return <div data-render-error style={{ padding: 40, fontFamily: 'sans-serif' }}>렌더 실패: {error}</div>
  }
  if (!card) {
    return <div style={{ padding: 40, fontFamily: 'sans-serif' }}>카드 로딩 중…</div>
  }

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: 1080, height: 1080, overflow: 'hidden', background: '#fff' }}>
      <CardRenderer card={card} theme={theme} bgColor={cardData?.bg_color} accentColor={cardData?.accent_color} fontPairing={cardData?.font_pairing} mode="render" scale={1} />
    </div>
  )
}
