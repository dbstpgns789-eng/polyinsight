import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<div className="p-8 text-2xl">Dashboard — WIP</div>} />
          <Route path="/editor/:jobId" element={<div className="p-8 text-2xl">Editor — WIP</div>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
