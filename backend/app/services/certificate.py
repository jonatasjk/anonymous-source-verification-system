"""
Certificate Service
-------------------
Assembles the VerificationCertificate from the completed submission data,
generates publication-ready attribution language, and persists to PostgreSQL.

The certificate never contains: source name, IP address, file contents,
verbatim quotes, or any other PII.

Certificate ID format: CERT-{YEAR}-{6 uppercase hex chars}
"""

import random
import string
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.db import Submission, Certificate

settings = get_settings()
logger = logging.getLogger(__name__)


def _generate_cert_id() -> str:
    year = datetime.now(timezone.utc).year
    suffix = "".join(random.choices("0123456789ABCDEF", k=6))
    return f"CERT-{year}-{suffix}"


def _build_attribution_language(
    cert_id: str,
    overall_confidence: int,
    attribution_quotes: list[str] | None = None,
    platform_name: str = "ASVS",
) -> list[str]:
    # Publication-ready attribution sentences produced by the LLM.
    # Each entry is a dict with "text" and "tone"; Python only substitutes
    # {platform} and {cert_id} placeholders — sentences are never rewritten.
    sentences: list[str] = []
    for entry in (attribution_quotes or []):
        if isinstance(entry, dict):
            text = entry.get("text", "")
        else:
            text = str(entry)
        sentence = text.replace("{platform}", platform_name).replace("{cert_id}", cert_id)
        if sentence:
            sentences.append(sentence)

    # Guarantee journalists always have something to work with.
    if not sentences:
        if overall_confidence >= 40:
            sentences.append(
                f"According to a source whose materials were independently verified by "
                f"{platform_name} (Certificate {cert_id}), the submitted evidence "
                f"warrants further investigation."
            )
        else:
            sentences.append(
                f"A source independently verified by {platform_name} "
                f"(Certificate {cert_id}) alleged that the submitted materials "
                f"contain information of potential public interest; confidence in the "
                f"evidence is low and independent corroboration is strongly advised "
                f"before publication."
            )

    return sentences


def generate_certificate(submission_id: str, db: Session) -> str:
    """
    Build and persist a VerificationCertificate for the completed submission.

    Returns the certificate_id string.
    """
    submission: Submission | None = (
        db.query(Submission).filter(Submission.id == uuid.UUID(submission_id)).first()
    )
    if not submission:
        raise ValueError(f"Submission {submission_id} not found")

    proof = submission.timestamp_proof
    analysis = submission.analysis_result

    if not proof or not analysis:
        raise ValueError(f"Submission {submission_id} missing proof or analysis")

    cert_id = _generate_cert_id()
    now = datetime.now(timezone.utc)

    # Build evidence package section
    files_payload = [
        {
            "filename_hash": f.filename_hash,
            "content_hash": f.content_hash,
            "file_type": f.file_type,
            "size_bytes": f.size_bytes,
            "merkle_proof_path": f.merkle_proof_path,
        }
        for f in submission.files
    ]

    # Build timestamp proofs section
    rfc3161_ts = proof.rfc3161_timestamp
    timestamp_proofs: dict = {}
    if proof.rfc3161_token_hash:
        timestamp_proofs["rfc3161"] = {
            "tsa": proof.rfc3161_tsa,
            "tsa_cert_generation": proof.rfc3161_cert_generation,
            "tsa_cert_algorithm": proof.rfc3161_cert_algorithm,
            "token_hash": proof.rfc3161_token_hash,
            "timestamp": rfc3161_ts.isoformat() if rfc3161_ts else None,
        }
    if proof.ots_file_hash:
        timestamp_proofs["opentimestamps"] = {
            "ots_file_hash": proof.ots_file_hash,
            "bitcoin_block": proof.ots_bitcoin_block,
            "block_timestamp": (
                proof.ots_block_timestamp.isoformat()
                if proof.ots_block_timestamp
                else None
            ),
            "confirmed": proof.ots_confirmed,
        }

    attribution = _build_attribution_language(
        cert_id,
        analysis.overall_confidence,
        attribution_quotes=analysis.attribution_quotes or [],
        platform_name=settings.platform_name,
    )

    payload = {
        "certificate_id": cert_id,
        "submission_id": str(submission_id),
        "issued_at": now.isoformat(),
        "evidence_package": {
            "file_count": submission.file_count,
            "merkle_root": submission.merkle_root,
            "files": files_payload,
        },
        "timestamp_proofs": timestamp_proofs,
        "analysis": {
            "overall_confidence": analysis.overall_confidence,
            "consistency_score": analysis.consistency_score,
            "corroboration_score": analysis.corroboration_score,
            "plausibility_score": analysis.plausibility_score,
            "evidence_types": analysis.evidence_types,
            "corroborating_sources": analysis.corroborating_sources,
            "red_flags": analysis.red_flags,
            "reliability_class": analysis.reliability_class,
            "key_claims": analysis.key_claims or [],
        },
        "attribution_language": attribution,
    }

    cert = Certificate(
        certificate_id=cert_id,
        submission_id=uuid.UUID(submission_id),
        payload=payload,
        issued_at=now,
    )
    db.add(cert)
    submission.status = "COMPLETE"
    db.commit()

    logger.info("Certificate %s issued for submission %s", cert_id, submission_id)
    return cert_id
