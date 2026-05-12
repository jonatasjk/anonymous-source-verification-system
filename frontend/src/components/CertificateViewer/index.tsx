import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  ShieldCheck,
  Clock,
  Bitcoin,
  BarChart3,
  Copy,
  Check,
  FileDown,
  AlertTriangle,
  Loader2,
} from 'lucide-react'
import { useSubmissionStatus, useCertificate } from '@/hooks/useSubmission'
import { certificatePdfUrl } from '@/api/client'

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
    <div className="flex flex-col items-center bg-surface-card rounded-lg p-4">
      <span className={`text-3xl font-bold ${color}`}>{score}</span>
      <span className="text-xs text-ink/50 mt-1 text-center">{label}</span>
    </div>
  )
}

export default function CertificateViewer() {
  const { id } = useParams<{ id: string }>()
  const { data: statusData } = useSubmissionStatus(id)
  const isComplete = statusData?.status === 'COMPLETE'
  const { data: cert, isLoading, isError } = useCertificate(id, isComplete)

  if (isLoading || !cert) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex-1 text-ink flex items-center justify-center px-4">
        <div className="text-center">
          <AlertTriangle className="mx-auto mb-4 text-red-600 w-10 h-10" />
          <p className="text-lg font-medium">Certificate not found</p>
          <p className="text-ink/50 text-sm mt-2">
            Processing may still be underway or the ID is invalid.
          </p>
        </div>
      </div>
    )
  }

  const { certificate_id, issued_at, evidence_package, timestamp_proofs, analysis, attribution_language } = cert

  return (
    <div className="flex-1 text-ink px-4 py-12">
      <div className="max-w-3xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <ShieldCheck className="text-brand w-7 h-7" />
              <h1 className="text-2xl font-bold">Verification Certificate</h1>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-ink/50 font-mono text-sm">{certificate_id}</p>
              <CopyButton text={certificate_id} />
            </div>
            <p className="text-ink/40 text-xs mt-1">Issued: {new Date(issued_at).toLocaleString()}</p>
          </div>
          <a
            href={certificatePdfUrl(id!)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-card hover:bg-surface-border border border-surface-border text-sm font-medium transition-colors"
          >
            <FileDown className="w-4 h-4" />
            PDF
          </a>
        </div>

        {/* Confidence scores */}
        <section className="bg-surface-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-brand" />
            <h2 className="font-semibold">Evidence Confidence</h2>
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

        {/* Merkle root */}
        <section className="bg-surface-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-5 h-5 text-brand" />
            <h2 className="font-semibold">Evidence Package Integrity</h2>
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
              <h2 className="font-semibold">RFC 3161 Timestamp Proof</h2>
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
              <div className="flex justify-between">
                <span className="text-ink/50">Timestamp</span>
                <span>{new Date(timestamp_proofs.rfc3161.timestamp).toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-ink/50 flex-shrink-0">Token hash</span>
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-xs text-ink/70 truncate">
                    {timestamp_proofs.rfc3161.token_hash}
                  </span>
                  <CopyButton text={timestamp_proofs.rfc3161.token_hash} />
                </div>
              </div>
            </div>
          </section>
        )}

        {/* OpenTimestamps */}
        {timestamp_proofs.opentimestamps && (
          <section className="bg-surface-card rounded-xl p-6">
            <div className="flex items-center gap-2 mb-3">
              <Bitcoin className="w-5 h-5 text-amber-700" />
              <h2 className="font-semibold">OpenTimestamps (Bitcoin) Proof</h2>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-ink/50">Status</span>
                <span
                  className={
                    timestamp_proofs.opentimestamps.confirmed ? 'text-emerald-700' : 'text-amber-700'
                  }
                >
                  {timestamp_proofs.opentimestamps.confirmed
                    ? `Confirmed — block ${timestamp_proofs.opentimestamps.bitcoin_block}`
                    : 'Pending Bitcoin confirmation (~10 min)'}
                </span>
              </div>
              {timestamp_proofs.opentimestamps.block_timestamp && (
                <div className="flex justify-between">
                  <span className="text-ink/50">Block time</span>
                  <span>
                    {new Date(timestamp_proofs.opentimestamps.block_timestamp).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Attribution language */}
        <section className="bg-surface-card rounded-xl p-6 space-y-4">
          <h2 className="font-semibold">Attribution Language</h2>
          {attribution_language.map((line, i) => (
            <div key={i} className="flex items-start gap-3">
              <p className="text-sm text-ink/80 flex-1">{line}</p>
              <CopyButton text={line} />
            </div>
          ))}
        </section>

        {/* Caveat */}
        <p className="text-center text-xs text-ink/60 pb-8">
          This certificate attests to provenance and integrity, not to the truth of the
          underlying allegations. The confidence score is an editorial aid, not a verdict.
        </p>
      </div>
    </div>
  )
}
