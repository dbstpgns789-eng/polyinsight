import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err.response?.data?.detail
    const message = typeof detail === 'object' ? detail.message : detail
    return Promise.reject(new Error(message || err.message))
  }
)

export const uploadPdf = (file: File, cardCount: number) => {
  const form = new FormData()
  form.append('file', file)
  form.append('card_count', String(cardCount))
  return api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export const getStatus = (jobId: string) => api.get(`/status/${jobId}`)

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

export default api
