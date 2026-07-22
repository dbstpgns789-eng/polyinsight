import axios from 'axios'
import type { StockImageResult } from '@/types/editor'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail
    const message = typeof detail === 'object' ? detail.message : detail
    // ★status/code를 보존한다 — 402(플랜 벽)와 429(브루트포스)를 구분해야 페이월을 정확히 띄운다.
    const wrapped = new Error(message || err.message) as Error & { status?: number; code?: string }
    wrapped.status = err.response?.status
    if (typeof detail === 'object' && detail?.code) wrapped.code = detail.code
    return Promise.reject(wrapped)
  }
)

// uploadPdf(구 POST /api/upload → run_pipeline)는 L0(2026-07-09)에서 삭제.
// 저작 진입은 uploadDeck(/api/deck/upload) 하나뿐.

export const getStatus = (jobId: string) => api.get(`/status/${jobId}`)

// ── 단일 저작 덱 (헌법 v3.0) ──────────────────────────────────────────────
export const uploadDeck = (file: File, cardCount: number, persona?: string, styleDirection?: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('card_count', String(cardCount))
  if (persona) form.append('persona', persona)
  if (styleDirection) form.append('style_direction', styleDirection)
  return api.post('/deck/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export const getDeck = (jobId: string) => api.get(`/deck/${jobId}`)

// 덱 이미지 자산 업로드(멀티파트) → {assetId, url}. 렌더시 data URI 인라인 전제(저장 HTML엔 url만).
export const uploadDeckAsset = (jobId: string, file: File, sourceType = 'upload-owned') => {
  const form = new FormData()
  form.append('file', file)
  form.append('source_type', sourceType)
  return api.post(`/deck/${jobId}/assets`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export const getDeckAssetUrl = (jobId: string, assetId: string) =>
  `/api/deck/${jobId}/assets/${assetId}`

// 편집(직접조작) 저장 → 재검증 + PNG 재렌더. Playwright 대기 위해 타임아웃 확대.
export const patchDeck = (jobId: string, html: string) =>
  api.patch(`/deck/${jobId}`, { html }, { timeout: 120_000 })

// 자연어 편집 (유료 LLM). 응답에 새 html·verify 포함.
export const nlPatchDeck = (jobId: string, instruction: string) =>
  api.post(`/deck/${jobId}/nlpatch`, { instruction }, { timeout: 180_000 })

export interface NLTarget { eid?: string; cardIndex?: number; quotedText?: string }

// AI 편집 제안 (미커밋, 유료 LLM 1콜). html=캔버스 라이브 serialize 결과. 응답 {html, verify}.
export const nlProposeDeck = (
  jobId: string, instruction: string, html: string, target?: NLTarget,
) => api.post(`/deck/${jobId}/nlpatch/propose`, { instruction, html, target }, { timeout: 180_000 })

export const exportDeck = (jobId: string) =>
  api.post(`/deck/${jobId}/export`, {}, { timeout: 120_000 })

// Phase 0 반자동 발행 — 계약면(스펙 2026-07-21). 실행 세션이 lazy+캐시로 생성.
// 첫 GET은 생성(수 초), 이후는 캐시. regen=true면 재생성(백엔드가 cap).
export interface DeckCaption { caption: string; hashtags: string[] }
export const getDeckCaption = (jobId: string, regen = false) =>
  api.get<DeckCaption>(`/deck/${jobId}/caption${regen ? '?regen=1' : ''}`, { timeout: 60_000 })

// v: 편집 저장 후 재렌더된 PNG 캐시 무력화용 버전(보통 updatedAt/저장 카운트).
export const getDeckCardUrl = (jobId: string, cardNum: number, v?: number | string) =>
  `/api/deck/${jobId}/cards/${cardNum}${v != null ? `?v=${v}` : ''}`

export const getCards = (jobId: string) => api.get(`/cards/${jobId}`)

export const patchCards = (jobId: string, cardData: unknown) =>
  api.patch(`/cards/${jobId}/data`, { cardData })

export const getProjects = (params: Record<string, unknown> = {}) =>
  api.get('/projects', { params })

export const getStats = () => api.get('/projects/stats')

export const renameJob = (jobId: string, title: string) =>
  api.patch(`/jobs/${jobId}`, { title })

export const deleteJob = (jobId: string) => api.delete(`/jobs/${jobId}`)

function parseFilename(cd?: string): string | null {
  if (!cd) return null
  const star = /filename\*=UTF-8''([^;]+)/i.exec(cd)
  if (star) return decodeURIComponent(star[1])
  const plain = /filename="?([^";]+)"?/i.exec(cd)
  return plain ? plain[1] : null
}

/** 단일 카드를 즉석 렌더한 PNG를 받아 브라우저 다운로드 트리거. */
export const downloadCard = async (jobId: string, cardNum: number) => {
  const res = await api.get(`/cards/${jobId}/download/${cardNum}`, {
    responseType: 'blob',
    timeout: 60000,
  })
  const cd = res.headers['content-disposition'] as string | undefined
  const fname = parseFilename(cd) ?? `card_${String(cardNum).padStart(2, '0')}.png`
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fname
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const getExportDownloadUrl = (exportId: string) =>
  `/api/export/${exportId}/download`

export const getCardImageUrl = (jobId: string, cardNum: number) =>
  `/api/cards/${jobId}/image/${cardNum}`

export const triggerExport = (jobId: string) =>
  api.post(`/cards/${jobId}/export`, {}, { timeout: 180_000 })  // Playwright 렌더링 대기 (최대 3분)

export const searchStockImages = async (q: string): Promise<StockImageResult[]> => {
  const res = await api.get('/images/search', { params: { q } })
  return res.data.results as StockImageResult[]
}

export default api
