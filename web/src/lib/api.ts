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

export const getExportDownloadUrl = (exportId: string) =>
  `/api/export/${exportId}/download`

export const getCardImageUrl = (jobId: string, cardNum: number) =>
  `/api/cards/${jobId}/image/${cardNum}`

export const triggerExport = (jobId: string) =>
  api.post(`/cards/${jobId}/export`, {}, { timeout: 180_000 })  // Playwright 렌더링 대기 (최대 3분)

export default api
