'use client'

import { create } from 'zustand'

interface UiState {
  exportModalOpen: boolean
  activeJobId: string | null
  openExportModal: (jobId: string) => void
  closeExportModal: () => void
  setActiveJobId: (id: string) => void
}

const useUiStore = create<UiState>((set) => ({
  exportModalOpen: false,
  activeJobId: null,

  openExportModal: (jobId) => set({ exportModalOpen: true, activeJobId: jobId }),
  closeExportModal: () => set({ exportModalOpen: false }),

  setActiveJobId: (id) => set({ activeJobId: id }),
}))

export default useUiStore
