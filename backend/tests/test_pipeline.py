"""Unit tests for app.tasks.pipeline Celery tasks."""
import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_session_ctx(db_mock=None):
    """Return a context manager factory that yields a mock DB session."""
    if db_mock is None:
        db_mock = MagicMock()

    @contextmanager
    def _ctx():
        yield db_mock

    return _ctx


# ---------------------------------------------------------------------------
# task_timestamp
# ---------------------------------------------------------------------------

class TestTaskTimestamp:
    def test_calls_timestamp_submission_and_sets_status(self):
        sub_id = str(uuid.uuid4())
        db_mock = MagicMock()

        with patch("app.tasks.pipeline.db_session", new=_make_db_session_ctx(db_mock)), \
             patch("app.tasks.pipeline.timestamp_submission") as mock_ts, \
             patch("app.tasks.pipeline.set_submission_status") as mock_status:
            from app.tasks.pipeline import task_timestamp
            # Call the underlying function body (bypasses Celery retry mechanism)
            result = task_timestamp.run(sub_id)

        mock_ts.assert_called_once_with(sub_id, db_mock)
        mock_status.assert_called_once_with(sub_id, "TIMESTAMPED")
        assert result == sub_id

    def test_retries_on_exception(self):
        sub_id = str(uuid.uuid4())

        with patch("app.tasks.pipeline.db_session", new=_make_db_session_ctx()), \
             patch("app.tasks.pipeline.timestamp_submission", side_effect=Exception("ts error")), \
             patch("app.tasks.pipeline.set_submission_status"):
            from app.tasks.pipeline import task_timestamp
            task_mock_self = MagicMock()
            task_mock_self.retry.side_effect = Exception("retry raised")

            with pytest.raises(Exception):
                task_timestamp.run(sub_id)


# ---------------------------------------------------------------------------
# task_analyse
# ---------------------------------------------------------------------------

class TestTaskAnalyse:
    def test_calls_analyse_submission_and_sets_status(self):
        sub_id = str(uuid.uuid4())
        db_mock = MagicMock()

        with patch("app.tasks.pipeline.db_session", new=_make_db_session_ctx(db_mock)), \
             patch("app.tasks.pipeline.analyse_submission") as mock_analyse, \
             patch("app.tasks.pipeline.set_submission_status") as mock_status:
            from app.tasks.pipeline import task_analyse
            result = task_analyse.run(sub_id)

        mock_analyse.assert_called_once_with(sub_id, db_mock)
        mock_status.assert_called_once_with(sub_id, "ANALYZED")
        assert result == sub_id

    def test_retries_on_exception(self):
        sub_id = str(uuid.uuid4())

        with patch("app.tasks.pipeline.db_session", new=_make_db_session_ctx()), \
             patch("app.tasks.pipeline.analyse_submission", side_effect=ValueError("bad")), \
             patch("app.tasks.pipeline.set_submission_status"):
            from app.tasks.pipeline import task_analyse
            with pytest.raises(Exception):
                task_analyse.run(sub_id)


# ---------------------------------------------------------------------------
# task_certify
# ---------------------------------------------------------------------------

class TestTaskCertify:
    def test_calls_generate_certificate_and_sets_status(self):
        sub_id = str(uuid.uuid4())
        cert_id = "CERT-2026-AABB01"
        db_mock = MagicMock()

        with patch("app.tasks.pipeline.db_session", new=_make_db_session_ctx(db_mock)), \
             patch("app.tasks.pipeline.generate_certificate", return_value=cert_id) as mock_cert, \
             patch("app.tasks.pipeline.set_submission_status") as mock_status:
            from app.tasks.pipeline import task_certify
            result = task_certify.run(sub_id)

        mock_cert.assert_called_once_with(sub_id, db_mock)
        mock_status.assert_called_once_with(sub_id, "COMPLETE")
        assert result == cert_id

    def test_retries_on_exception(self):
        sub_id = str(uuid.uuid4())

        with patch("app.tasks.pipeline.db_session", new=_make_db_session_ctx()), \
             patch("app.tasks.pipeline.generate_certificate", side_effect=RuntimeError("err")), \
             patch("app.tasks.pipeline.set_submission_status"):
            from app.tasks.pipeline import task_certify
            with pytest.raises(Exception):
                task_certify.run(sub_id)


# ---------------------------------------------------------------------------
# enqueue_pipeline
# ---------------------------------------------------------------------------

class TestEnqueuePipeline:
    def test_enqueues_chain(self):
        sub_id = str(uuid.uuid4())

        with patch("app.tasks.pipeline.chain") as mock_chain:
            mock_pipeline = MagicMock()
            mock_chain.return_value = mock_pipeline

            from app.tasks.pipeline import enqueue_pipeline
            enqueue_pipeline(sub_id)

        mock_chain.assert_called_once()
        mock_pipeline.delay.assert_called_once()
