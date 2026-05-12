import type {
  CertificateListItem,
  CertificateResponse,
  MerkleProofResponse,
  SubmissionResponse,
  SubmissionStatusResponse,
  VerifyResponse,
} from '@/types/certificate'

const CERT_ID = 'CERT-2026-590845'
const SUB_ID = 'mock-submission-001'

export const MOCK_SUBMISSION: SubmissionResponse = {
  submission_id: SUB_ID,
  merkle_root: 'a3f1c2e4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2',
  file_count: 3,
  status: 'COMPLETE',
  created_at: new Date().toISOString(),
}

export const MOCK_STATUS: SubmissionStatusResponse = {
  submission_id: SUB_ID,
  status: 'COMPLETE',
}

export const MOCK_CERTIFICATE: CertificateResponse = {
  certificate_id: CERT_ID,
  submission_id: SUB_ID,
  issued_at: new Date().toISOString(),
  evidence_package: {
    file_count: 3,
    merkle_root: 'a3f1c2e4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2',
    proof_paths_available: true,
  },
  timestamp_proofs: {
    rfc3161: {
      tsa: 'freetsa.org',
      timestamp: new Date().toISOString(),
      token_hash: 'b7e23ec29af22b0b4e41da31e868d57226121c84b9c6d4e5f8a1b2c3d4e5f6a7',
      tsa_cert_algorithm: 'EC P-384 (secp384r1)',
      tsa_cert_generation: '2026-2040',
    },
    opentimestamps: {
      calendars: [
        'https://alice.btc.calendar.opentimestamps.org',
        'https://bob.btc.calendar.opentimestamps.org',
      ],
      confirmed: true,
      bitcoin_block: 895432,
      block_timestamp: new Date(Date.now() - 3_600_000).toISOString(),
    },
  },
  analysis: {
    overall_confidence: 81,
    consistency_score: 85,
    corroboration_score: 78,
    plausibility_score: 80,
    reliability_class: 'HIGH',
    evidence_types: ['financial_records', 'internal_communications', 'supporting_documents'],
    red_flags: [],
    analysis_notes:
      'The evidence package demonstrates strong internal consistency across the three submitted documents. Financial figures corroborate the timeline described in the communications.',
  },
  attribution_language: [
    `Documents reviewed by ASVS (cert ${CERT_ID}) show internal communications that assertively indicate the procurement process was bypassed for contracts awarded in Q3 2024.`,
    `The evidence package allegedly contains financial records suggesting off-the-books payments totalling €2.3 million between April and September 2024.`,
    `Supporting materials hedgedly corroborate accounts from multiple sources regarding the involvement of senior officials in the approval chain.`,
  ],
}

export const MOCK_CERTIFICATES_LIST: CertificateListItem[] = [
  {
    certificate_id: CERT_ID,
    submission_id: SUB_ID,
    issued_at: new Date().toISOString(),
    overall_confidence: 81,
    reliability_class: 'HIGH',
  },
]

export const MOCK_MERKLE_PROOF: MerkleProofResponse = {
  file_hash: 'c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2',
  merkle_proof_path: [
    { hash: 'd1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2', position: 'right' },
    { hash: 'e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2', position: 'left' },
  ],
  merkle_root: 'a3f1c2e4b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2',
  valid: true,
}

export const MOCK_VERIFY: VerifyResponse = {
  certificate_id: CERT_ID,
  rfc3161_valid: true,
  opentimestamps_confirmed: true,
  merkle_root_matches: true,
}

/**
 * Returns mock data matching the request URL, or null if no mock exists for
 * that route. Only used when the backend is unreachable.
 */
export function getMockResponse(url: string, _method: string): unknown | null {
  // POST /submissions → new submission
  if (/\/submissions$/.test(url)) return MOCK_SUBMISSION

  // GET /submissions/:id/status
  if (/\/submissions\/[^/]+\/status$/.test(url)) return MOCK_STATUS

  // GET /submissions/:id/certificate
  if (/\/submissions\/[^/]+\/certificate$/.test(url)) return MOCK_CERTIFICATE

  // GET /certificates
  if (/\/certificates$/.test(url)) return MOCK_CERTIFICATES_LIST

  // GET /certificates/:id
  if (/\/certificates\/[^/]+$/.test(url)) return MOCK_CERTIFICATE

  // POST /verify
  if (/\/verify$/.test(url)) return MOCK_VERIFY

  // GET /submissions/:id/files/:hash/proof
  if (/\/files\/[^/]+\/proof$/.test(url)) return MOCK_MERKLE_PROOF

  return null
}
