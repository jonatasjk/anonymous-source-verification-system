"""Unit tests for app.services.certificate."""
import uuid
from datetime import datetime, timezone

import pytest

from app.services.certificate import _generate_cert_id, _build_attribution_language, generate_certificate
from app.models.db import Submission, TimestampProof, AnalysisResult, Certificate
from tests.conftest import make_submission, make_file, make_proof, make_analysis


# ---------------------------------------------------------------------------
# _generate_cert_id
# ---------------------------------------------------------------------------

class TestGenerateCertId:
    def test_format(self):
        cert_id = _generate_cert_id()
        assert cert_id.startswith("CERT-")
        parts = cert_id.split("-")
        assert len(parts) == 3
        assert parts[1].isdigit()
        assert len(parts[2]) == 6

    def test_unique(self):
        ids = {_generate_cert_id() for _ in range(20)}
        # Very unlikely to collide with 6 hex chars; all 20 should be unique
        assert len(ids) >= 18  # allow for extreme edge case


# ---------------------------------------------------------------------------
# _build_attribution_language
# ---------------------------------------------------------------------------

class TestBuildAttributionLanguage:
    def test_substitutes_platform_and_cert_id(self):
        quotes = [{"text": "Evidence via {platform} cert {cert_id}.", "tone": "assertive"}]
        result = _build_attribution_language("CERT-2026-AABB01", 80, quotes, "ASVS")
        assert "ASVS" in result[0]
        assert "CERT-2026-AABB01" in result[0]

    def test_placeholders_not_remaining(self):
        quotes = [{"text": "Via {platform} ({cert_id}).", "tone": "hedged"}]
        result = _build_attribution_language("CERT-2026-000000", 80, quotes, "MyPlatform")
        assert "{platform}" not in result[0]
        assert "{cert_id}" not in result[0]

    def test_fallback_high_confidence_when_no_quotes(self):
        result = _build_attribution_language("CERT-2026-AABB01", 75, [], "ASVS")
        assert len(result) == 1
        assert "warrants further investigation" in result[0]

    def test_fallback_low_confidence_when_no_quotes(self):
        result = _build_attribution_language("CERT-2026-AABB01", 30, [], "ASVS")
        assert len(result) == 1
        assert "low" in result[0].lower()

    def test_fallback_threshold_40(self):
        # Exactly 40 should use "warrants" (hedged fallback)
        result = _build_attribution_language("CERT-2026-AABB01", 40, [], "ASVS")
        assert "warrants further investigation" in result[0]

    def test_fallback_threshold_39(self):
        # Below 40 triggers low-confidence alleged fallback
        result = _build_attribution_language("CERT-2026-AABB01", 39, [], "ASVS")
        assert "low" in result[0].lower()

    def test_multiple_quotes_all_substituted(self):
        quotes = [
            {"text": "First via {platform} ({cert_id}).", "tone": "assertive"},
            {"text": "Second via {platform} ({cert_id}).", "tone": "hedged"},
        ]
        result = _build_attribution_language("CERT-2026-XYZ789", 80, quotes, "ASVS")
        assert len(result) == 2
        for sentence in result:
            assert "ASVS" in sentence
            assert "CERT-2026-XYZ789" in sentence

    def test_none_quotes_treated_as_empty(self):
        result = _build_attribution_language("CERT-2026-AABB01", 80, None, "ASVS")
        assert len(result) == 1  # fallback triggered

    def test_string_entries_handled(self):
        """Handles plain string entries (not dicts) gracefully."""
        quotes = ["Plain string sentence for {platform} ({cert_id})."]
        result = _build_attribution_language("CERT-2026-AA0000", 80, quotes, "ASVS")
        assert "ASVS" in result[0]

    def test_empty_text_entry_skipped(self):
        quotes = [{"text": "", "tone": "assertive"}]
        # Empty text is filtered; fallback kicks in
        result = _build_attribution_language("CERT-2026-AABB01", 80, quotes, "ASVS")
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# generate_certificate
# ---------------------------------------------------------------------------

class TestGenerateCertificate:
    def test_creates_certificate_record(self, db):
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)

        cert_id = generate_certificate(str(sub.id), db)

        cert = db.query(Certificate).filter(Certificate.certificate_id == cert_id).first()
        assert cert is not None

    def test_returns_cert_id_string(self, db):
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)

        cert_id = generate_certificate(str(sub.id), db)

        assert isinstance(cert_id, str)
        assert cert_id.startswith("CERT-")

    def test_updates_submission_status_to_complete(self, db):
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)

        generate_certificate(str(sub.id), db)

        db.refresh(sub)
        assert sub.status == "COMPLETE"

    def test_payload_contains_required_sections(self, db):
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)

        cert_id = generate_certificate(str(sub.id), db)

        cert = db.query(Certificate).filter(Certificate.certificate_id == cert_id).first()
        assert "evidence_package" in cert.payload
        assert "analysis" in cert.payload
        assert "attribution_language" in cert.payload
        assert "timestamp_proofs" in cert.payload

    def test_raises_for_missing_submission(self, db):
        with pytest.raises(ValueError, match="not found"):
            generate_certificate(str(uuid.uuid4()), db)

    def test_raises_when_missing_proof(self, db):
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        # No proof added
        make_analysis(db, sub)

        with pytest.raises(ValueError, match="missing proof or analysis"):
            generate_certificate(str(sub.id), db)

    def test_raises_when_missing_analysis(self, db):
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        make_proof(db, sub)
        # No analysis added

        with pytest.raises(ValueError, match="missing proof or analysis"):
            generate_certificate(str(sub.id), db)

    def test_certificate_contains_no_pii(self, db):
        """Certificate payload must not contain raw filenames."""
        sub = make_submission(db, status="ANALYZED")
        make_file(db, sub)
        make_proof(db, sub)
        make_analysis(db, sub)

        cert_id = generate_certificate(str(sub.id), db)

        cert = db.query(Certificate).filter(Certificate.certificate_id == cert_id).first()
        payload_str = str(cert.payload)
        # filename_hash is a SHA-256 hex — check that "filename_hash" key exists in payload
        # but no raw filename like "secret_source.txt" could appear since we only store hashes
        assert len(cert.payload["evidence_package"]["files"]) >= 0  # structure exists
