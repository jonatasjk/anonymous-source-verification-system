import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Award, Loader2, AlertTriangle, ChevronRight } from 'lucide-react'
import { listCertificates } from '@/api/client'

const CLASS_STYLES: Record<string, string> = {
  HIGH:   'bg-emerald-100 text-emerald-800',
  MEDIUM: 'bg-amber-100 text-amber-800',
  LOW:    'bg-red-100 text-red-700',
}

export default function CertificatesList() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['certificates'],
    queryFn: listCertificates,
    staleTime: 30_000,
  })

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex-1 flex items-center justify-center px-4">
        <div className="text-center">
          <AlertTriangle className="mx-auto mb-4 text-red-600 w-10 h-10" />
          <p className="text-lg font-medium">Failed to load certificates</p>
          <p className="text-ink/50 text-sm mt-1">Check the backend connection and try again.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-8 py-10 max-w-4xl w-full">
      <div className="flex items-center gap-3 mb-8">
        <Award className="text-brand w-7 h-7" />
        <h1 className="text-2xl font-bold tracking-tight">Certificates</h1>
      </div>

      {data?.length === 0 ? (
        <p className="text-ink/50 text-sm">No certificates have been issued yet.</p>
      ) : (
        <div className="space-y-3">
          {data?.map((cert) => (
            <Link
              key={cert.certificate_id}
              to={`/certificate/${cert.submission_id}`}
              className="flex items-center justify-between bg-surface-card border border-surface-border rounded-xl px-6 py-4 hover:border-brand/50 hover:shadow-sm transition-all group"
            >
              <div>
                <p className="font-mono text-sm font-semibold text-brand group-hover:text-brand-light transition-colors">
                  {cert.certificate_id}
                </p>
                <p className="text-ink/50 text-xs mt-0.5">
                  {new Date(cert.issued_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-5">
                <div className="text-right">
                  <p className="text-xs text-ink/40 mb-0.5">Confidence</p>
                  <p className="font-bold text-lg leading-none">
                    {cert.overall_confidence}
                    <span className="text-xs text-ink/40 font-normal">/100</span>
                  </p>
                </div>

                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                    CLASS_STYLES[cert.reliability_class] ?? 'bg-surface-border text-ink/60'
                  }`}
                >
                  {cert.reliability_class}
                </span>

                <ChevronRight className="w-4 h-4 text-ink/30 group-hover:text-ink/60 transition-colors" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
