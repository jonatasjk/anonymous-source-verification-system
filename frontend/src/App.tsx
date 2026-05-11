import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import LandingPage from '@/components/LandingPage'
import UploadWizard from '@/components/UploadWizard'
import StatusDashboard from '@/components/StatusDashboard'
import CertificateViewer from '@/components/CertificateViewer'
import CertificatesList from '@/components/CertificatesList'
import CertificateSearch from '@/components/CertificateSearch'

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
          <Route path="/" element={<LandingPage />} />
          <Route element={<Layout />}>
            <Route path="/submit" element={<UploadWizard />} />
            <Route path="/status/:id" element={<StatusDashboard />} />
            <Route path="/certificate/:id" element={<CertificateViewer />} />
            <Route path="/certificates" element={<CertificatesList />} />
            <Route path="/search" element={<CertificateSearch />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
