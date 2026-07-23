import { describe, it, expect, vi, beforeEach } from 'vitest'

// ★vi.mock은 파일 최상단으로 호이스트됨 → mock 함수도 vi.hoisted로 먼저 초기화해야
//   factory 안에서 접근 가능("Cannot access mockGet before initialization" 방지).
const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

// axios.create()가 반환하는 인스턴스의 get/post를 목킹 (api.ts는 모듈 로드 시 interceptors 등록)
vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      post: mockPost,
      interceptors: { response: { use: vi.fn() } },
    }),
  },
}))

import { getInstagramStatus, publishInstagram, instagramConnectUrl } from '../api'

beforeEach(() => {
  mockGet.mockReset()
  mockPost.mockReset()
})

describe('instagramConnectUrl', () => {
  it('IG OAuth 시작 라우트를 가리킨다', () => {
    expect(instagramConnectUrl()).toBe('/api/auth/oauth/instagram/start')
  })
})

describe('publishInstagram', () => {
  it('성공 시 permalink 반환', async () => {
    mockPost.mockResolvedValue({ data: { permalink: 'https://instagram.com/p/X' } })
    expect(await publishInstagram('j1')).toEqual({ ok: true, permalink: 'https://instagram.com/p/X' })
  })

  it('실패 시 백엔드 메시지를 error로 반환', async () => {
    mockPost.mockRejectedValue(new Error('크레딧이 부족합니다.'))
    const r = await publishInstagram('j1')
    expect(r.ok).toBe(false)
    expect((r as { error: string }).error).toBe('크레딧이 부족합니다.')
  })
})

describe('getInstagramStatus', () => {
  it('에러 시 미연동으로 폴백', async () => {
    mockGet.mockRejectedValue(new Error('500'))
    expect(await getInstagramStatus()).toEqual({ connected: false, username: null })
  })

  it('성공 시 서버 상태 반환', async () => {
    mockGet.mockResolvedValue({ data: { connected: true, username: 'shop' } })
    expect(await getInstagramStatus()).toEqual({ connected: true, username: 'shop' })
  })
})
