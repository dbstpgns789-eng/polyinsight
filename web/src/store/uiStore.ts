'use client'

import { create } from 'zustand'

interface UiState {
  uploadModalOpen: boolean
  exportModalOpen: boolean
  activeJobId: string | null
  openUploadModal: () => void
  closeUploadModal: () => void
  openExportModal: (jobId: string) => void
  closeExportModal: () => void
  setActiveJobId: (id: string) => void
}

const useUiStore = create<UiState>((set) => ({
  uploadModalOpen: false,
  exportModalOpen: false,
  activeJobId: null,

  openUploadModal: () => set({ uploadModalOpen: true }),
  closeUploadModal: () => set({ uploadModalOpen: false }),

  openExportModal: (jobId) => set({ exportModalOpen: true, activeJobId: jobId }),
  closeExportModal: () => set({ exportModalOpen: false }),

  setActiveJobId: (id) => set({ activeJobId: id }),
}))

export default useUiStore
