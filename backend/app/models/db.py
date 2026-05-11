import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merkle_root = Column(String(64), nullable=False)
    file_count = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="INGESTED")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    files = relationship("SubmissionFile", back_populates="submission")
    timestamp_proof = relationship(
        "TimestampProof", back_populates="submission", uselist=False
    )
    analysis_result = relationship(
        "AnalysisResult", back_populates="submission", uselist=False
    )
    certificate = relationship(
        "Certificate", back_populates="submission", uselist=False
    )


class SubmissionFile(Base):
    __tablename__ = "submission_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(
        UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False
    )
    # SHA-256 of the original filename — filename itself is never stored
    filename_hash = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=False)
    file_type = Column(String(64))
    size_bytes = Column(BigInteger)
    # Ordered list of {"hash": "...", "position": "left"|"right"} steps
    merkle_proof_path = Column(JSONB, nullable=False)
    encrypted_path = Column(Text, nullable=False)

    submission = relationship("Submission", back_populates="files")


class TimestampProof(Base):
    __tablename__ = "timestamp_proofs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False,
        unique=True,
    )
    # RFC 3161
    rfc3161_tsa = Column(String(255))
    rfc3161_token_hash = Column(String(64))
    rfc3161_timestamp = Column(DateTime(timezone=True))
    rfc3161_tsr_path = Column(Text)
    rfc3161_cert_generation = Column(String(32))
    rfc3161_cert_algorithm = Column(String(64))
    # OpenTimestamps
    ots_file_hash = Column(String(64))
    ots_file_path = Column(Text)
    ots_bitcoin_block = Column(BigInteger)
    ots_block_timestamp = Column(DateTime(timezone=True))
    ots_confirmed = Column(Boolean, nullable=False, default=False)

    submission = relationship("Submission", back_populates="timestamp_proof")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False,
        unique=True,
    )
    overall_confidence = Column(SmallInteger)
    consistency_score = Column(SmallInteger)
    corroboration_score = Column(SmallInteger)
    plausibility_score = Column(SmallInteger)
    reliability_class = Column(String(16))
    corroborating_sources = Column(SmallInteger)
    # Anonymised structured output — no source names or verbatim quotes
    evidence_types = Column(JSONB)
    red_flags = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    submission = relationship("Submission", back_populates="analysis_result")


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id = Column(String(32), nullable=False, unique=True)
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False,
        unique=True,
    )
    # Full certificate JSON cached for fast retrieval
    payload = Column(JSONB, nullable=False)
    issued_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    submission = relationship("Submission", back_populates="certificate")
