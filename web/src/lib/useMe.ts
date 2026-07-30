'use client'

// 현재 유저(/auth/me) 단일 소스. 모듈 캐시로 /me를 페이지당 1회만 부른다
// (헤더·크레딧 배지·게이트가 각자 부르면 중복). 크레딧 소모 작업 뒤 invalidateMe()로 갱신.
import { useEffect, useState } from 'react'

export interface Me {
  email: string
  role: string
  plan: string            // 'free' | 'pro' | 'lab'
  credits: number         // 유료 잔액
  freeDecksUsed: number
  freeDeckLimit: number
  canAuthor: boolean      // 생성 가능(무료=한도 내 / 유료=잔액≥덱단가). 배지 '부족' 표시에 사용
  canExport: boolean
}

let cache: Me | null = null
let inflight: Promise<Me | null> | null = null

function load(): Promise<Me | null> {
  if (cache) return Promise.resolve(cache)
  if (!inflight) {
    inflight = fetch('/api/auth/me', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: Me | null) => { cache = d; return d })
      .catch(() => null)
      .finally(() => { inflight = null })
  }
  return inflight
}

// 크레딧을 쓰는 작업(생성·AI편집·발행) 성공 뒤 호출 → 다음 useMe가 새 잔액을 받는다.
export function invalidateMe() { cache = null }

export function useMe(): Me | null {
  const [me, setMe] = useState<Me | null>(cache)
  useEffect(() => {
    let alive = true
    load().then((d) => { if (alive) setMe(d) })
    return () => { alive = false }
  }, [])
  return me
}
