'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import PostHogProvider from '@/components/analytics/PostHogProvider'

export default function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { retry: 1, refetchOnWindowFocus: false },
    },
  }))

  return (
    <QueryClientProvider client={qc}>
      <PostHogProvider>{children}</PostHogProvider>
    </QueryClientProvider>
  )
}
