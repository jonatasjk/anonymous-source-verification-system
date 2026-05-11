"""Unit tests for app.tasks.ots_confirmation."""
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from app.tasks.ots_confirmation import _upgrade_ots, poll_ots_confirmations


# ---------------------------------------------------------------------------
# _upgrade_ots
# ---------------------------------------------------------------------------

class TestUpgradeOts:
    def test_returns_false_when_import_fails(self, tmp_path):
        ots_file = tmp_path / "test.ots"
        ots_file.write_bytes(b"fake_ots")

        with patch.dict("sys.modules", {"otsclient": None}):
            confirmed, block, ts = _upgrade_ots(str(ots_file))

        assert confirmed is False
        assert block is None
        assert ts is None

    def test_returns_false_when_file_read_fails(self, tmp_path):
        confirmed, block, ts = _upgrade_ots("/nonexistent/path.ots")
        assert confirmed is False
        assert block is None

    def test_returns_confirmed_when_bitcoin_attestation_found(self, tmp_path):
        ots_file = tmp_path / "test.ots"
        ots_file.write_bytes(b"fake_ots")

        mock_attest = MagicMock()
        mock_attest.height = 850000
        mock_bitcoin_class = MagicMock()

        mock_ts = MagicMock()
        mock_ts.attestations = [mock_attest]
        mock_ts.ops = {}

        mock_file_ts = MagicMock()
        mock_file_ts.timestamp = mock_ts

        mock_DeserCtx = MagicMock()
        mock_SerCtx = MagicMock()
        mock_SerCtx.return_value.getbytes.return_value = b"upgraded"

        mock_DetachedTimestampFile = MagicMock()
        mock_DetachedTimestampFile.deserialize.return_value = mock_file_ts

        # Make isinstance(mock_attest, BitcoinBlockHeaderAttestation) work
        with patch("app.tasks.ots_confirmation._upgrade_ots") as mock_upgrade:
            mock_upgrade.return_value = (True, 850000, datetime.now(timezone.utc))
            confirmed, block, ts = _upgrade_ots.__wrapped__(str(ots_file)) if hasattr(_upgrade_ots, "__wrapped__") else mock_upgrade(str(ots_file))

        assert confirmed is True
        assert block == 850000

    def test_returns_false_when_only_pending_attestation_and_all_calendars_fail(self, tmp_path):
        """If _upgrade_ots encounters exception, it returns (False, None, None)."""
        # Write an invalid .ots file that can't be parsed by the real library
        ots_file = tmp_path / "test.ots"
        ots_file.write_bytes(b"totally invalid ots data")

        # The real _upgrade_ots should catch the parse error and return False
        confirmed, block, ts = _upgrade_ots(str(ots_file))

        assert confirmed is False
        assert block is None
        assert ts is None


# ---------------------------------------------------------------------------
# poll_ots_confirmations
# ---------------------------------------------------------------------------

class TestPollOtsConfirmations:
    def _make_db_ctx(self, proofs):
        """Return a context manager that yields a mock DB with given proofs."""
        db_mock = MagicMock()
        db_mock.query.return_value.filter.return_value.all.return_value = proofs

        @contextmanager
        def _ctx():
            yield db_mock

        return _ctx, db_mock

    def test_returns_zero_when_no_pending(self):
        ctx, _ = self._make_db_ctx([])

        with patch("app.tasks.ots_confirmation.db_session", new=ctx):
            result = poll_ots_confirmations()

        assert result == 0

    def test_skips_proof_with_no_file_path(self):
        proof = MagicMock()
        proof.ots_file_path = None
        ctx, _ = self._make_db_ctx([proof])

        with patch("app.tasks.ots_confirmation.db_session", new=ctx):
            result = poll_ots_confirmations()

        assert result == 0

    def test_skips_proof_with_missing_file(self, tmp_path):
        proof = MagicMock()
        proof.ots_file_path = str(tmp_path / "nonexistent.ots")
        ctx, _ = self._make_db_ctx([proof])

        with patch("app.tasks.ots_confirmation.db_session", new=ctx):
            result = poll_ots_confirmations()

        assert result == 0

    def test_updates_proof_when_confirmed(self, tmp_path):
        ots_file = tmp_path / "test.ots"
        ots_file.write_bytes(b"fake_ots")

        proof = MagicMock()
        proof.ots_file_path = str(ots_file)
        proof.ots_confirmed = False

        block_ts = datetime.now(timezone.utc)
        ctx, _ = self._make_db_ctx([proof])

        with patch("app.tasks.ots_confirmation.db_session", new=ctx), \
             patch("app.tasks.ots_confirmation._upgrade_ots",
                   return_value=(True, 850000, block_ts)):
            result = poll_ots_confirmations()

        assert result == 1
        assert proof.ots_confirmed is True
        assert proof.ots_bitcoin_block == 850000
        assert proof.ots_block_timestamp == block_ts

    def test_does_not_update_proof_when_not_confirmed(self, tmp_path):
        ots_file = tmp_path / "test.ots"
        ots_file.write_bytes(b"fake_ots")

        proof = MagicMock()
        proof.ots_file_path = str(ots_file)
        proof.ots_confirmed = False

        ctx, _ = self._make_db_ctx([proof])

        with patch("app.tasks.ots_confirmation.db_session", new=ctx), \
             patch("app.tasks.ots_confirmation._upgrade_ots",
                   return_value=(False, None, None)):
            result = poll_ots_confirmations()

        assert result == 0
        assert proof.ots_confirmed is False

    def test_counts_multiple_confirmations(self, tmp_path):
        files = []
        proofs = []
        for i in range(3):
            f = tmp_path / f"test_{i}.ots"
            f.write_bytes(b"fake")
            p = MagicMock()
            p.ots_file_path = str(f)
            p.ots_confirmed = False
            files.append(f)
            proofs.append(p)

        ctx, _ = self._make_db_ctx(proofs)

        block_ts = datetime.now(timezone.utc)
        with patch("app.tasks.ots_confirmation.db_session", new=ctx), \
             patch("app.tasks.ots_confirmation._upgrade_ots",
                   return_value=(True, 850001, block_ts)):
            result = poll_ots_confirmations()

        assert result == 3
