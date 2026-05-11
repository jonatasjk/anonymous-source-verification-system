"""Unit tests for app.services.ingestion."""
import os
import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.ingestion import _detect_file_type, ingest_files
from app.models.db import Submission, SubmissionFile


# ---------------------------------------------------------------------------
# _detect_file_type
# ---------------------------------------------------------------------------

class TestDetectFileType:
    def test_extension_pdf(self):
        assert _detect_file_type("report.pdf") == "document"

    def test_extension_txt(self):
        # "notes" keyword takes precedence; use a neutral name to test the extension path
        assert _detect_file_type("report.txt") == "document"

    def test_extension_docx(self):
        assert _detect_file_type("letter.docx") == "document"

    def test_extension_log(self):
        assert _detect_file_type("server.log") == "log_file"

    def test_extension_mp3(self):
        assert _detect_file_type("clip.mp3") == "audio_recording"

    def test_extension_wav(self):
        assert _detect_file_type("clip.wav") == "audio_recording"

    def test_extension_m4a(self):
        assert _detect_file_type("clip.m4a") == "audio_recording"

    def test_extension_xlsx(self):
        assert _detect_file_type("data.xlsx") == "spreadsheet"

    def test_extension_csv(self):
        assert _detect_file_type("data.csv") == "spreadsheet"

    def test_extension_png(self):
        assert _detect_file_type("screenshot.png") == "image"

    def test_extension_jpg(self):
        assert _detect_file_type("photo.jpg") == "image"

    def test_extension_jpeg(self):
        assert _detect_file_type("photo.jpeg") == "image"

    def test_unknown_extension_defaults_to_document(self):
        assert _detect_file_type("mystery.xyz") == "document"

    def test_keyword_email_overrides_extension(self):
        assert _detect_file_type("email_thread.pdf") == "email_chain"

    def test_keyword_intake(self):
        assert _detect_file_type("intake_form.txt") == "journalist_intake"

    def test_keyword_notes(self):
        assert _detect_file_type("field_notes.txt") == "personal_notes"

    def test_keyword_memo(self):
        assert _detect_file_type("internal_memo.docx") == "analytical_memo"

    def test_keyword_comparison(self):
        assert _detect_file_type("comparison_report.txt") == "analytical_memo"

    def test_keyword_conversation(self):
        assert _detect_file_type("conversation.mp3") == "audio_recording"

    def test_keyword_recording(self):
        assert _detect_file_type("recording_01.wav") == "audio_recording"

    def test_case_insensitive_extension(self):
        assert _detect_file_type("REPORT.PDF") == "document"

    def test_case_insensitive_keyword(self):
        assert _detect_file_type("EMAIL_CHAIN.PDF") == "email_chain"


# ---------------------------------------------------------------------------
# ingest_files
# ---------------------------------------------------------------------------

def _make_upload(filename: str, content: bytes):
    upload = MagicMock()
    upload.filename = filename
    upload.file = BytesIO(content)
    return upload


class TestIngestFiles:
    def test_returns_valid_uuid(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("test.txt", b"hello world")
            submission_id = ingest_files([upload], db)

        uuid.UUID(submission_id)  # must not raise

    def test_creates_submission_record(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("doc.txt", b"evidence content")
            submission_id = ingest_files([upload], db)

        submission = db.query(Submission).filter(
            Submission.id == uuid.UUID(submission_id)
        ).first()
        assert submission is not None
        assert submission.status == "INGESTED"
        assert submission.file_count == 1

    def test_creates_submission_file_records(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            uploads = [
                _make_upload("file1.txt", b"content one"),
                _make_upload("file2.txt", b"content two"),
            ]
            submission_id = ingest_files(uploads, db)

        files = db.query(SubmissionFile).filter(
            SubmissionFile.submission_id == uuid.UUID(submission_id)
        ).all()
        assert len(files) == 2

    def test_filename_not_stored(self, db, tmp_path):
        """Filenames are never persisted — only SHA-256(filename)."""
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("secret_source.txt", b"sensitive")
            submission_id = ingest_files([upload], db)

        files = db.query(SubmissionFile).filter(
            SubmissionFile.submission_id == uuid.UUID(submission_id)
        ).all()
        # filename_hash is SHA-256 hex (64 chars), NOT the original filename
        for f in files:
            assert f.filename_hash != "secret_source.txt"
            assert len(f.filename_hash) == 64

    def test_content_hash_stored(self, db, tmp_path):
        from app.core.crypto import sha256_bytes
        content = b"known content"
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("doc.txt", content)
            submission_id = ingest_files([upload], db)

        files = db.query(SubmissionFile).filter(
            SubmissionFile.submission_id == uuid.UUID(submission_id)
        ).all()
        assert files[0].content_hash == sha256_bytes(content)

    def test_encrypted_file_written_to_disk(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("doc.txt", b"plaintext")
            submission_id = ingest_files([upload], db)

        files = db.query(SubmissionFile).filter(
            SubmissionFile.submission_id == uuid.UUID(submission_id)
        ).all()
        for f in files:
            assert os.path.exists(f.encrypted_path)

    def test_merkle_root_in_submission(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("doc.txt", b"data")
            submission_id = ingest_files([upload], db)

        submission = db.query(Submission).filter(
            Submission.id == uuid.UUID(submission_id)
        ).first()
        assert len(submission.merkle_root) == 64

    def test_file_type_detected(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            upload = _make_upload("data.csv", b"col1,col2\nval1,val2")
            submission_id = ingest_files([upload], db)

        files = db.query(SubmissionFile).filter(
            SubmissionFile.submission_id == uuid.UUID(submission_id)
        ).all()
        assert files[0].file_type == "spreadsheet"

    def test_multiple_files_have_merkle_proof_paths(self, db, tmp_path):
        with patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)

            uploads = [
                _make_upload("a.txt", b"aaa"),
                _make_upload("b.txt", b"bbb"),
                _make_upload("c.txt", b"ccc"),
            ]
            submission_id = ingest_files(uploads, db)

        files = db.query(SubmissionFile).filter(
            SubmissionFile.submission_id == uuid.UUID(submission_id)
        ).all()
        for f in files:
            assert isinstance(f.merkle_proof_path, list)
