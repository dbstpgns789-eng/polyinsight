// EditableImage — 카드 내부의 이미지 영역.
//
// 모드:
//  - edit:      클릭 시 onImageRequest(slotKey) 호출 (RightPanel 업로드 위젯 트리거)
//  - render:    순수 <img>
//  - thumbnail: 순수 <img>
//
// imageUrl 없으면 빈 슬롯(점선 박스 + 아이콘) 표시 (edit 모드만).

'use client'

import { type CSSProperties, useState } from 'react'

type Mode = 'edit' | 'render' | 'thumbnail'

interface EditableImageProps {
  imageUrl?: string
  slotKey: string
  mode: Mode
  alt?: string
  className?: string
  style?: CSSProperties
  objectFit?: 'cover' | 'contain'
  onImageRequest?: (slotKey: string) => void
}

export default function EditableImage({
  imageUrl,
  slotKey,
  mode,
  alt = '',
  className,
  style,
  objectFit = 'cover',
  onImageRequest,
}: EditableImageProps) {
  const [hovered, setHovered] = useState(false)
  const isEditable = mode === 'edit'

  if (imageUrl) {
    return (
      <div
        className={className}
        style={{ position: 'relative', width: '100%', height: '100%', ...style }}
        onMouseEnter={isEditable ? () => setHovered(true) : undefined}
        onMouseLeave={isEditable ? () => setHovered(false) : undefined}
      >
        <img
          src={imageUrl}
          alt={alt}
          style={{
            width: '100%',
            height: '100%',
            objectFit,
            objectPosition: 'center',
            display: 'block',
          }}
        />
        {isEditable && (
          <button
            type="button"
            onClick={() => onImageRequest?.(slotKey)}
            aria-label="이미지 교체"
            style={{
              position: 'absolute',
              inset: 0,
              background: hovered ? 'rgba(0, 0, 0, 0.40)' : 'transparent',
              border: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'background 150ms ease',
            }}
          >
            {hovered && (
              <span style={{
                background: 'rgba(255, 255, 255, 0.92)',
                color: '#111',
                fontSize: 16,
                fontWeight: 700,
                padding: '8px 16px',
                borderRadius: 8,
                pointerEvents: 'none',
              }}>
                이미지 교체
              </span>
            )}
          </button>
        )}
      </div>
    )
  }

  // 빈 슬롯 (edit 모드만 표시; render/thumbnail은 null)
  if (!isEditable) return null

  return (
    <button
      type="button"
      onClick={() => onImageRequest?.(slotKey)}
      aria-label="이미지 추가"
      className={className}
      style={{
        width: '100%',
        height: '100%',
        background: 'rgba(0, 0, 0, 0.06)',
        border: '3px dashed rgba(0, 0, 0, 0.25)',
        borderRadius: 8,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        cursor: 'pointer',
        transition: 'all 150ms ease',
        color: 'rgba(0, 0, 0, 0.5)',
        ...style,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(0, 0, 0, 0.10)'
        e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.40)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(0, 0, 0, 0.06)'
        e.currentTarget.style.borderColor = 'rgba(0, 0, 0, 0.25)'
      }}
    >
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="9" cy="9" r="2" />
        <path d="M21 15l-5-5L5 21" />
      </svg>
      <span style={{ fontSize: 20, fontWeight: 600 }}>이미지 추가</span>
    </button>
  )
}
