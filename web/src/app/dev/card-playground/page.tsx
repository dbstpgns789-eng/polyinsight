// /dev/card-playground — Phase 1 primitives 동작 검증용 dev 페이지.
//
// 사용 방법:
//   1. `npm run dev`
//   2. http://localhost:3000/dev/card-playground 접속
//   3. 텍스트 클릭 → 인라인 편집, 이미지 영역 클릭 → 콘솔 로그
//
// Phase 2에서 12개 카드 컴포넌트가 등록되면 여기서 각 템플릿 미리보기 가능.

'use client'

import { useState } from 'react'
import CardFrame from '@/components/cards/CardFrame'
import CardRenderer from '@/components/cards/CardRenderer'
import EditableText from '@/components/cards/shared/EditableText'
import EditableImage from '@/components/cards/shared/EditableImage'
import { TEMPLATE_TYPES } from '@/lib/templateFields'
import type { CardMode } from '@/components/cards/types'
import type { Card, CardTheme } from '@/types/editor'

const MOCK_THEME: CardTheme = { primary: '#2563EB', dark: '#1A4C96' }

const MOCK_CARDS: Card[] = TEMPLATE_TYPES.map((t, i) => ({
  card_num: i + 1,
  template_type: t,
  fields: {
    title: { value: `${t} 카드 제목` },
    body: { value: '본문 내용이 여기 표시됩니다.' },
  },
}))

export default function CardPlaygroundPage() {
  const [mode, setMode] = useState<CardMode>('edit')
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const [titleValue, setTitleValue] = useState('편집 가능한 큰 타이틀')
  const [bodyValue, setBodyValue] = useState('본문 텍스트. 여기를 클릭해서 수정해 보세요.')
  const [imageUrl, setImageUrl] = useState<string | undefined>(undefined)

  const handleFieldChange = (key: string, value: string) => {
    console.log('[playground] field change', key, value)
    if (key === 'title') setTitleValue(value)
    if (key === 'body') setBodyValue(value)
  }

  const handleImageRequest = (slotKey: string) => {
    console.log('[playground] image request for slot', slotKey)
    // 데모용 더미 이미지 토글
    setImageUrl((prev) => prev ? undefined : 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=1080')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5', padding: 32 }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>Card Playground</h1>
        <p style={{ color: '#666' }}>Phase 1 — Shared primitives 동작 확인</p>
      </header>

      <div style={{ marginBottom: 24, display: 'flex', gap: 12, alignItems: 'center' }}>
        <strong>모드:</strong>
        {(['edit', 'render', 'thumbnail'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: mode === m ? '2px solid #2563EB' : '1px solid #ccc',
              background: mode === m ? '#dbeafe' : '#fff',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            {m}
          </button>
        ))}
      </div>

      {/* Primitives in isolation */}
      <section style={{ marginBottom: 48, background: '#fff', padding: 24, borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>1. EditableText (with CardFrame + theme injection)</h2>
        <CardFrame theme={MOCK_THEME} scale={0.4}>
          <div style={{
            width: '100%',
            height: '100%',
            background: 'var(--theme-dark)',
            padding: 80,
            display: 'flex',
            flexDirection: 'column',
            gap: 32,
            justifyContent: 'center',
          }}>
            <EditableText
              fieldKey="title"
              value={titleValue}
              mode={mode}
              onFieldChange={handleFieldChange}
              onFieldFocus={setFocusedField}
              focused={focusedField === 'title'}
              style={{ fontSize: 88, fontWeight: 900, color: '#fff', lineHeight: 1.1 }}
            />
            <EditableText
              fieldKey="body"
              value={bodyValue}
              mode={mode}
              multiline
              onFieldChange={handleFieldChange}
              onFieldFocus={setFocusedField}
              focused={focusedField === 'body'}
              style={{ fontSize: 32, color: 'rgba(255,255,255,0.8)', lineHeight: 1.5 }}
            />
            <div style={{ width: 60, height: 6, background: 'var(--theme-primary)', borderRadius: 3 }} />
          </div>
        </CardFrame>
      </section>

      {/* EditableImage standalone */}
      <section style={{ marginBottom: 48, background: '#fff', padding: 24, borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>2. EditableImage</h2>
        <div style={{ width: 432, height: 432, background: '#fafafa', borderRadius: 8 }}>
          <EditableImage
            slotKey="bg"
            imageUrl={imageUrl}
            mode={mode}
            onImageRequest={handleImageRequest}
          />
        </div>
        <p style={{ marginTop: 12, color: '#666', fontSize: 14 }}>
          빈 상태 클릭 → 이미지 추가. 이미지 있는 상태 호버 → "이미지 교체" 버튼.
        </p>
      </section>

      {/* CardRenderer dispatcher — Phase 2 전까지 unimplemented placeholder */}
      <section style={{ background: '#fff', padding: 24, borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>3. CardRenderer (Phase 2 대기)</h2>
        <p style={{ marginBottom: 16, color: '#666', fontSize: 14 }}>
          템플릿별 실제 React 컴포넌트는 Phase 2에서 추가됩니다. 현재는 "구현 대기 중" placeholder.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {MOCK_CARDS.slice(0, 6).map((card) => (
            <div key={card.card_num} style={{ background: '#fafafa', padding: 8, borderRadius: 8 }}>
              <CardRenderer
                card={card}
                theme={MOCK_THEME}
                mode={mode}
                scale={0.28}
                onFieldChange={handleFieldChange}
                onImageRequest={handleImageRequest}
              />
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
