// 카드의 image_mode를 피부 컴포넌트로 흘려보내는 Context.
// VisualZone/CardSurface가 이 값을 읽어 렌더 방식을 결정한다.
'use client'

import { createContext, useContext, type ReactNode } from 'react'
import type { ImageMode, VisualKind } from '@/types/editor'

const ImageModeContext = createContext<ImageMode>('box')

export function ImageModeProvider({ value, children }: { value: ImageMode; children: ReactNode }) {
  return <ImageModeContext.Provider value={value}>{children}</ImageModeContext.Provider>
}

export function useImageMode(): ImageMode {
  return useContext(ImageModeContext)
}

// image_mode와 독립된 차원 — 사진/일러스트. focal 클릭 활성 여부만 갈라치는 용도(docs/18 §6.1).
const VisualKindContext = createContext<VisualKind>('photo')

export function VisualKindProvider({ value, children }: { value: VisualKind; children: ReactNode }) {
  return <VisualKindContext.Provider value={value}>{children}</VisualKindContext.Provider>
}

export function useVisualKind(): VisualKind {
  return useContext(VisualKindContext)
}
