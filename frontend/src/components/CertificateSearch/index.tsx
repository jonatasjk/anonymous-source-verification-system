import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  ShieldCheck,
  Loader2,
  AlertTriangle,
  BarChart3,
  Clock,
  Bitcoin,
  FileDown,
  Copy,
  Check,
} from 'lucide-react'
import { getCertificateById, certificatePdfUrl } from '@/api/client'
import type { CertificateResponse } from '@/types/certificate'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="text-ink/40 hover:text-ink transition-colors">
      {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
    </button>
  )
}

function ScoreBadge({ score, label }: { score: number; label: string }) {
  const color =
    score >= 75 ? 'text-emerald-700' : score >= 50 ? 'text-amber-700' : 'text-red-700'
  return (
    <div className="flex flex-col items-center bg-surface rounded-lg p-4">
      <span className={`text-3xl font-bold ${color}`}>{score}</span>
      <span className="text-xs text-ink/50 mt-1 text-center">{label}</span>
    </div>
  )
}

function CertificateResult({ cert }: { cert: CertificateResponse }) {
  const { certificate_id, issued_at, evidence_package, timestamp_proofs, analysis, attribution_language } = cert
  const submissionId = cert.submission_id

  return (
    <div className="space-y-6 mt-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <ShieldCheck className="text-brand w-7 h-7" />
            <h2 className="text-xl font-bold">Verification Certificate</h2>
          </div>
          <p className="text-ink/50 font-mono text-sm">{certificate_id}</p>
          <p className="text-ink/40 text-xs mt-1">Issued: {new Date(issued_at).toLocaleString()}</p>
        </div>
        {submissionId && (
          <a
            href={certificatePdfUrl(submissionId)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-card hover:bg-surface-border border border-surface-border text-sm font-medium transition-colors"
          >
            <FileDown className="w-4 h-4" />
            PDF
          </a>
        )}
      </div>

      {/* Confidence scores */}
      <section className="bg-surface-card rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-brand" />
          <h3 className="font-semibold">Evidence Confidence</h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <ScoreBadge score={analysis.overall_confidence} label="Overall" />
          <ScoreBadge score={analysis.consistency_score} label="Consistency" />
          <ScoreBadge score={analysis.corroboration_score} label="Corroboration" />
          <ScoreBadge score={analysis.plausibility_score} label="Plausibility" />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-ink/50">Reliability class:</span>
          <span
            className={`font-bold ${
              analysis.reliability_class === 'HIGH'
                ? 'text-emerald-700'
                : analysis.reliability_class === 'MEDIUM'
                ? 'text-amber-700'
                : 'text-red-700'
            }`}
          >
            {analysis.reliability_class}
          </span>
        </div>
        {analysis.analysis_notes && (
          <p className="text-ink/60 text-sm mt-3">{analysis.analysis_notes}</p>
        )}
        {analysis.red_flags.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-red-700 font-semibold uppercase mb-1">Red flags</p>
            <ul className="text-sm text-ink/60 space-y-1">
              {analysis.red_flags.map((flag, i) => (
                <li key={i} className="flex items-start gap-2">
                  <AlertTriangle className="w-3 h-3 text-red-600 mt-1 flex-shrink-0" />
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Evidence integrity */}
      <section className="bg-surface-card rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="w-5 h-5 text-brand" />
          <h3 className="font-semibold">Evidence Package Integrity</h3>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink/50">Files in package</span>
            <span>{evidence_package.file_count}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-ink/50 flex-shrink-0">Merkle root</span>
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-mono text-xs text-ink/70 truncate">
                {evidence_package.merkle_root}
              </span>
              <CopyButton text={evidence_package.merkle_root} />
            </div>
          </div>
        </div>
      </section>

      {/* RFC 3161 */}
      {timestamp_proofs.rfc3161 && (
        <section className="bg-surface-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-brand" />
            <h3 className="font-semibold">RFC 3161 Timestamp Proof</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-ink/50">TSA</span>
              <span>{timestamp_proofs.rfc3161.tsa}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink/50">Algorithm</span>
              <span>{timestamp_proofs.rfc3161.tsa_cert_algorithm}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink/50">Cert generation</span>
              <span>{timestamp_proofs.rfc3161.tsa_cert_generation}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-ink/50 flex-shrink-0">Token hash</span>
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono text-xs truncate">
                  {timestamp_proofs.rfc3161.token_hash}
                </span>
                <CopyButton text={timestamp_proofs.rfc3161.token_hash} />
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Bitcoin / OTS */}
      {timestamp_proofs.opentimestamps && (
        <section className="bg-surface-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <Bitcoin className="w-5 h-5 text-amber-700" />
            <h3 className="font-semibold">OpenTimestamps (Bitcoin) Proof</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-ink/50">Status</span>
              <span className={timestamp_proofs.opentimestamps.confirmed ? 'text-emerald-700 font-semibold' : 'text-ink/50'}>
                {timestamp_proofs.opentimestamps.confirmed
                  ? `Confirmed — block ${timestamp_proofs.opentimestamps.bitcoin_block}`
                  : 'Pending Bitcoin confirmation (~10 min)'}
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Attribution language */}
      {attribution_language.length > 0 && (
        <section className="bg-surface-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-brand" />
            <h3 className="font-semibold">Publication Attribution</h3>
          </div>
          <ul className="space-y-2">
            {attribution_language.map((sentence, i) => (
              <li key={i} className="text-sm text-ink/80 leading-relaxed border-l-2 border-brand/30 pl-3">
                {sentence}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Disclaimer */}
      <p className="text-xs text-ink/40 leading-relaxed border-t border-surface-border pt-4">
        This certificate attests to provenance and integrity, not to the truth of the underlying allegations.
      </p>
    </div>
  )
}

export default function CertificateSearch() {
  const [searchParams, setSearchParams] = useSearchParams()
  const qParam = searchParams.get('q') ?? ''
  const [input, setInput] = useState(qParam)

  // Sync input with URL param when navigating directly to /search?q=...
  useEffect(() => {
    setInput(qParam)
  }, [qParam])

  const {
    data: cert,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['certificateById', qParam],
    queryFn: () => getCertificateById(qParam),
    enabled: qParam.length > 0,
    retry: false,
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = input.trim().toUpperCase()
    if (!trimmed) return
    setSearchParams({ q: trimmed })
  }

  const is404 = isError && (error as { response?: { status: number } })?.response?.status === 404

  return (
    <div className="px-8 py-10 max-w-3xl w-full">
      <div className="flex items-center gap-3 mb-8">
        <Search className="text-brand w-7 h-7" />
        <h1 className="text-2xl font-bold tracking-tight">Search Certificate</h1>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="CERT-2026-42C7E2"
          className="flex-1 bg-surface-card border border-surface-border rounded-xl px-4 py-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-brand/40"
          spellCheck={false}
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="px-5 py-3 bg-brand text-white rounded-xl text-sm font-semibold hover:bg-brand-dark disabled:opacity-40 transition-colors"
        >
          Search
        </button>
      </form>

      <p className="text-xs text-ink/40 mt-2">
        You can also share a direct link:{' '}
        <span className="font-mono">/search?q=CERT-2026-XXXXXX</span>
      </p>

      {/* States */}
      {isLoading && (
        <div className="flex items-center gap-3 mt-10 text-ink/50">
          <Loader2 className="w-5 h-5 animate-spin text-brand" />
          <span className="text-sm">Looking up certificate…</span>
        </div>
      )}

      {isError && (
        <div className="mt-10 flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl p-5">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">
              {is404 ? 'Certificate not found' : 'Lookup failed'}
            </p>
            <p className="text-xs text-red-600 mt-0.5">
              {is404
                ? `No certificate with ID "${qParam}" exists in the system.`
                : 'Could not reach the backend. Check your connection and try again.'}
            </p>
          </div>
        </div>
      )}

      {cert && <CertificateResult cert={cert} />}
    </div>
  )
}
