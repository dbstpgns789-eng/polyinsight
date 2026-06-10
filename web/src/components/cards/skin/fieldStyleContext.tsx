// 카드의 field_styles 맵을 피부 컴포넌트로 흘려보내는 Context.
// 뼈대는 이 존재를 모른다 — CardRenderer가 주입하고 피부 컴포넌트만 읽는다.
'use client'

import { createContext, useContext } from 'react'
import type { FieldStyle } from '@/types/editor'

const FieldStylesContext = createContext<Record<string, FieldStyle>>({})

export const FieldStylesProvider = FieldStylesContext.Provider

export function useFieldStyle(fieldKey: string): FieldStyle | undefined {
  return useContext(FieldStylesContext)[fieldKey]
}
