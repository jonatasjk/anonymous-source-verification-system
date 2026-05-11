from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


class SubmissionResponse(BaseModel):
    submission_id: UUID = Field(validation_alias="id")
    status: str
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SubmissionStatusResponse(BaseModel):
    submission_id: UUID
    status: str


# ---------------------------------------------------------------------------
# Certificate sub-schemas
# ---------------------------------------------------------------------------


class FileEntry(BaseModel):
    filename_hash: str
    content_hash: str
    file_type: str | None
    size_bytes: int | None
    merkle_proof_path: list[dict[str, str]]


class EvidencePackage(BaseModel):
    file_count: int
    merkle_root: str
    files: list[FileEntry]


class RFC3161Proof(BaseModel):
    tsa: str
    tsa_cert_generation: str
    tsa_cert_algorithm: str
    token_hash: str
    timestamp: datetime


class OTSProof(BaseModel):
    ots_file_hash: str
    bitcoin_block: int | None = None
    block_timestamp: datetime | None = None
    confirmed: bool


class TimestampProofs(BaseModel):
    rfc3161: RFC3161Proof | None = None
    opentimestamps: OTSProof | None = None


class AnalysisSummary(BaseModel):
    overall_confidence: int
    consistency_score: int
    corroboration_score: int
    plausibility_score: int
    evidence_types: list[str]
    corroborating_sources: int
    red_flags: list[str]
    reliability_class: str


class CertificateResponse(BaseModel):
    certificate_id: str
    submission_id: UUID
    issued_at: datetime
    evidence_package: EvidencePackage
    timestamp_proofs: TimestampProofs
    analysis: AnalysisSummary
    attribution_language: list[str]


class CertificateListItem(BaseModel):
    certificate_id: str
    submission_id: UUID
    issued_at: datetime
    overall_confidence: int
    reliability_class: str


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    certificate_id: str
    merkle_root: str


class VerifyResponse(BaseModel):
    certificate_id: str
    rfc3161_valid: bool
    opentimestamps_confirmed: bool
    merkle_root_matches: bool


class MerkleProofResponse(BaseModel):
    file_hash: str
    merkle_proof_path: list[dict[str, str]]
    merkle_root: str

    def verify(self) -> bool:
        from app.core.merkle import verify_inclusion

        return verify_inclusion(self.file_hash, self.merkle_proof_path, self.merkle_root)
