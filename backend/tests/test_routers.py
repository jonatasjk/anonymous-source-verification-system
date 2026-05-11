"""Integration tests for submission and certificate routers via FastAPI TestClient."""
import os
import uuid
from io import BytesIO
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.models.db import Submission, Certificate
from tests.conftest import make_submission, make_certificate, make_file, make_proof, make_analysis


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/submissions
# ---------------------------------------------------------------------------

class TestCreateSubmission:
    def _post_file(self, client, filename="test.txt", content=b"evidence content"):
        return client.post(
            "/api/submissions",
            files=[("files", (filename, BytesIO(content), "text/plain"))],
        )

    def test_returns_202_with_submission_id(self, client, tmp_path):
        with patch("app.routers.submissions.enqueue_pipeline"), \
             patch("app.services.ingestion.settings") as mock_settings:
            mock_settings.storage_path = str(tmp_path)
            mock_settings.encryption_key = os.urandom(32)
            resp = self._post_file(client)

        assert resp.status_code == 202
        data = resp.json()
        assert "submission_id" in data
        uuid.UUID(str(data["submission_id"]))  # must be valid UUID

    def test_no_files_returns_422(self, client):
        resp = client.post("/api/submissions", files=[])
        assert resp.status_code in (422, 400)

    def test_too_many_files_returns_422(self, client):
        files = [("files", (f"f{i}.txt", BytesIO(b"x"), "text/plain")) for i in range(21)]
        with patch("app.routers.submissions.enqueue_pipeline"):
            resp = client.post("/api/submissions", files=files)
        assert resp.status_code == 422

    def test_file_too_large_returns_413(self, client):
        big_content = b"x" * (51 * 1024 * 1024)  # 51 MB
        resp = client.post(
            "/api/submissions",
            files=[("files", ("big.txt", BytesIO(big_content), "text/plain"))],
        )
        assert resp.status_code == 413


# ---------------------------------------------------------------------------
# GET /api/submissions/{id}/status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_returns_status_from_db(self, client, db):
        sub = make_submission(db, status="TIMESTAMPED")
        db.commit()

        with patch("app.routers.submissions.get_submission_status", return_value=None):
            resp = client.get(f"/api/submissions/{sub.id}/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "TIMESTAMPED"
        assert str(data["submission_id"]) == str(sub.id)

    def test_returns_status_from_redis_cache(self, client, db):
        sub = make_submission(db, status="INGESTED")
        db.commit()

        with patch("app.routers.submissions.get_submission_status", return_value="ANALYZED"):
            resp = client.get(f"/api/submissions/{sub.id}/status")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ANALYZED"

    def test_invalid_uuid_returns_422(self, client):
        with patch("app.routers.submissions.get_submission_status", return_value=None):
            resp = client.get("/api/submissions/not-a-uuid/status")
        assert resp.status_code == 422

    def test_unknown_id_returns_404(self, client):
        with patch("app.routers.submissions.get_submission_status", return_value=None):
            resp = client.get(f"/api/submissions/{uuid.uuid4()}/status")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/certificates
# ---------------------------------------------------------------------------

class TestListCertificates:
    def test_empty_list(self, client):
        resp = client.get("/api/certificates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_certificate_items(self, client, db):
        sub = make_submission(db)
        make_file(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        resp = client.get("/api/certificates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        item = data[0]
        assert "certificate_id" in item
        assert "overall_confidence" in item
        assert "reliability_class" in item


# ---------------------------------------------------------------------------
# GET /api/certificates/{certificate_id}
# ---------------------------------------------------------------------------

class TestGetCertificateById:
    def test_returns_certificate_payload(self, client, db):
        sub = make_submission(db)
        make_file(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        resp = client.get(f"/api/certificates/{cert.certificate_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "certificate_id" in data
        assert "evidence_package" in data
        assert "analysis" in data

    def test_case_insensitive_lookup(self, client, db):
        sub = make_submission(db)
        make_file(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        # Lowercase version of the cert ID
        resp = client.get(f"/api/certificates/{cert.certificate_id.lower()}")
        assert resp.status_code == 200

    def test_unknown_id_returns_404(self, client):
        resp = client.get("/api/certificates/CERT-2099-FFFFFF")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/submissions/{id}/certificate
# ---------------------------------------------------------------------------

class TestGetCertificateBySubmission:
    def test_returns_payload_for_complete_submission(self, client, db):
        sub = make_submission(db, status="COMPLETE")
        make_file(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        resp = client.get(f"/api/submissions/{sub.id}/certificate")
        assert resp.status_code == 200
        assert "certificate_id" in resp.json()

    def test_not_complete_returns_202(self, client, db):
        sub = make_submission(db, status="ANALYZED")
        db.commit()

        resp = client.get(f"/api/submissions/{sub.id}/certificate")
        assert resp.status_code == 202

    def test_invalid_uuid_returns_422(self, client):
        resp = client.get("/api/submissions/bad-id/certificate")
        assert resp.status_code == 422

    def test_unknown_submission_returns_404(self, client):
        resp = client.get(f"/api/submissions/{uuid.uuid4()}/certificate")
        assert resp.status_code == 404
