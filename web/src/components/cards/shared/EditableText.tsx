// EditableText — contenteditable 텍스트 프리미티브.
//
// 핵심 원칙 (cursor jump 방지):
//  - focused 상태에서는 React가 DOM textContent를 절대 건드리지 않음
//  - 외부 value 변경은 not-focused 시점에만 imperative하게 반영
//  - onInput은 200ms 로컬 debounce 후 부모로 (fieldKey, value) 발행
//  - onBlur 시 강제 flush
//
// 모드:
//  - edit:      contentEditable=true, 클릭 시 편집
//  - render:    순수 텍스트 (S7 시각 회귀, 미리보기)
//  - thumbnail: 순수 텍스트 (썸네일)

'use client'

import { type CSSProperties, type JSX, useCallback, useEffect, useRef, useState } from 'react'

type Mode = 'edit' | 'render' | 'thumbnail'

interface EditableTextProps {
  value: string
  fieldKey: string
  mode: Mode
  as?: keyof JSX.IntrinsicElements
  className?: string
  style?: CSSProperties
  multiline?: boolean
  onFieldChange?: (fieldKey: string, value: string) => void
  onFieldFocus?: (fieldKey: string) => void
  focused?: boolean
}

const FLUSH_DELAY_MS = 200

export default function EditableText({
  value,
  fieldKey,
  mode,
  as: Tag = 'span',
  className,
  style,
  multiline = false,
  onFieldChange,
  onFieldFocus,
  focused,
}: EditableTextProps) {
  const ref = useRef<HTMLElement | null>(null)
  const pendingRef = useRef<string | null>(null)
  const timerRef = useRef<number | null>(null)
  const isFocusedRef = useRef(false)
  const [hovered, setHovered] = useState(false)

  // 외부 value 변경 반영: focused 중에는 절대 건드리지 않음.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (isFocusedRef.current) return
    if (el.textContent !== value) {
      el.textContent = value
    }
  }, [value])

  // 초기 마운트 시 textContent 세팅 (편집 모드 + 비편집 모드 공통)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (el.textContent !== value) {
      el.textContent = value
    }
    // 초기 마운트만 수행
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const flush = useCallback(() => {
    if (pendingRef.current === null) return
    const next = pendingRef.current
    pendingRef.current = null
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
    onFieldChange?.(fieldKey, next)
  }, [fieldKey, onFieldChange])

  const handleInput = useCallback(() => {
    const el = ref.current
    if (!el) return
    const text = multiline ? (el.innerText ?? '') : (el.textContent ?? '')
    pendingRef.current = text
    if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(flush, FLUSH_DELAY_MS)
  }, [flush, multiline])

  const handleFocus = useCallback(() => {
    isFocusedRef.current = true
    onFieldFocus?.(fieldKey)
  }, [fieldKey, onFieldFocus])

  const handleBlur = useCallback(() => {
    isFocusedRef.current = false
    flush()
  }, [flush])

  // 모드별 분기
  const isEditable = mode === 'edit'

  const TagAny = Tag as unknown as 'span'
  return (
    <TagAny
      ref={(el: HTMLElement | null) => { ref.current = el }}
      contentEditable={isEditable}
      suppressContentEditableWarning
      spellCheck={false}
      data-field={fieldKey}
      data-focused={focused ? 'true' : undefined}
      className={className}
      style={{
        ...style,
        cursor: isEditable ? 'text' : undefined,
        background: isEditable && hovered && !focused ? 'rgba(22,163,74,0.08)' : undefined,
        borderRadius: (isEditable && hovered && !focused) || focused ? 4 : undefined,
        outline: focused ? '1.5px solid var(--brand)' : undefined,
        outlineOffset: focused ? '4px' : undefined,
        whiteSpace: multiline ? 'pre-wrap' : undefined,
      }}
      onInput={isEditable ? handleInput : undefined}
      onFocus={isEditable ? handleFocus : undefined}
      onBlur={isEditable ? handleBlur : undefined}
      onMouseEnter={isEditable ? () => setHovered(true) : undefined}
      onMouseLeave={isEditable ? () => setHovered(false) : undefined}
    />
  )
}
