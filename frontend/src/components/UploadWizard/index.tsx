import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, X, ShieldCheck, Loader2 } from 'lucide-react'
import { submitFiles } from '@/api/client'

const MAX_FILES = 20
const MAX_SIZE = 50 * 1024 * 1024 // 50 MB

type Step = 1 | 2 | 3

export default function UploadWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>(1)
  const [files, setFiles] = useState<File[]>([])
  const [submissionId, setSubmissionId] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onDrop = useCallback((accepted: File[]) => {
    setError('')
    setFiles((prev) => {
      const merged = [...prev, ...accepted]
      if (merged.length > MAX_FILES) {
        setError(`Maximum ${MAX_FILES} files allowed.`)
        return prev
      }
      return merged
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: MAX_SIZE,
    multiple: true,
    onDropRejected: (rejections) => {
      const reasons = rejections.map((r) => r.errors[0].message).join('; ')
      setError(reasons)
    },
  })

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError('Please add at least one file.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const result = await submitFiles(files)
      setSubmissionId(result.submission_id)
      setStep(3)
    } catch (err) {
      setError('Submission failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface text-ink flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <ShieldCheck className="text-brand w-8 h-8" />
          <h1 className="text-2xl font-bold tracking-tight">
            Anonymous Source Verification
          </h1>
        </div>

        {/* Step indicator */}
        <div className="flex gap-4 mb-8">
          {(['Select Files', 'Review', 'Confirmation'] as const).map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
                  step > i + 1
                    ? 'bg-brand text-white'
                    : step === i + 1
                    ? 'bg-brand text-white'
                    : 'bg-surface-card text-ink/40'
                }`}
              >
                {i + 1}
              </div>
              <span className={step === i + 1 ? 'text-ink' : 'text-ink/40'}>
                {label}
              </span>
              {i < 2 && <div className="w-8 h-px bg-surface-border" />}
            </div>
          ))}
        </div>

        {/* Step 1 — Drop zone */}
        {step === 1 && (
          <div className="space-y-6">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
                isDragActive
                  ? 'border-brand bg-brand/5'
                  : 'border-surface-border hover:border-ink/40'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="mx-auto mb-4 text-ink/40 w-10 h-10" />
              <p className="text-lg font-medium">
                {isDragActive ? 'Drop files here…' : 'Drag & drop evidence files'}
              </p>
              <p className="text-sm text-ink/50 mt-2">
                or click to browse &mdash; max {MAX_FILES} files, 50 MB each
              </p>
            </div>

            {files.length > 0 && (
              <ul className="space-y-2">
                {files.map((f, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between bg-surface-card rounded-lg px-4 py-2"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="w-4 h-4 text-ink/50 flex-shrink-0" />
                      <span className="text-sm truncate">{f.name}</span>
                      <span className="text-xs text-ink/40 flex-shrink-0">
                        {(f.size / 1024).toFixed(0)} KB
                      </span>
                    </div>
                    <button onClick={() => removeFile(i)} className="text-ink/40 hover:text-red-600 ml-2">
                      <X className="w-4 h-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {error && <p className="text-red-600 text-sm">{error}</p>}

            <button
              disabled={files.length === 0}
              onClick={() => setStep(2)}
              className="w-full py-3 rounded-lg bg-brand hover:bg-brand-dark text-white disabled:opacity-40 disabled:cursor-not-allowed font-semibold transition-colors"
            >
              Continue →
            </button>
          </div>
        )}

        {/* Step 2 — Review */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="bg-surface-card rounded-xl p-6 space-y-4">
              <h2 className="font-semibold text-lg">Review your submission</h2>
              <p className="text-sm text-ink/60">
                {files.length} file{files.length !== 1 ? 's' : ''} selected. No identifying
                information is collected — files are stored encrypted with hashed filenames only.
              </p>
              <ul className="divide-y divide-surface-border">
                {files.map((f, i) => (
                  <li key={i} className="py-2 flex justify-between text-sm">
                    <span className="text-ink">{f.name}</span>
                    <span className="text-ink/50">{(f.size / 1024).toFixed(0)} KB</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900">
              <strong>Privacy reminder:</strong> Once submitted, files cannot be retrieved
              or deleted. Do not include documents that could uniquely identify you
              unless you intend to disclose them.
            </div>

            {error && <p className="text-red-600 text-sm">{error}</p>}

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 rounded-lg border border-surface-border hover:border-ink/40 text-ink font-semibold transition-colors"
              >
                ← Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex-1 py-3 rounded-lg bg-brand hover:bg-brand-dark text-white disabled:opacity-60 font-semibold transition-colors flex items-center justify-center gap-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? 'Submitting…' : 'Submit securely'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3 — Confirmation */}
        {step === 3 && (
          <div className="space-y-6 text-center">
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8">
              <ShieldCheck className="mx-auto mb-4 text-emerald-600 w-12 h-12" />
              <h2 className="text-xl font-bold mb-2">Submission received</h2>
              <p className="text-ink/60 text-sm mb-6">
                Save your submission ID. You will need it to retrieve your certificate.
              </p>
              <div className="bg-surface-border rounded-lg px-6 py-3 font-mono text-brand text-sm break-all">
                {submissionId}
              </div>
            </div>

            <button
              onClick={() => navigate(`/status/${submissionId}`)}
              className="w-full py-3 rounded-lg bg-brand hover:bg-brand-dark text-white font-semibold transition-colors"
            >
              Track processing status →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
