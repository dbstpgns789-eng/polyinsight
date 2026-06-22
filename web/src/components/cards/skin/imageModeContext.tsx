// 카드의 image_mode를 피부 컴포넌트로 흘려보내는 Context.
// VisualZone/CardSurface가 이 값을 읽어 렌더 방식을 결정한다.
'use client'

import { createContext, useContext, type ReactNode } from 'react'
import type { ImageMode } from '@/types/editor'

const ImageModeContext = createContext<ImageMode>('box')

export function ImageModeProvider({ value, children }: { value: ImageMode; children: ReactNode }) {
  return <ImageModeContext.Provider value={value}>{children}</ImageModeContext.Provider>
}

export function useImageMode(): ImageMode {
  return useContext(ImageModeContext)
}
