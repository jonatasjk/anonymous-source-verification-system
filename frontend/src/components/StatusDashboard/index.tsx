import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ShieldCheck, Clock, Search, Award, AlertCircle, Loader2 } from 'lucide-react'
import { useSubmissionStatus } from '@/hooks/useSubmission'
import type { SubmissionStatus } from '@/types/certificate'

const STEPS: { status: SubmissionStatus; label: string; icon: typeof Clock }[] = [
  { status: 'INGESTED',    label: 'Files ingested & Merkle tree built',   icon: ShieldCheck },
  { status: 'TIMESTAMPED', label: 'RFC 3161 + OpenTimestamps anchored',   icon: Clock       },
  { status: 'ANALYZED',   label: 'LLM evidence analysis complete',         icon: Search      },
  { status: 'COMPLETE',   label: 'Verification certificate issued',         icon: Award       },
]

const STATUS_ORDER: SubmissionStatus[] = ['INGESTED', 'TIMESTAMPED', 'ANALYZED', 'COMPLETE']

function stepIndex(status: SubmissionStatus) {
  return STATUS_ORDER.indexOf(status)
}

export default function StatusDashboard() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isError } = useSubmissionStatus(id)

  useEffect(() => {
    if (data?.status === 'COMPLETE') {
      const t = setTimeout(() => navigate(`/certificate/${id}`), 1500)
      return () => clearTimeout(t)
    }
  }, [data?.status, id, navigate])

  const currentIndex = data ? stepIndex(data.status) : -1

  return (
    <div className="flex-1 text-ink flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg space-y-8">
        <div>
          <h1 className="text-2xl font-bold">Processing status</h1>
          <p className="text-ink/50 font-mono text-xs mt-1 break-all">{id}</p>
        </div>

        {isError && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            Unable to retrieve status. Check your submission ID and try again.
          </div>
        )}

        <ol className="space-y-4">
          {STEPS.map((step, i) => {
            const done = currentIndex >= i
            const active = currentIndex === i - 1
            const Icon = step.icon

            return (
              <li
                key={step.status}
                className={`flex items-center gap-4 p-4 rounded-xl border transition-colors ${
                  done
                    ? 'border-brand bg-brand/5 text-ink'
                    : active
                    ? 'border-ink/30 bg-surface-card'
                    : 'border-surface-border bg-surface text-ink/30'
                }`}
              >
                <div className={`flex-shrink-0 ${done ? 'text-brand' : 'text-ink/30'}`}>
                  {!done && active ? (
                    <Loader2 className="w-6 h-6 animate-spin text-ink/40" />
                  ) : (
                    <Icon className="w-6 h-6" />
                  )}
                </div>
                <span className="text-sm font-medium">{step.label}</span>
              </li>
            )
          })}
        </ol>

        {data?.status === 'COMPLETE' && (
          <p className="text-center text-emerald-700 text-sm animate-pulse">
            Certificate ready — redirecting…
          </p>
        )}

        {!data && !isError && (
          <div className="flex items-center justify-center gap-2 text-ink/50 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            Connecting…
          </div>
        )}
      </div>
    </div>
  )
}
