// EditableImage — 카드 내부의 이미지 영역.
//
// 모드:
//  - edit:      클릭 시 onImageRequest(slotKey) 호출 (RightPanel 업로드 위젯 트리거)
//  - render:    순수 <img>
//  - thumbnail: 순수 <img>
//
// imageUrl 없으면 빈 슬롯(점선 박스 + 아이콘) 표시 (edit 모드만).

'use client'

import { type CSSProperties, type MouseEvent, useState } from 'react'
import { clickToFocal, focalToObjectPosition, type Focal } from '@/lib/focal'

type Mode = 'edit' | 'render' | 'thumbnail'

interface EditableImageProps {
  imageUrl?: string
  slotKey: string
  mode: Mode
  alt?: string
  className?: string
  style?: CSSProperties
  objectFit?: 'cover' | 'contain'
  focal?: Focal
  onImageRequest?: (slotKey: string) => void
  onFocalChange?: (focal: Focal) => void
  onFitChange?: (fit: 'cover' | 'contain') => void
}

export default function EditableImage({
  imageUrl,
  slotKey,
  mode,
  alt = '',
  className,
  style,
  objectFit = 'cover',
  focal,
  onImageRequest,
  onFocalChange,
  onFitChange,
}: EditableImageProps) {
  const [hovered, setHovered] = useState(false)
  const isEditable = mode === 'edit'
  const objectPosition = objectFit === 'cover' ? focalToObjectPosition(focal) : 'center'

  if (imageUrl) {
    const handleFocalClick = (e: MouseEvent<HTMLDivElement>) => {
      if (!isEditable || !onFocalChange || objectFit !== 'cover') return
      const rect = e.currentTarget.getBoundingClientRect()
      onFocalChange(clickToFocal(e.clientX, e.clientY, rect))
    }

    return (
      <div
        className={className}
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          cursor: isEditable ? 'crosshair' : 'default',
          ...style,
        }}
        onMouseEnter={isEditable ? () => setHovered(true) : undefined}
        onMouseLeave={isEditable ? () => setHovered(false) : undefined}
        onClick={handleFocalClick}
      >
        <img
          src={imageUrl}
          alt={alt}
          style={{ width: '100%', height: '100%', objectFit, objectPosition, display: 'block' }}
        />

        {isEditable && (
          <>
            {/* 현재 초점 십자 표식 (클릭 통과) */}
            {objectFit === 'cover' && (
              <div
                style={{
                  position: 'absolute',
                  left: `${(focal?.x ?? 0.5) * 100}%`,
                  top: `${(focal?.y ?? 0.5) * 100}%`,
                  transform: 'translate(-50%, -50%)',
                  width: 26,
                  height: 26,
                  borderRadius: '50%',
                  border: '2px solid rgba(255, 255, 255, 0.95)',
                  boxShadow: '0 0 0 2px rgba(0, 0, 0, 0.45)',
                  pointerEvents: 'none',
                }}
              />
            )}
            {/* 우상단 교체 버튼 (stopPropagation으로 초점과 분리) */}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onImageRequest?.(slotKey) }}
              aria-label="이미지 교체"
              style={{
                position: 'absolute',
                top: 10,
                right: 10,
                width: 36,
                height: 36,
                borderRadius: 8,
                background: hovered ? 'rgba(0, 0, 0, 0.65)' : 'rgba(0, 0, 0, 0.45)',
                color: '#fff',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'background 150ms ease',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <polyline points="1 20 1 14 7 14" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
            </button>
            {onFitChange && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onFitChange(objectFit === 'cover' ? 'contain' : 'cover') }}
                aria-label="이미지 맞춤 전환"
                style={{
                  position: 'absolute',
                  top: 10,
                  left: 10,
                  height: 36,
                  padding: '0 12px',
                  borderRadius: 8,
                  background: hovered ? 'rgba(0, 0, 0, 0.65)' : 'rgba(0, 0, 0, 0.45)',
                  color: '#fff',
                  border: 'none',
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'background 150ms ease',
                }}
              >
                {objectFit === 'cover' ? '채움' : '전체'}
              </button>
            )}
          </>
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
