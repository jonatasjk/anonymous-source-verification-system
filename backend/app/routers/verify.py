import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.merkle import verify_inclusion
from app.models.db import Submission, Certificate
from app.models.schemas import MerkleProofResponse, VerifyRequest, VerifyResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/verify", response_model=VerifyResponse)
def verify_certificate(body: VerifyRequest, db: Session = Depends(get_db)):
    """
    Public endpoint. Given a certificate_id and merkle_root, verify:
      1. The merkle_root matches the stored certificate
      2. The RFC 3161 token hash is on record
      3. The OpenTimestamps receipt is confirmed on the Bitcoin blockchain

    No authentication required. Anyone can verify independently.
    """
    cert = db.query(Certificate).filter(
        Certificate.certificate_id == body.certificate_id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")

    payload = cert.payload
    stored_root = payload["evidence_package"]["merkle_root"]
    root_matches = stored_root == body.merkle_root

    proof = cert.submission.timestamp_proof if cert.submission else None
    ots_confirmed = proof.ots_confirmed if proof else False

    # For RFC 3161, we confirm the token is stored (full cryptographic verification
    # requires the TSA public certificate; see docs/ARCHITECTURE.md §3.2.2).
    rfc3161_valid = bool(proof and proof.rfc3161_token_hash)

    return VerifyResponse(
        certificate_id=body.certificate_id,
        rfc3161_valid=rfc3161_valid,
        opentimestamps_confirmed=ots_confirmed,
        merkle_root_matches=root_matches,
    )


@router.get(
    "/submissions/{submission_id}/files/{file_hash}/proof",
    response_model=MerkleProofResponse,
)
def get_merkle_proof(submission_id: str, file_hash: str, db: Session = Depends(get_db)):
    """
    Return the Merkle proof path for a single file.

    Enables selective disclosure: a journalist can publish and authenticate
    one document without revealing any other files in the submission.

    Verification:
        hash(leaf + proof_path) == merkle_root
    """
    try:
        sid = uuid.UUID(submission_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid submission_id format.")

    submission = db.query(Submission).filter(Submission.id == sid).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")

    target_file = next(
        (f for f in submission.files if f.content_hash == file_hash), None
    )
    if not target_file:
        raise HTTPException(status_code=404, detail="File not found in this submission.")

    return MerkleProofResponse(
        file_hash=file_hash,
        merkle_proof_path=target_file.merkle_proof_path,
        merkle_root=submission.merkle_root,
    )
