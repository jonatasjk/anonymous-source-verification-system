"""
Shared pytest fixtures for the ASVS backend test suite.

Uses an in-memory SQLite database so tests run without PostgreSQL or Redis.
"""
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# -------------------------------------------------------------------
# Set env vars BEFORE any app module is imported so pydantic-settings
# picks them up and doesn't raise validation errors.
# -------------------------------------------------------------------
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("SECRET_KEY", "testsecretkey0000000000000000000")
os.environ.setdefault("ENCRYPTION_KEY", "a" * 64)

# -------------------------------------------------------------------
# Teach SQLite to render PostgreSQL JSONB as plain JSON.
# Must happen before any SQLAlchemy compilation.
# -------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402

def _visit_JSONB(self, type_, **kw):  # noqa: N802
    return self.visit_JSON(type_, **kw)

SQLiteTypeCompiler.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.db import Base, Submission, SubmissionFile, TimestampProof, AnalysisResult, Certificate  # noqa: E402

# -------------------------------------------------------------------
# Shared in-memory SQLite engine — one connection kept alive for the
# entire session so the in-memory DB is not destroyed between tests.
# -------------------------------------------------------------------
TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db():
    """Yield a fresh DB session; roll back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """FastAPI test client with the real DB dependency overridden."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# -------------------------------------------------------------------
# Helpers to build in-memory DB objects
# -------------------------------------------------------------------

def make_submission(db, status: str = "COMPLETE") -> Submission:
    sub = Submission(
        id=uuid.uuid4(),
        merkle_root="a" * 64,
        file_count=1,
        status=status,
    )
    db.add(sub)
    db.flush()
    return sub


def make_file(db, submission: Submission) -> SubmissionFile:
    sf = SubmissionFile(
        id=uuid.uuid4(),
        submission_id=submission.id,
        filename_hash="b" * 64,
        content_hash="c" * 64,
        file_type="document",
        size_bytes=100,
        merkle_proof_path=[],
        encrypted_path="/tmp/dummy.enc",
    )
    db.add(sf)
    db.flush()
    return sf


def make_proof(db, submission: Submission) -> TimestampProof:
    proof = TimestampProof(
        id=uuid.uuid4(),
        submission_id=submission.id,
        rfc3161_tsa="https://freetsa.org/tsr",
        rfc3161_token_hash="d" * 64,
        rfc3161_timestamp=datetime.now(timezone.utc),
        rfc3161_tsr_path="/tmp/dummy.tsr",
        rfc3161_cert_generation="2026-2040",
        rfc3161_cert_algorithm="EC P-384 (secp384r1)",
        ots_file_hash="e" * 64,
        ots_file_path="/tmp/dummy.ots",
        ots_confirmed=False,
    )
    db.add(proof)
    db.flush()
    return proof


def make_analysis(db, submission: Submission) -> AnalysisResult:
    result = AnalysisResult(
        id=uuid.uuid4(),
        submission_id=submission.id,
        overall_confidence=75,
        consistency_score=78,
        corroboration_score=72,
        plausibility_score=74,
        reliability_class="HIGH",
        corroborating_sources=2,
        evidence_types=["document"],
        red_flags=[],
        key_claims=["Claim A"],
        attribution_quotes=[
            {"text": "Source verified via {platform} (Certificate {cert_id}).", "tone": "assertive"}
        ],
    )
    db.add(result)
    db.flush()
    return result


def make_certificate(db, submission: Submission) -> Certificate:
    cert = Certificate(
        id=uuid.uuid4(),
        certificate_id=f"CERT-2026-{uuid.uuid4().hex[:6].upper()}",
        submission_id=submission.id,
        issued_at=datetime.now(timezone.utc),
        payload={
            "certificate_id": "CERT-2026-AABBCC",
            "submission_id": str(submission.id),
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "evidence_package": {
                "file_count": 1,
                "merkle_root": "a" * 64,
                "files": [],
            },
            "timestamp_proofs": {},
            "analysis": {
                "overall_confidence": 75,
                "consistency_score": 78,
                "corroboration_score": 72,
                "plausibility_score": 74,
                "evidence_types": ["document"],
                "corroborating_sources": 2,
                "red_flags": [],
                "reliability_class": "HIGH",
                "key_claims": [],
            },
            "attribution_language": ["Source verified by ASVS (Certificate CERT-2026-AABBCC)."],
        },
    )
    db.add(cert)
    db.flush()
    return cert
