// TypeScript interfaces matching backend Pydantic schemas

export type SubmissionStatus = 'INGESTED' | 'TIMESTAMPED' | 'ANALYZED' | 'COMPLETE' | 'FAILED'

export interface SubmissionResponse {
  submission_id: string
  merkle_root: string
  file_count: number
  status: SubmissionStatus
  created_at: string
}

export interface SubmissionStatusResponse {
  submission_id: string
  status: SubmissionStatus
}

export interface RFC3161Proof {
  tsa: string
  timestamp: string
  token_hash: string
  tsa_cert_algorithm: string
  tsa_cert_generation: string
}

export interface OTSProof {
  calendars: string[]
  confirmed: boolean
  bitcoin_block: number | null
  block_timestamp: string | null
}

export interface TimestampProofs {
  rfc3161: RFC3161Proof | null
  opentimestamps: OTSProof | null
}

export interface AnalysisSummary {
  overall_confidence: number
  consistency_score: number
  corroboration_score: number
  plausibility_score: number
  reliability_class: 'HIGH' | 'MEDIUM' | 'LOW'
  evidence_types: string[]
  red_flags: string[]
  analysis_notes: string
}

export interface EvidencePackage {
  file_count: number
  merkle_root: string
  proof_paths_available: boolean
}

export interface CertificateResponse {
  certificate_id: string
  submission_id: string
  issued_at: string
  evidence_package: EvidencePackage
  timestamp_proofs: TimestampProofs
  analysis: AnalysisSummary
  attribution_language: string[]
}

export interface MerkleProofStep {
  hash: string
  position: 'left' | 'right'
}

export interface MerkleProofResponse {
  file_hash: string
  merkle_proof_path: MerkleProofStep[]
  merkle_root: string
  valid: boolean
}

export interface VerifyRequest {
  certificate_id: string
  merkle_root: string
}

export interface VerifyResponse {
  certificate_id: string
  rfc3161_valid: boolean
  opentimestamps_confirmed: boolean
  merkle_root_matches: boolean
}

export interface CertificateListItem {
  certificate_id: string
  submission_id: string
  issued_at: string
  overall_confidence: number
  reliability_class: string
}
