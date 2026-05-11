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


def _upgrade_ots(ots_path: str) -> tuple[bool, int | None, datetime | None]:
    """
    Attempt to upgrade a pending .ots file against the OTS calendars.

    Returns (confirmed, bitcoin_block, block_timestamp).

    Correct upgrade flow (mirrors otsclient.cmds.upgrade_timestamp):
      1. Deserialise the DetachedTimestampFile (from otsclient.cmds, not opentimestamps.timestamp)
      2. Walk sub-timestamps looking for PendingAttestation leaf nodes
      3. For each, call cal.get_timestamp(sub_stamp.msg) — raw commitment bytes, NOT
         the Timestamp object — and merge the result back
      4. Check for BitcoinBlockHeaderAttestation anywhere in the tree
    """
    try:
        from otsclient.cmds import DetachedTimestampFile, PendingAttestation
        from opentimestamps.core.serialize import (
            BytesDeserializationContext,
            BytesSerializationContext,
        )
        from opentimestamps.core.notary import BitcoinBlockHeaderAttestation
        import opentimestamps.calendar
        from app.core.config import get_settings

        settings = get_settings()
        ots_bytes = Path(ots_path).read_bytes()
        ctx = BytesDeserializationContext(ots_bytes)
        file_ts = DetachedTimestampFile.deserialize(ctx)

        # Walk to leaf sub-stamps that carry attestations (mirrors directly_verified)
        def _directly_verified(stamp):
            if stamp.attestations:
                yield stamp
            else:
                for sub in stamp.ops.values():
                    yield from _directly_verified(sub)

        for sub_stamp in _directly_verified(file_ts.timestamp):
            for attestation in list(sub_stamp.attestations):
                if isinstance(attestation, PendingAttestation):
                    commitment = sub_stamp.msg  # raw bytes — NOT the Timestamp object
                    for url in settings.ots_calendar_urls:
                        try:
                            cal = opentimestamps.calendar.RemoteCalendar(url)
                            upgraded_stamp = cal.get_timestamp(commitment, timeout=10)
                            sub_stamp.merge(upgraded_stamp)
                        except Exception:
                            pass

        # Persist the upgraded .ots file
        out_ctx = BytesSerializationContext()
        file_ts.serialize(out_ctx)
        Path(ots_path).write_bytes(out_ctx.getbytes())

        # Check for Bitcoin attestation anywhere in the tree
        def _find_bitcoin_attestation(ts):
            for attest in ts.attestations:
                if isinstance(attest, BitcoinBlockHeaderAttestation):
                    return attest
            for sub_ts in ts.ops.values():
                result = _find_bitcoin_attestation(sub_ts)
                if result:
                    return result
            return None

        attest = _find_bitcoin_attestation(file_ts.timestamp)
        if attest:
            # Block timestamp requires a Bitcoin node; record upgrade time as proxy
            return True, attest.height, datetime.now(timezone.utc)

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

            confirmed, block_height, block_ts = _upgrade_ots(
                proof.ots_file_path
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
