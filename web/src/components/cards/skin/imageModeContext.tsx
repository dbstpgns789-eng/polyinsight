// web/src/components/cards/skin/imageModeContext.tsx
import { createContext, useContext, type ReactNode } from 'react'
import type { ImageMode } from '@/types/editor'

const ImageModeContext = createContext<ImageMode>('box')

export function ImageModeProvider({ value, children }: { value: ImageMode; children: ReactNode }) {
  return <ImageModeContext.Provider value={value}>{children}</ImageModeContext.Provider>
}

export function useImageMode(): ImageMode {
  return useContext(ImageModeContext)
}
