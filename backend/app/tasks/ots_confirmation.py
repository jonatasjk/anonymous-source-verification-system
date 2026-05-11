"""
OTS Confirmation Task (Celery Beat)
------------------------------------
Runs every 5 minutes. Checks all pending OpenTimestamps receipts against
the Bitcoin blockchain. When a block is confirmed, writes the block height
and timestamp back to PostgreSQL.

Bitcoin confirmations take ~10 minutes on average (one block).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from app.tasks.celery_app import celery_app
from app.core.database import db_session
from app.models.db import TimestampProof

logger = logging.getLogger(__name__)


def _upgrade_ots(ots_path: str, merkle_root_hex: str) -> tuple[bool, int | None, datetime | None]:
    """
    Attempt to upgrade a pending .ots file against the OTS calendars.

    Returns (confirmed, bitcoin_block, block_timestamp).
    """
    try:
        from opentimestamps.core.serialize import (
            BytesDeserializationContext,
            BytesSerializationContext,
        )
        from opentimestamps.timestamp import DetachedTimestampFile
        import opentimestamps.calendar
        from app.core.config import get_settings

        settings = get_settings()
        ots_bytes = Path(ots_path).read_bytes()
        ctx = BytesDeserializationContext(ots_bytes)
        file_ts = DetachedTimestampFile.deserialize(ctx)

        # Try to upgrade via calendars
        for url in settings.ots_calendar_urls:
            try:
                cal = opentimestamps.calendar.RemoteCalendar(url)
                cal.get_timestamp(file_ts.timestamp)
            except Exception:
                pass

        # Save upgraded .ots file
        out_ctx = BytesSerializationContext()
        file_ts.serialize(out_ctx)
        Path(ots_path).write_bytes(out_ctx.getbytes())

        # Check for Bitcoin attestation
        from opentimestamps.core.notary import BitcoinBlockHeaderAttestation

        def _find_bitcoin_attestation(ts):
            for attest in ts.attestations:
                if isinstance(attest, BitcoinBlockHeaderAttestation):
                    return attest
            for op, next_ts in ts.ops.items():
                result = _find_bitcoin_attestation(next_ts)
                if result:
                    return result
            return None

        attest = _find_bitcoin_attestation(file_ts.timestamp)
        if attest:
            block_height = attest.height
            # Block timestamp is not directly available from the attestation object
            # without a Bitcoin node; we record the upgrade time as an approximation
            return True, block_height, datetime.now(timezone.utc)

        return False, None, None

    except Exception as exc:
        logger.warning("OTS upgrade failed for %s: %s", ots_path, exc)
        return False, None, None


@celery_app.task(name="app.tasks.ots_confirmation.poll_ots_confirmations")
def poll_ots_confirmations() -> int:
    """
    Celery Beat periodic task — runs every 5 minutes.
    Returns the number of submissions confirmed in this run.
    """
    confirmed_count = 0

    with db_session() as db:
        pending = (
            db.query(TimestampProof)
            .filter(
                TimestampProof.ots_confirmed == False,
                TimestampProof.ots_file_path != None,
            )
            .all()
        )

        logger.info("Polling OTS for %d pending submission(s)", len(pending))

        for proof in pending:
            if not proof.ots_file_path or not Path(proof.ots_file_path).exists():
                continue

            submission = proof.submission
            if not submission:
                continue

            confirmed, block_height, block_ts = _upgrade_ots(
                proof.ots_file_path, submission.merkle_root
            )

            if confirmed:
                proof.ots_confirmed = True
                proof.ots_bitcoin_block = block_height
                proof.ots_block_timestamp = block_ts
                confirmed_count += 1
                logger.info(
                    "OTS confirmed for submission %s at block %s",
                    proof.submission_id, block_height,
                )

    return confirmed_count
