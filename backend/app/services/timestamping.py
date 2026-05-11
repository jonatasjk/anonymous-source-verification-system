"""
Timestamping Service
--------------------
Anchors the Merkle root to two independent timestamp authorities:
  1. RFC 3161 TSA (FreeTSA.org) — legally admissible, EC P-384 cert since March 2026
  2. OpenTimestamps (Bitcoin blockchain) — decentralised, immutable after ~10 min

The timestamps prove the evidence existed BEFORE any analysis or publication.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import sha256_bytes
from app.models.db import Submission, TimestampProof

settings = get_settings()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RFC 3161
# ---------------------------------------------------------------------------

def _get_rfc3161_timestamp(merkle_root_bytes: bytes) -> bytes:
    """
    Request an RFC 3161 timestamp token from FreeTSA.org.
    Returns raw .tsr bytes.

    Note on the FreeTSA certificate rotation (March 2026):
      - New cert uses EC P-384 (secp384r1), valid 2026-03-16 to 2040.
      - Old cert (2016-2026) is archived as tsa.crt_expired and still needed
        for verifying tokens issued before March 2026.
    """
    try:
        from rfc3161ng import RemoteTimestamper

        rt = RemoteTimestamper(settings.tsa_url, hashname="sha256")
        tsr_bytes = rt.timestamp(data=merkle_root_bytes, return_tsr=True)
        return tsr_bytes
    except Exception as exc:
        logger.warning("rfc3161ng failed (%s), falling back to raw HTTP", exc)
        return _get_rfc3161_raw(merkle_root_bytes)


def _get_rfc3161_raw(merkle_root_bytes: bytes) -> bytes:
    """
    Fallback: craft a minimal RFC 3161 TimeStampReq with pyasn1 and POST it
    directly to the TSA. Used when rfc3161ng is unavailable.
    """
    import hashlib
    import struct

    digest = hashlib.sha256(merkle_root_bytes).digest()

    # Minimal DER-encoded TimeStampReq
    # SHA-256 OID: 2.16.840.1.101.3.4.2.1
    sha256_oid = bytes([
        0x30, 0x0d,                                      # SEQUENCE
        0x06, 0x09,                                      # OID (9 bytes)
        0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01,
        0x05, 0x00,                                      # NULL params
    ])
    hash_octet = bytes([0x04, len(digest)]) + digest
    msg_imprint = bytes([0x30, len(sha256_oid) + len(hash_octet)]) + sha256_oid + hash_octet

    version = bytes([0x02, 0x01, 0x01])  # INTEGER 1
    req_body = version + msg_imprint
    tsq = bytes([0x30, len(req_body)]) + req_body

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            settings.tsa_url,
            content=tsq,
            headers={"Content-Type": "application/timestamp-query"},
        )
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# OpenTimestamps
# ---------------------------------------------------------------------------

def _stamp_ots(merkle_root_bytes: bytes) -> bytes:
    """
    Submit the Merkle root to OpenTimestamps calendar servers.
    Returns serialised DetachedTimestampFile bytes, or empty bytes on failure.

    The correct flow:
      1. cal.submit(raw_hash_bytes) → returns a Timestamp with PendingAttestation
      2. Merge the returned Timestamp into file_ts.timestamp
      3. Serialise the whole DetachedTimestampFile for storage

    DetachedTimestampFile lives in otsclient.cmds (not opentimestamps.timestamp).
    cal.submit() takes raw bytes (the commitment digest), not a Timestamp object.
    """
    try:
        from otsclient.cmds import DetachedTimestampFile
        from opentimestamps.core.timestamp import Timestamp
        from opentimestamps.core.op import OpSHA256
        from opentimestamps.core.serialize import BytesSerializationContext
        import opentimestamps.calendar

        file_ts = DetachedTimestampFile(OpSHA256(), Timestamp(merkle_root_bytes))

        submitted = False
        for url in settings.ots_calendar_urls:
            try:
                cal = opentimestamps.calendar.RemoteCalendar(url)
                # submit() takes raw hash bytes and returns a Timestamp containing
                # a PendingAttestation; merge it back so the .ots file is complete.
                calendar_timestamp = cal.submit(file_ts.timestamp.msg, timeout=10)
                file_ts.timestamp.merge(calendar_timestamp)
                submitted = True
                logger.info("OTS stamp submitted to %s", url)
            except Exception as exc:
                logger.warning("OTS calendar %s failed: %s", url, exc)

        if not submitted:
            logger.warning("OTS: all calendars failed — no Bitcoin stamp will be stored")
            return b""

        ctx = BytesSerializationContext()
        file_ts.serialize(ctx)
        return ctx.getbytes()

    except Exception as exc:
        logger.warning("opentimestamps library unavailable (%s) — no Bitcoin stamp", exc)
        return b""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def timestamp_submission(submission_id: str, db: Session) -> None:
    """
    Anchor the submission's Merkle root to RFC 3161 and OpenTimestamps.
    Creates a TimestampProof record and updates submission status.
    """
    submission: Submission | None = db.query(Submission).filter(
        Submission.id == uuid.UUID(submission_id)
    ).first()

    if not submission:
        raise ValueError(f"Submission {submission_id} not found")

    merkle_root = submission.merkle_root
    merkle_root_bytes = bytes.fromhex(merkle_root)

    storage_dir = Path(settings.storage_path) / submission_id
    storage_dir.mkdir(parents=True, exist_ok=True)

    # --- RFC 3161 ---
    tsr_bytes = _get_rfc3161_timestamp(merkle_root_bytes)
    tsr_path = storage_dir / "timestamp.tsr"
    tsr_path.write_bytes(tsr_bytes)
    token_hash = sha256_bytes(tsr_bytes)

    # --- OpenTimestamps ---
    ots_bytes = _stamp_ots(merkle_root_bytes)
    ots_path = storage_dir / "timestamp.ots"
    ots_path.write_bytes(ots_bytes)
    ots_hash = sha256_bytes(ots_bytes) if ots_bytes else ""

    proof = TimestampProof(
        submission_id=uuid.UUID(submission_id),
        rfc3161_tsa=settings.tsa_url,
        rfc3161_token_hash=token_hash,
        rfc3161_timestamp=datetime.now(timezone.utc),
        rfc3161_tsr_path=str(tsr_path),
        rfc3161_cert_generation=settings.tsa_cert_generation,
        rfc3161_cert_algorithm=settings.tsa_cert_algorithm,
        ots_file_hash=ots_hash,
        ots_file_path=str(ots_path),
        ots_confirmed=False,
    )
    db.add(proof)

    submission.status = "TIMESTAMPED"
    db.commit()
    logger.info("Timestamped submission %s (rfc3161=%s)", submission_id, token_hash[:16])
