"""Integration tests for the verify router."""
import uuid
from unittest.mock import patch

import pytest

from tests.conftest import make_submission, make_file, make_proof, make_analysis, make_certificate


class TestVerifyCertificate:
    def test_valid_certificate_and_root_matches(self, client, db):
        sub = make_submission(db, status="COMPLETE")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        resp = client.post(
            "/api/verify",
            json={
                "certificate_id": cert.certificate_id,
                "merkle_root": "a" * 64,  # matches conftest make_submission merkle_root
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["merkle_root_matches"] is True
        assert data["certificate_id"] == cert.certificate_id

    def test_wrong_merkle_root_flagged(self, client, db):
        sub = make_submission(db, status="COMPLETE")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        resp = client.post(
            "/api/verify",
            json={
                "certificate_id": cert.certificate_id,
                "merkle_root": "0" * 64,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["merkle_root_matches"] is False

    def test_unknown_certificate_returns_404(self, client):
        resp = client.post(
            "/api/verify",
            json={"certificate_id": "CERT-2099-FFFFFF", "merkle_root": "a" * 64},
        )
        assert resp.status_code == 404

    def test_rfc3161_valid_when_token_exists(self, client, db):
        sub = make_submission(db, status="COMPLETE")
        make_file(db, sub)
        make_proof(db, sub)  # conftest creates proof with rfc3161_token_hash
        make_analysis(db, sub)
        cert = make_certificate(db, sub)
        db.commit()

        resp = client.post(
            "/api/verify",
            json={"certificate_id": cert.certificate_id, "merkle_root": "a" * 64},
        )
        assert resp.status_code == 200
        assert resp.json()["rfc3161_valid"] is True


class TestGetMerkleProof:
    def test_returns_proof_for_known_file(self, client, db):
        sub = make_submission(db, status="COMPLETE")
        sf = make_file(db, sub)
        db.commit()

        resp = client.get(f"/api/submissions/{sub.id}/files/{sf.content_hash}/proof")
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_hash"] == sf.content_hash
        assert "merkle_proof_path" in data
        assert "merkle_root" in data

    def test_unknown_file_hash_returns_404(self, client, db):
        sub = make_submission(db, status="COMPLETE")
        make_file(db, sub)
        db.commit()

        resp = client.get(f"/api/submissions/{sub.id}/files/{'0' * 64}/proof")
        assert resp.status_code == 404

    def test_invalid_submission_id_returns_422(self, client):
        resp = client.get(f"/api/submissions/bad-id/files/{'a' * 64}/proof")
        assert resp.status_code == 422

    def test_unknown_submission_returns_404(self, client):
        resp = client.get(f"/api/submissions/{uuid.uuid4()}/files/{'a' * 64}/proof")
        assert resp.status_code == 404
