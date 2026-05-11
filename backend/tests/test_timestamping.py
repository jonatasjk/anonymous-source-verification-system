"""Unit tests for app.services.timestamping."""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.timestamping import (
    _get_rfc3161_raw,
    _get_rfc3161_timestamp,
    _stamp_ots,
    timestamp_submission,
)
from app.models.db import Submission, TimestampProof
from tests.conftest import make_submission


MERKLE_ROOT = "a" * 64
MERKLE_BYTES = bytes.fromhex(MERKLE_ROOT)


# ---------------------------------------------------------------------------
# _get_rfc3161_timestamp
# ---------------------------------------------------------------------------

class TestGetRfc3161Timestamp:
    def test_uses_rfc3161ng_when_available(self):
        fake_tsr = b"fake_tsr_bytes"
        mock_rt = MagicMock()
        mock_rt.timestamp.return_value = fake_tsr
        mock_remote = MagicMock(return_value=mock_rt)

        with patch.dict("sys.modules", {"rfc3161ng": MagicMock(RemoteTimestamper=mock_remote)}):
            result = _get_rfc3161_timestamp(MERKLE_BYTES)

        assert result == fake_tsr

    def test_falls_back_to_raw_when_rfc3161ng_raises(self):
        raw_tsr = b"raw_tsr"
        with patch("app.services.timestamping._get_rfc3161_raw", return_value=raw_tsr) as mock_raw:
            with patch.dict("sys.modules", {"rfc3161ng": MagicMock(
                RemoteTimestamper=MagicMock(side_effect=Exception("lib error"))
            )}):
                result = _get_rfc3161_timestamp(MERKLE_BYTES)

        assert result == raw_tsr


class TestGetRfc3161Raw:
    def test_posts_to_tsa_and_returns_content(self):
        fake_response = MagicMock()
        fake_response.content = b"tsa_response"
        fake_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = fake_response

        with patch("app.services.timestamping.httpx.Client", return_value=mock_client):
            result = _get_rfc3161_raw(MERKLE_BYTES)

        assert result == b"tsa_response"
        assert mock_client.post.called

    def test_raises_on_http_error(self):
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = MagicMock(
            raise_for_status=MagicMock(side_effect=httpx.HTTPStatusError(
                "error", request=MagicMock(), response=MagicMock()
            ))
        )

        with patch("app.services.timestamping.httpx.Client", return_value=mock_client):
            with pytest.raises(Exception):
                _get_rfc3161_raw(MERKLE_BYTES)


# ---------------------------------------------------------------------------
# _stamp_ots
# ---------------------------------------------------------------------------

class TestStampOts:
    def test_returns_bytes_on_success(self):
        """Mock all opentimestamps dependencies and verify bytes are returned."""
        mock_calendar = MagicMock()
        mock_calendar_ts = MagicMock()
        mock_calendar.submit.return_value = mock_calendar_ts

        mock_file_ts = MagicMock()
        mock_file_ts.timestamp.msg = MERKLE_BYTES

        mock_ctx = MagicMock()
        mock_ctx.getbytes.return_value = b"ots_serialized"

        mock_DetachedTimestampFile = MagicMock(return_value=mock_file_ts)
        mock_Timestamp = MagicMock()
        mock_OpSHA256 = MagicMock()
        mock_BytesCtx = MagicMock(return_value=mock_ctx)
        mock_RemoteCalendar = MagicMock(return_value=mock_calendar)
        mock_calendar_mod = MagicMock()
        mock_calendar_mod.RemoteCalendar = mock_RemoteCalendar

        mods = {
            "otsclient": MagicMock(),
            "otsclient.cmds": MagicMock(
                DetachedTimestampFile=mock_DetachedTimestampFile,
            ),
            "opentimestamps": MagicMock(),
            "opentimestamps.core": MagicMock(),
            "opentimestamps.core.timestamp": MagicMock(Timestamp=mock_Timestamp),
            "opentimestamps.core.op": MagicMock(OpSHA256=mock_OpSHA256),
            "opentimestamps.core.serialize": MagicMock(
                BytesSerializationContext=mock_BytesCtx
            ),
            "opentimestamps.calendar": mock_calendar_mod,
        }

        with patch.dict("sys.modules", mods):
            result = _stamp_ots(MERKLE_BYTES)

        assert isinstance(result, bytes)

    def test_returns_empty_bytes_when_import_fails(self):
        # Also mask the submodule so cached imports from earlier tests don't leak through
        with patch.dict("sys.modules", {"otsclient": None, "otsclient.cmds": None}):
            result = _stamp_ots(MERKLE_BYTES)
        assert result == b""

    def test_returns_empty_bytes_when_all_calendars_fail(self):
        """When all calendars fail, _stamp_ots returns b""."""
        # Use a settings mock with empty calendar list to force submitted=False path
        with patch("app.services.timestamping.settings") as mock_settings:
            mock_settings.ots_calendar_urls = []  # no calendars → submitted stays False

            # We still need the opentimestamps imports to not crash
            mock_DetachedTimestampFile = MagicMock()
            mods = {
                "otsclient": MagicMock(),
                "otsclient.cmds": MagicMock(
                    DetachedTimestampFile=mock_DetachedTimestampFile,
                ),
                "opentimestamps": MagicMock(),
                "opentimestamps.core": MagicMock(),
                "opentimestamps.core.timestamp": MagicMock(Timestamp=MagicMock()),
                "opentimestamps.core.op": MagicMock(OpSHA256=MagicMock()),
                "opentimestamps.core.serialize": MagicMock(
                    BytesSerializationContext=MagicMock()
                ),
                "opentimestamps.calendar": MagicMock(),
            }
            with patch.dict("sys.modules", mods):
                result = _stamp_ots(MERKLE_BYTES)

        assert result == b""


# ---------------------------------------------------------------------------
# timestamp_submission
# ---------------------------------------------------------------------------

class TestTimestampSubmission:
    def test_creates_timestamp_proof(self, db, tmp_path):
        sub = make_submission(db, status="INGESTED")
        db.commit()

        with patch("app.services.timestamping._get_rfc3161_timestamp", return_value=b"fake_tsr"), \
             patch("app.services.timestamping._stamp_ots", return_value=b"fake_ots"), \
             patch("app.services.timestamping.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.tsa_url = "https://freetsa.org/tsr"
            mock_settings.tsa_cert_generation = "2026-2040"
            mock_settings.tsa_cert_algorithm = "EC P-384 (secp384r1)"
            mock_settings.ots_calendar_urls = []

            timestamp_submission(str(sub.id), db)

        proof = db.query(TimestampProof).filter(
            TimestampProof.submission_id == sub.id
        ).first()
        assert proof is not None
        assert proof.rfc3161_token_hash is not None
        assert len(proof.rfc3161_token_hash) == 64

    def test_updates_submission_status_to_timestamped(self, db, tmp_path):
        sub = make_submission(db, status="INGESTED")
        db.commit()

        with patch("app.services.timestamping._get_rfc3161_timestamp", return_value=b"fake_tsr"), \
             patch("app.services.timestamping._stamp_ots", return_value=b""), \
             patch("app.services.timestamping.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.tsa_url = "https://freetsa.org/tsr"
            mock_settings.tsa_cert_generation = "2026-2040"
            mock_settings.tsa_cert_algorithm = "EC P-384"
            mock_settings.ots_calendar_urls = []

            timestamp_submission(str(sub.id), db)

        db.refresh(sub)
        assert sub.status == "TIMESTAMPED"

    def test_raises_for_missing_submission(self, db):
        with pytest.raises(ValueError, match="not found"):
            timestamp_submission(str(uuid.uuid4()), db)

    def test_ots_empty_bytes_handled(self, db, tmp_path):
        """Empty OTS bytes (all calendars failed) should produce empty ots_file_hash."""
        sub = make_submission(db, status="INGESTED")
        db.commit()

        with patch("app.services.timestamping._get_rfc3161_timestamp", return_value=b"fake_tsr"), \
             patch("app.services.timestamping._stamp_ots", return_value=b""), \
             patch("app.services.timestamping.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.tsa_url = "https://freetsa.org/tsr"
            mock_settings.tsa_cert_generation = "2026-2040"
            mock_settings.tsa_cert_algorithm = "EC P-384"
            mock_settings.ots_calendar_urls = []

            timestamp_submission(str(sub.id), db)  # must not raise

        proof = db.query(TimestampProof).filter(
            TimestampProof.submission_id == sub.id
        ).first()
        # ots_bytes was empty → ots_hash is "" (not sha256)
        assert proof.ots_file_hash == ""
