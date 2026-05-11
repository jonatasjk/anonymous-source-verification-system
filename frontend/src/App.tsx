import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import UploadWizard from '@/components/UploadWizard'
import StatusDashboard from '@/components/StatusDashboard'
import CertificateViewer from '@/components/CertificateViewer'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<UploadWizard />} />
          <Route path="/status/:id" element={<StatusDashboard />} />
          <Route path="/certificate/:id" element={<CertificateViewer />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
