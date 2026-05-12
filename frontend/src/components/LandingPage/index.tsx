import { Link } from 'react-router-dom'
import {
  ShieldCheck,
  Upload,
  Clock,
  BarChart3,
  Award,
  ArrowRight,
  Lock,
  Bitcoin,
  FileText,
  Search,
} from 'lucide-react'
const certPdf = new URL('../../assets/CERT-2026-590845.pdf', import.meta.url).href

const steps = [
  {
    icon: Upload,
    title: 'Submit Evidence',
    desc: 'Upload documents, images, videos or any files from an anonymous source. No IP address, name or email is ever stored.',
  },
  {
    icon: Clock,
    title: 'Cryptographic Timestamping',
    desc: 'Before any analysis touches the files, ASVS seals the package with an RFC 3161 timestamp and anchors it to the Bitcoin blockchain via OpenTimestamps.',
  },
  {
    icon: BarChart3,
    title: 'LLM Evidence Analysis',
    desc: 'GPT-4o scores the package across three dimensions — consistency, corroboration, and plausibility — and flags red flags or contradictions.',
  },
  {
    icon: Award,
    title: 'Verification Certificate',
    desc: 'A signed certificate is issued with publication-ready attribution language and a downloadable PDF, independently verifiable by any third party.',
  },
]

const features = [
  {
    icon: Lock,
    title: 'Source anonymity preserved',
    desc: 'Only SHA-256 hashes of filenames are stored. Zero PII.',
  },
  {
    icon: Clock,
    title: 'Tamper-evident timestamps',
    desc: 'RFC 3161 + Bitcoin blockchain anchoring before any LLM reads the files.',
  },
  {
    icon: Bitcoin,
    title: 'Bitcoin-backed proof',
    desc: 'OpenTimestamps confirmation provides decentralised, unforgeable time-of-receipt proof.',
  },
  {
    icon: FileText,
    title: 'Publication-ready language',
    desc: 'Per-claim attribution sentences with assertive, hedged or alleged tone — ready to paste into your story.',
  },
  {
    icon: Search,
    title: 'Publicly verifiable',
    desc: 'Anyone can verify a certificate ID against the Merkle root without accessing the original files.',
  },
  {
    icon: ShieldCheck,
    title: 'Provenance, not truth',
    desc: 'The certificate attests to integrity and time-of-receipt — never to the truth of allegations.',
  },
]

const sampleAttribution = [
  'Documents reviewed by ASVS (cert CERT-2026-590845) show internal communications that assertively indicate the procurement process was bypassed for contracts awarded in Q3 2024.',
  'The evidence package allegedly contains financial records suggesting off-the-books payments totalling €2.3 million between April and September 2024.',
  'Supporting materials hedgedly corroborate accounts from multiple sources regarding the involvement of senior officials in the approval chain.',
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-surface text-ink flex flex-col">

      {/* ── NAV ── */}
      <header className="sticky top-0 z-10 bg-brand/95 backdrop-blur-sm border-b border-brand-dark shadow-sm">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <ShieldCheck className="w-6 h-6 text-white/90 group-hover:text-white transition-colors" />
            <span className="font-bold tracking-tight text-white text-lg group-hover:text-white/90 transition-colors">ASVS</span>
            <span className="text-white/40 text-sm hidden sm:block group-hover:text-white/60 transition-colors">
              Anonymous Source Verification System
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Link
              to="/certificates"
              className="text-sm text-white/70 hover:text-white transition-colors hidden sm:block"
            >
              Certificates
            </Link>
            <Link
              to="/search"
              className="text-sm text-white/70 hover:text-white transition-colors hidden sm:block"
            >
              Verify
            </Link>
            <Link
              to="/submit"
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-white text-brand font-semibold text-sm hover:bg-surface transition-colors"
            >
              Submit Evidence
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* ── HERO ── */}
      <section className="relative overflow-hidden bg-brand text-white py-24 px-6">
        {/* ── HERO BACKGROUND ── */}
        <div className="absolute inset-0 pointer-events-none select-none overflow-hidden" aria-hidden="true">

          {/* 1. Film grain — tactile texture */}
          <svg className="absolute inset-0 w-full h-full opacity-[0.07]" xmlns="http://www.w3.org/2000/svg">
            <filter id="hero-noise">
              <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="4" stitchTiles="stitch" />
              <feColorMatrix type="saturate" values="0" />
            </filter>
            <rect width="100%" height="100%" filter="url(#hero-noise)" />
          </svg>

          {/* 2. Dot matrix grid */}
          <svg className="absolute inset-0 w-full h-full opacity-[0.11]" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="hero-dots" x="0" y="0" width="36" height="36" patternUnits="userSpaceOnUse">
                <circle cx="1" cy="1" r="1" fill="white" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#hero-dots)" />
          </svg>

          {/* 3. Warm deep centre glow */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_90%_at_50%_30%,rgba(107,18,40,0.60),transparent)]" />

          {/* 4. Edge vignette — frames the section with depth */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_95%_80%_at_50%_50%,transparent_48%,rgba(25,4,10,0.80))]" />

          {/* 5. Top hairline */}
          <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />

          {/* 6. Left ambient bleed */}
          <div className="absolute -left-40 top-1/2 -translate-y-1/2 w-[420px] h-[420px] rounded-full bg-brand-light/25 blur-[100px]" />

          {/* 7. Cryptographic seal — right side */}
          <div className="absolute right-0 sm:right-[5%] lg:right-[9%] top-1/2 -translate-y-1/2 w-[300px] h-[300px]">
            {/* pulsing glow behind the seal */}
            <div
              className="absolute inset-0 rounded-full bg-brand-light/20 blur-[55px] animate-pulse"
              style={{ animationDuration: '4s' }}
            />
            <svg
              viewBox="-150 -150 300 300"
              className="relative w-full h-full opacity-[0.18]"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* concentric rings */}
              <circle cx="0" cy="0" r="140" fill="none" stroke="white" strokeWidth="1.5" />
              <circle cx="0" cy="0" r="110" fill="none" stroke="white" strokeWidth="0.8" />
              <circle cx="0" cy="0" r="82"  fill="none" stroke="white" strokeWidth="0.8" />
              <circle cx="0" cy="0" r="58"  fill="none" stroke="white" strokeWidth="1.0" />
              <circle cx="0" cy="0" r="36"  fill="none" stroke="white" strokeWidth="0.8" />
              <circle cx="0" cy="0" r="18"  fill="none" stroke="white" strokeWidth="1.2" />
              {/* tick marks on outer ring */}
              {Array.from({ length: 36 }, (_, i) => {
                const a = (i / 36) * Math.PI * 2
                const major = i % 3 === 0
                const r0 = major ? 125 : 133
                return (
                  <line
                    key={i}
                    x1={Math.cos(a) * r0} y1={Math.sin(a) * r0}
                    x2={Math.cos(a) * 140} y2={Math.sin(a) * 140}
                    stroke="white" strokeWidth={major ? 1.5 : 0.7}
                  />
                )
              })}
              {/* dashed crosshairs */}
              <line x1="-148" y1="0" x2="148" y2="0" stroke="white" strokeWidth="0.5" strokeDasharray="3 9" />
              <line x1="0" y1="-148" x2="0" y2="148" stroke="white" strokeWidth="0.5" strokeDasharray="3 9" />
              {/* diagonal guides (very faint) */}
              <line x1="-104" y1="-104" x2="104" y2="104" stroke="white" strokeWidth="0.35" opacity="0.4" />
              <line x1="104" y1="-104" x2="-104" y2="104" stroke="white" strokeWidth="0.35" opacity="0.4" />
              {/* centre target */}
              <circle cx="0" cy="0" r="7" fill="none" stroke="white" strokeWidth="1.5" />
              <circle cx="0" cy="0" r="2.5" fill="white" opacity="0.9" />
            </svg>
          </div>

          {/* 8. Subtle beacon ring (centre-right, animates) */}
          <div className="absolute right-[calc(5%+134px)] sm:right-[calc(9%+134px)] top-1/2 -translate-y-1/2 w-6 h-6 rounded-full border border-white/30 animate-ping" style={{ animationDuration: '3s' }} />

        </div>
        <div className="relative max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-1.5 text-sm mb-8">
            <ShieldCheck className="w-4 h-4" />
            AI-powered evidence verification
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight leading-tight mb-6">
            Prove when you received it.
            <br />
            <span className="text-white/60">Before anyone questions it.</span>
          </h1>
          <p className="text-white/70 text-lg leading-relaxed max-w-2xl mx-auto mb-10">
            ASVS timestamps anonymous evidence packages on the Bitcoin blockchain before any
            analysis, then issues a cryptographically verifiable certificate with publication-ready
            attribution language — protecting both the journalist and the source.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/submit"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-white text-brand font-bold text-base hover:bg-surface transition-colors"
            >
              <Upload className="w-5 h-5" />
              Submit Evidence Package
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-white/10 text-white font-semibold text-base hover:bg-white/20 transition-colors"
            >
              How it works
            </a>
          </div>
        </div>
      </section>

      {/* ── PROBLEM ── */}
      <section className="py-20 px-6 border-b border-surface-border">
        <div className="max-w-4xl mx-auto">
          <div className="grid sm:grid-cols-2 gap-12 items-center">
            <div>
              <p className="text-brand font-semibold text-sm uppercase tracking-wider mb-3">
                The Problem
              </p>
              <h2 className="text-3xl font-bold mb-5 leading-tight">
                Anonymous tips arrive with no verifiable history
              </h2>
              <p className="text-ink/60 leading-relaxed mb-4">
                A source sends documents. You don't know if they were altered before reaching
                you. You can't prove when you received them. If challenged in court or by an
                editor, you have no cryptographic evidence of time-of-receipt.
              </p>
              <p className="text-ink/60 leading-relaxed">
                And if you investigate the files yourself, you risk tainting the chain of
                custody — making it impossible to prove the analysis came after the timestamp.
              </p>
            </div>
            <div className="bg-surface-card border border-surface-border rounded-xl p-6 space-y-4">
              {[
                'When exactly did you receive the files?',
                'Were they modified after receipt?',
                'Can you prove it was before the story broke?',
                "What's your source for the analysis confidence?",
              ].map((q) => (
                <div key={q} className="flex items-start gap-3">
                  <span className="text-red-500 mt-0.5 flex-shrink-0 text-lg leading-none">✕</span>
                  <p className="text-ink/70 text-sm">{q}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="how-it-works" className="py-20 px-6 bg-surface-card border-b border-surface-border">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-brand font-semibold text-sm uppercase tracking-wider mb-3">
              The Solution
            </p>
            <h2 className="text-3xl font-bold">How ASVS works</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map(({ icon: Icon, title, desc }, i) => (
              <div key={title} className="relative">
                {i < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-6 left-[calc(100%_-_12px)] w-6 h-px bg-surface-border z-10" />
                )}
                <div className="bg-surface rounded-xl border border-surface-border p-5 h-full flex flex-col">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-5 h-5 text-brand" />
                    </div>
                    <span className="text-xs font-bold text-ink/30 uppercase tracking-wider">
                      Step {i + 1}
                    </span>
                  </div>
                  <p className="font-semibold text-sm mb-2">{title}</p>
                  <p className="text-ink/55 text-sm leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="py-20 px-6 border-b border-surface-border">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-3xl font-bold">Built for editorial integrity</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex gap-4 p-5 rounded-xl bg-surface-card border border-surface-border">
                <div className="w-9 h-9 rounded-lg bg-brand/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-4.5 h-4.5 text-brand" />
                </div>
                <div>
                  <p className="font-semibold text-sm mb-1">{title}</p>
                  <p className="text-ink/55 text-sm leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SAMPLE CERTIFICATE ── */}
      <section className="py-20 px-6 bg-surface-card border-b border-surface-border">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-10">
            <p className="text-brand font-semibold text-sm uppercase tracking-wider mb-3">
              Example Output
            </p>
            <h2 className="text-3xl font-bold mb-3">A real verification certificate</h2>
            <p className="text-ink/55 max-w-xl mx-auto">
              Every submission produces a PDF certificate and publication-ready attribution
              sentences with per-claim tone selection.
            </p>
          </div>

          {/* Attribution language preview */}
          <div className="bg-surface rounded-xl border border-surface-border p-6 mb-8">
            <p className="text-xs font-semibold text-ink/40 uppercase tracking-wider mb-4">
              Sample Attribution Language
            </p>
            <div className="space-y-3">
              {sampleAttribution.map((line, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-brand/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-brand text-xs font-bold">{i + 1}</span>
                  </div>
                  <p className="text-ink/70 text-sm leading-relaxed italic">"{line}"</p>
                </div>
              ))}
            </div>
          </div>

          {/* PDF embed */}
          <div className="rounded-xl overflow-hidden border border-surface-border shadow-sm">
            <div className="bg-brand px-5 py-3 flex items-center gap-2">
              <Award className="w-4 h-4 text-white/80" />
              <span className="text-white text-sm font-semibold">CERT-2026-590845.pdf</span>
            </div>
            <iframe
              src={certPdf}
              title="Sample Verification Certificate"
              className="w-full"
              style={{ height: '780px' }}
            />
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ── */}
      <section className="relative overflow-hidden py-24 px-6 bg-brand text-white text-center">

        {/* background layers */}
        <div className="absolute inset-0 pointer-events-none select-none" aria-hidden="true">
          {/* film grain */}
          <svg className="absolute inset-0 w-full h-full opacity-[0.07]" xmlns="http://www.w3.org/2000/svg">
            <filter id="cta-noise">
              <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="4" stitchTiles="stitch" />
              <feColorMatrix type="saturate" values="0" />
            </filter>
            <rect width="100%" height="100%" filter="url(#cta-noise)" />
          </svg>
          {/* dot matrix */}
          <svg className="absolute inset-0 w-full h-full opacity-[0.09]" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="cta-dots" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
                <circle cx="1" cy="1" r="1" fill="white" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#cta-dots)" />
          </svg>
          {/* warm centre glow */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_65%_100%_at_50%_50%,rgba(107,18,40,0.55),transparent)]" />
          {/* edge vignette */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_75%_at_50%_50%,transparent_45%,rgba(25,4,10,0.75))]" />
          {/* top hairline */}
          <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          {/* seal — bottom right */}
          <div className="absolute -bottom-20 -right-20 w-72 h-72 opacity-[0.10]">
            <svg viewBox="-130 -130 260 260" xmlns="http://www.w3.org/2000/svg">
              <circle cx="0" cy="0" r="122" fill="none" stroke="white" strokeWidth="1.2" />
              <circle cx="0" cy="0" r="96"  fill="none" stroke="white" strokeWidth="0.7" />
              <circle cx="0" cy="0" r="70"  fill="none" stroke="white" strokeWidth="0.7" />
              <circle cx="0" cy="0" r="48"  fill="none" stroke="white" strokeWidth="0.9" />
              <circle cx="0" cy="0" r="28"  fill="none" stroke="white" strokeWidth="0.7" />
              <circle cx="0" cy="0" r="12"  fill="none" stroke="white" strokeWidth="1.1" />
              {Array.from({ length: 30 }, (_, i) => {
                const a = (i / 30) * Math.PI * 2
                const major = i % 5 === 0
                return (
                  <line
                    key={i}
                    x1={Math.cos(a) * (major ? 108 : 115)} y1={Math.sin(a) * (major ? 108 : 115)}
                    x2={Math.cos(a) * 122} y2={Math.sin(a) * 122}
                    stroke="white" strokeWidth={major ? 1.4 : 0.6}
                  />
                )
              })}
              <line x1="-122" y1="0" x2="122" y2="0" stroke="white" strokeWidth="0.4" strokeDasharray="3 8" />
              <line x1="0" y1="-122" x2="0" y2="122" stroke="white" strokeWidth="0.4" strokeDasharray="3 8" />
              <circle cx="0" cy="0" r="5" fill="none" stroke="white" strokeWidth="1.2" />
              <circle cx="0" cy="0" r="2" fill="white" opacity="0.8" />
            </svg>
          </div>
          {/* mirror seal — top left, smaller */}
          <div className="absolute -top-16 -left-16 w-48 h-48 opacity-[0.07]">
            <svg viewBox="-80 -80 160 160" xmlns="http://www.w3.org/2000/svg">
              <circle cx="0" cy="0" r="74" fill="none" stroke="white" strokeWidth="1" />
              <circle cx="0" cy="0" r="56" fill="none" stroke="white" strokeWidth="0.6" />
              <circle cx="0" cy="0" r="40" fill="none" stroke="white" strokeWidth="0.6" />
              <circle cx="0" cy="0" r="24" fill="none" stroke="white" strokeWidth="0.8" />
              <line x1="-74" y1="0" x2="74" y2="0" stroke="white" strokeWidth="0.4" strokeDasharray="2 7" />
              <line x1="0" y1="-74" x2="0" y2="74" stroke="white" strokeWidth="0.4" strokeDasharray="2 7" />
            </svg>
          </div>
        </div>

        <div className="relative max-w-2xl mx-auto">
          <ShieldCheck className="w-12 h-12 text-white/70 mx-auto mb-5" />
          <h2 className="text-3xl font-bold mb-4">Ready to verify your evidence?</h2>
          <p className="text-white/65 mb-8 leading-relaxed">
            Upload your files. ASVS timestamps them immediately, runs the analysis, and issues a
            certificate — no account required, no metadata stored.
          </p>
          <Link
            to="/submit"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-white text-brand font-bold text-base hover:bg-surface transition-colors"
          >
            <Upload className="w-5 h-5" />
            Submit Evidence Package
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="py-6 border-t border-surface-border text-center text-xs text-ink/40">
        Developed by Jônatas Kirsch · ASVS attests to provenance and integrity, not to the truth of the underlying allegations.
      </footer>
    </div>
  )
}
