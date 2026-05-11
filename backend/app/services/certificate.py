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
    corroborating_sources: int,
    rfc3161_timestamp: datetime | None,
    ots_confirmed: bool = False,
    attribution_quotes: list[str] | None = None,
    platform_name: str = "ASVS",
) -> list[str]:
    ts_str = rfc3161_timestamp.strftime("%B %d, %Y") if rfc3161_timestamp else "an independently verified date"

    if ots_confirmed:
        anchor_clause = (
            "cryptographic timestamps anchored to the Bitcoin blockchain and "
            "a trusted timestamp authority"
        )
    else:
        anchor_clause = (
            "cryptographic timestamps issued by a trusted timestamp authority "
            "and submitted for Bitcoin blockchain anchoring (confirmation pending)"
        )

    # --- Boilerplate provenance paragraphs ---
    paragraphs: list[str] = [
        (
            f"Evidence reviewed for this report was authenticated using "
            f"{anchor_clause}, establishing that the materials "
            f"existed no later than {ts_str} — before any analysis or "
            f"publication occurred."
        ),
        (
            f"Materials cited in this report have been independently verified "
            f"through cryptographic timestamping (Certificate {cert_id}, "
            f"confidence score {overall_confidence}/100). The certificate "
            f"attests to provenance and integrity, not to the truth of the "
            f"underlying allegations."
        ),
    ]

    # --- Publication-ready attribution sentences ---
    # The LLM produced complete sentences with {platform} and {cert_id} placeholders.
    # Each entry in attribution_quotes is now a dict with "text" and "tone".
    # We substitute the placeholders and return them as-is — no additional wrapping.
    attribution_sentences: list[str] = []
    for entry in (attribution_quotes or []):
        if isinstance(entry, dict):
            text = entry.get("text", "")
        else:
            text = str(entry)
        sentence = text.replace("{platform}", platform_name).replace("{cert_id}", cert_id)
        if sentence:
            attribution_sentences.append(sentence)

    return paragraphs + attribution_sentences


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

    ots_confirmed = bool(proof.ots_confirmed) if proof.ots_file_hash else False
    attribution = _build_attribution_language(
        cert_id,
        analysis.overall_confidence,
        analysis.corroborating_sources,
        rfc3161_ts,
        ots_confirmed=ots_confirmed,
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
